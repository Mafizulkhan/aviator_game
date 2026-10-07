import 'package:flutter_test/flutter_test.dart';
import 'package:zero_gravity/core/networking/api_client.dart';
import 'package:zero_gravity/core/auth/token_storage.dart';
import 'package:zero_gravity/core/errors/app_exceptions.dart';

void main() {
  group('ApiClient Tests', () {
    test('Initializes with default baseUrl', () {
      final client = ApiClient();
      expect(client.baseUrl.isNotEmpty, true);
    });

    test('AppException format validation', () {
      final ex = AppException('Test Error', statusCode: 400);
      expect(ex.message, 'Test Error');
      expect(ex.statusCode, 400);
      expect(ex.toString(), 'Test Error');
    });

    test('AuthException inherits from AppException', () {
      final authEx = AuthException('Unauthorized', statusCode: 401);
      expect(authEx is AppException, true);
      expect(authEx.statusCode, 401);
    });
  });
}
