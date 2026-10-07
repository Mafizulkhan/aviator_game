/// App configuration loaded via build-time Dart defines or defaults.
class AppConfig {
  static const String appName = 'Zero Gravity';
  static const String appVersion = '1.0.0';

  // Environment: 'development', 'staging', 'production'
  static const String environment = String.fromEnvironment(
    'ANTI_GRAVITY_ENV',
    defaultValue: 'development',
  );

  // Default API Base URL (LAN development support via Dart Define)
  static const String apiBaseUrl = String.fromEnvironment(
    'ANTI_GRAVITY_API_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  // Default WebSocket URL
  static const String wsUrl = String.fromEnvironment(
    'ANTI_GRAVITY_WS_URL',
    defaultValue: 'ws://10.0.2.2:8000/ws/game',
  );

  static bool get isProduction => environment == 'production';
  static bool get isDevelopment => environment == 'development';

  // Gameplay configuration limits
  static const int minBet = 10;
  static const int maxBet = 5000;
  static const int defaultBet = 100;
  static const int startingBalance = 10000;
}
