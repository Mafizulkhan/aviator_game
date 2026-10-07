import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/networking/api_client.dart';
import 'core/networking/websocket_client.dart';
import 'core/auth/token_storage.dart';
import 'repositories/auth_repository.dart';
import 'repositories/player_repository.dart';
import 'repositories/game_repository.dart';
import 'repositories/fairness_repository.dart';
import 'theme/app_theme.dart';
import 'features/splash/splash_screen.dart';

class ZeroGravityApp extends StatelessWidget {
  const ZeroGravityApp({super.key});

  @override
  Widget build(BuildContext context) {
    final tokenStorage = TokenStorage();
    final apiClient = ApiClient(tokenStorage: tokenStorage);
    final wsClient = WebSocketClient();

    return MultiProvider(
      providers: [
        Provider<TokenStorage>.value(value: tokenStorage),
        Provider<ApiClient>.value(value: apiClient),
        Provider<WebSocketClient>.value(value: wsClient),
        Provider<AuthRepository>(
          create: (_) => AuthRepository(apiClient: apiClient, tokenStorage: tokenStorage),
        ),
        Provider<PlayerRepository>(
          create: (_) => PlayerRepository(apiClient: apiClient),
        ),
        ChangeNotifierProvider<GameRepository>(
          create: (_) => GameRepository(apiClient: apiClient, wsClient: wsClient),
        ),
        Provider<FairnessRepository>(
          create: (_) => FairnessRepository(apiClient: apiClient),
        ),
      ],
      child: MaterialApp(
        title: 'Zero Gravity',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        home: const SplashScreen(),
      ),
    );
  }
}
