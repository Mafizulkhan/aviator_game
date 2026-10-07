/// Custom Application Exceptions with user-friendly error messages.
class AppException implements Exception {
  final String message;
  final int? statusCode;

  AppException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class AuthException extends AppException {
  AuthException(super.message, {super.statusCode});
}

class NetworkException extends AppException {
  NetworkException(super.message, {super.statusCode});
}

class GameException extends AppException {
  GameException(super.message, {super.statusCode});
}
