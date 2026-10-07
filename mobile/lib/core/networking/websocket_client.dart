import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../config/app_config.dart';

enum WsConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

class WebSocketClient {
  final String url;
  WebSocketChannel? _channel;
  WsConnectionState _state = WsConnectionState.disconnected;
  final _stateController = StreamController<WsConnectionState>.broadcast();
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();

  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  int _reconnectAttempts = 0;
  bool _intentionalClose = false;

  WebSocketClient({String? url}) : url = url ?? AppConfig.wsUrl;

  WsConnectionState get state => _state;
  Stream<WsConnectionState> get stateStream => _stateController.stream;
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;

  void connect({String? token}) {
    _intentionalClose = false;
    _updateState(WsConnectionState.connecting);

    try {
      final wsUri = Uri.parse(url);
      _channel = WebSocketChannel.connect(wsUri);

      _channel!.stream.listen(
        (data) {
          _onData(data);
        },
        onError: (error) {
          _onError(error);
        },
        onDone: () {
          _onDone();
        },
      );

      _updateState(WsConnectionState.connected);
      _reconnectAttempts = 0;
      _startHeartbeat();

      if (token != null) {
        send({'type': 'auth', 'token': token});
      }
    } catch (e) {
      _onError(e);
    }
  }

  void _onData(dynamic rawData) {
    try {
      final Map<String, dynamic> data = jsonDecode(rawData.toString());
      _messageController.add(data);
    } catch (_) {
      // Ignore malformed payloads safely
    }
  }

  void _onError(dynamic error) {
    _updateState(WsConnectionState.error);
    _scheduleReconnect();
  }

  void _onDone() {
    _stopHeartbeat();
    if (!_intentionalClose) {
      _updateState(WsConnectionState.disconnected);
      _scheduleReconnect();
    }
  }

  void _startHeartbeat() {
    _stopHeartbeat();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      if (_state == WsConnectionState.connected) {
        send({'type': 'ping', 'timestamp': DateTime.now().millisecondsSinceEpoch});
      }
    });
  }

  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  void _scheduleReconnect() {
    if (_intentionalClose) return;

    _reconnectTimer?.cancel();
    final delaySeconds = [1, 2, 4, 8, 16][(_reconnectAttempts).clamp(0, 4)];
    _reconnectAttempts++;

    _updateState(WsConnectionState.reconnecting);
    _reconnectTimer = Timer(Duration(seconds: delaySeconds), () {
      connect();
    });
  }

  void send(Map<String, dynamic> message) {
    if (_channel != null && _state == WsConnectionState.connected) {
      _channel!.sink.add(jsonEncode(message));
    }
  }

  void disconnect() {
    _intentionalClose = true;
    _stopHeartbeat();
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
    _updateState(WsConnectionState.disconnected);
  }

  void _updateState(WsConnectionState newState) {
    _state = newState;
    _stateController.add(_state);
  }

  void dispose() {
    disconnect();
    _stateController.close();
    _messageController.close();
  }
}
