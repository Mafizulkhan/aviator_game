import '../core/networking/api_client.dart';
import '../models/fairness.dart';

class FairnessRepository {
  final ApiClient _apiClient;

  FairnessRepository({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  Future<FairnessRecord> getRoundFairness(int roundId) async {
    final response = await _apiClient.get('/api/fairness/$roundId');
    return FairnessRecord.fromJson(response as Map<String, dynamic>);
  }

  Future<FairnessRecord> verifyRound(int roundId) async {
    final response = await _apiClient.get('/api/fairness/$roundId/verify');
    return FairnessRecord.fromJson(response as Map<String, dynamic>);
  }
}
