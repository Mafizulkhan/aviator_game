import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../../config/app_config.dart';
import '../errors/app_exceptions.dart';
import '../auth/token_storage.dart';

class ApiClient {
  final String baseUrl;
  final http.Client _client;
  final TokenStorage _tokenStorage;

  ApiClient({
    String? baseUrl,
    http.Client? client,
    TokenStorage? tokenStorage,
  })  : baseUrl = baseUrl ?? AppConfig.apiBaseUrl,
        _client = client ?? http.Client(),
        _tokenStorage = tokenStorage ?? TokenStorage();

  Future<Map<String, String>> _getHeaders({bool requiresAuth = true}) async {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (requiresAuth) {
      final token = await _tokenStorage.getAccessToken();
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  Future<dynamic> get(String endpoint, {bool requiresAuth = true}) async {
    try {
      final headers = await _getHeaders(requiresAuth: requiresAuth);
      final response = await _client.get(
        Uri.parse('$baseUrl$endpoint'),
        headers: headers,
      );
      return _processResponse(response);
    } on SocketException {
      throw NetworkException('Unable to reach Zero Gravity servers. Please check your connection.');
    }
  }

  Future<dynamic> post(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    try {
      final headers = await _getHeaders(requiresAuth: requiresAuth);
      final response = await _client.post(
        Uri.parse('$baseUrl$endpoint'),
        headers: headers,
        body: body != null ? jsonEncode(body) : null,
      );
      return _processResponse(response);
    } on SocketException {
      throw NetworkException('Unable to reach Zero Gravity servers. Please check your connection.');
    }
  }

  dynamic _processResponse(http.Response response) {
    dynamic body;
    try {
      body = jsonDecode(response.body);
    } catch (_) {
      body = response.body;
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    }

    final errorMessage = body is Map && body.containsKey('detail')
        ? body['detail'].toString()
        : 'Request failed (${response.statusCode})';

    if (response.statusCode == 401) {
      throw AuthException(errorMessage, statusCode: 401);
    } else if (response.statusCode == 400 || response.statusCode == 422) {
      throw AppException(errorMessage, statusCode: response.statusCode);
    } else {
      throw AppException(errorMessage, statusCode: response.statusCode);
    }
  }
}
