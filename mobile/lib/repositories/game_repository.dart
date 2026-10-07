import 'dart:async';
import 'package:flutter/foundation.dart';
import '../core/networking/api_client.dart';
import '../core/networking/websocket_client.dart';
import '../models/round.dart';
import '../models/bet.dart';

class GameRepository extends ChangeNotifier {
  final ApiClient _apiClient;
  final WebSocketClient _wsClient;

  GameRound? _currentRound;
  double _currentMultiplier = 1.00;
  RoundStatus _gameStatus = RoundStatus.waiting;
  Bet? _activeBet;
  bool _isCashedOut = false;
  int? _lastPayout;

  StreamSubscription? _wsSubscription;
  StreamSubscription? _wsStateSubscription;

  GameRound? get currentRound => _currentRound;
  double get currentMultiplier => _currentMultiplier;
  RoundStatus get gameStatus => _gameStatus;
  Bet? get activeBet => _activeBet;
  bool get isCashedOut => _isCashedOut;
  int? get lastPayout => _lastPayout;
  WsConnectionState get connectionState => _wsClient.state;

  GameRepository({
    ApiClient? apiClient,
    WebSocketClient? wsClient,
  })  : _apiClient = apiClient ?? ApiClient(),
        _wsClient = wsClient ?? WebSocketClient() {
    _initWsListeners();
  }

  void _initWsListeners() {
    _wsSubscription = _wsClient.messageStream.listen(_handleWsMessage);
    _wsStateSubscription = _wsClient.stateStream.listen((_) => notifyListeners());
  }

  void connectWebSocket({String? token}) {
    _wsClient.connect(token: token);
  }

  void _handleWsMessage(Map<String, dynamic> msg) {
    final type = msg['type'] as String?;

    switch (type) {
      case 'round_start':
        _currentRound = GameRound.fromJson(msg);
        _gameStatus = RoundStatus.running;
        _currentMultiplier = 1.00;
        _isCashedOut = false;
        _lastPayout = null;
        notifyListeners();
        break;

      case 'multiplier_update':
        if (_gameStatus == RoundStatus.running) {
          _currentMultiplier = (msg['multiplier'] as num?)?.toDouble() ?? _currentMultiplier;
          notifyListeners();
        }
        break;

      case 'crash':
        _gameStatus = RoundStatus.crashed;
        _currentMultiplier = (msg['crash_multiplier'] as num?)?.toDouble() ?? _currentMultiplier;
        if (_activeBet != null && !_isCashedOut) {
          _activeBet = Bet(
            id: _activeBet!.id,
            roundId: _activeBet!.roundId,
            amount: _activeBet!.amount,
            status: BetStatus.lost,
            createdAt: _activeBet!.createdAt,
          );
        }
        notifyListeners();
        break;

      case 'cashout':
        _isCashedOut = true;
        _lastPayout = (msg['payout'] as num?)?.toInt();
        final mult = (msg['multiplier'] as num?)?.toDouble();
        if (_activeBet != null) {
          _activeBet = Bet(
            id: _activeBet!.id,
            roundId: _activeBet!.roundId,
            amount: _activeBet!.amount,
            cashoutMultiplier: mult,
            payout: _lastPayout,
            status: BetStatus.cashedOut,
            createdAt: _activeBet!.createdAt,
          );
        }
        notifyListeners();
        break;

      case 'round_end':
        _gameStatus = RoundStatus.ended;
        notifyListeners();
        break;
    }
  }

  Future<Bet> placeBet({required int roundId, required int amount}) async {
    final response = await _apiClient.post(
      '/api/game/join',
      body: {
        'round_id': roundId,
        'amount': amount,
      },
    );

    _activeBet = Bet.fromJson(response as Map<String, dynamic>);
    _isCashedOut = false;
    _lastPayout = null;
    notifyListeners();
    return _activeBet!;
  }

  Future<Map<String, dynamic>> cashOut({required int roundId}) async {
    final response = await _apiClient.post(
      '/api/game/cashout',
      body: {
        'round_id': roundId,
      },
    );

    _isCashedOut = true;
    _lastPayout = (response['payout'] as num?)?.toInt();
    notifyListeners();
    return response as Map<String, dynamic>;
  }

  Future<List<GameRound>> getRoundHistory({int limit = 30}) async {
    final response = await _apiClient.get('/api/game/history?limit=$limit');
    if (response is List) {
      return response.map((item) => GameRound.fromJson(item as Map<String, dynamic>)).toList();
    }
    return [];
  }

  @override
  void dispose() {
    _wsSubscription?.cancel();
    _wsStateSubscription?.cancel();
    _wsClient.dispose();
    super.dispose();
  }
}
