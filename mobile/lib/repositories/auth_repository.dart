import '../core/networking/api_client.dart';
import '../core/auth/token_storage.dart';
import '../models/user.dart';

class AuthRepository {
  final ApiClient _apiClient;
  final TokenStorage _tokenStorage;

  User? _currentUser;
  User? get currentUser => _currentUser;
  bool get isAuthenticated => _currentUser != null;

  AuthRepository({
    ApiClient? apiClient,
    TokenStorage? tokenStorage,
  })  : _apiClient = apiClient ?? ApiClient(),
        _tokenStorage = tokenStorage ?? TokenStorage();

  Future<User> register({
    required String username,
    required String email,
    required String password,
  }) async {
    final response = await _apiClient.post(
      '/api/auth/register',
      body: {
        'username': username,
        'email': email,
        'password': password,
      },
      requiresAuth: false,
    );

    if (response is Map && response.containsKey('access_token')) {
      await _tokenStorage.saveTokens(
        accessToken: response['access_token'] as String,
        refreshToken: response['refresh_token'] as String?,
      );
    }

    return await fetchProfile();
  }

  Future<User> login({
    required String username,
    required String password,
  }) async {
    final response = await _apiClient.post(
      '/api/auth/login',
      body: {
        'username': username,
        'password': password,
      },
      requiresAuth: false,
    );

    if (response is Map && response.containsKey('access_token')) {
      await _tokenStorage.saveTokens(
        accessToken: response['access_token'] as String,
        refreshToken: response['refresh_token'] as String?,
      );
    }

    return await fetchProfile();
  }

  Future<User> fetchProfile() async {
    final response = await _apiClient.get('/api/player/profile');
    _currentUser = User.fromJson(response as Map<String, dynamic>);
    return _currentUser!;
  }

  Future<bool> tryAutoLogin() async {
    final token = await _tokenStorage.getAccessToken();
    if (token == null) return false;

    try {
      await fetchProfile();
      return true;
    } catch (_) {
      await logout();
      return false;
    }
  }

  Future<void> logout() async {
    try {
      await _apiClient.post('/api/auth/logout');
    } catch (_) {}
    await _tokenStorage.clearTokens();
    _currentUser = null;
  }
}
