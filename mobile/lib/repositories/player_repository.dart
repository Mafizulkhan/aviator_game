import '../core/networking/api_client.dart';
import '../models/wallet.dart';
import '../models/transaction.dart';
import '../models/bet.dart';

class PlayerRepository {
  final ApiClient _apiClient;

  PlayerRepository({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  Future<Wallet> getBalance() async {
    final response = await _apiClient.get('/api/player/balance');
    return Wallet.fromJson(response as Map<String, dynamic>);
  }

  Future<List<Bet>> getPlayerHistory({int limit = 50}) async {
    final response = await _apiClient.get('/api/player/history?limit=$limit');
    if (response is List) {
      return response.map((item) => Bet.fromJson(item as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<List<WalletTransaction>> getTransactions({int limit = 50}) async {
    final response = await _apiClient.get('/api/player/transactions?limit=$limit');
    if (response is List) {
      return response.map((item) => WalletTransaction.fromJson(item as Map<String, dynamic>)).toList();
    }
    return [];
  }
}
