import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zero_gravity/widgets/multiplier_display.dart';
import 'package:zero_gravity/widgets/cyber_spider.dart';
import 'package:zero_gravity/widgets/balance_display.dart';
import 'package:zero_gravity/widgets/connection_status.dart';
import 'package:zero_gravity/models/round.dart';
import 'package:zero_gravity/core/networking/websocket_client.dart';

void main() {
  group('Zero Gravity Core Widgets Tests', () {
    testWidgets('MultiplierDisplay renders active multiplier correctly', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MultiplierDisplay(
              multiplier: 2.37,
              status: RoundStatus.running,
            ),
          ),
        ),
      );

      expect(find.text('2.37x'), findsOneWidget);
    });

    testWidgets('MultiplierDisplay renders CRASHED when round is crashed', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MultiplierDisplay(
              multiplier: 1.50,
              status: RoundStatus.crashed,
            ),
          ),
        ),
      );

      expect(find.text('CRASHED'), findsOneWidget);
      expect(find.text('1.50x'), findsOneWidget);
    });

    testWidgets('BalanceDisplay renders virtual credits format', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: BalanceDisplay(balance: 10450),
          ),
        ),
      );

      expect(find.text('10,450 CR'), findsOneWidget);
    });

    testWidgets('ConnectionStatusWidget renders LIVE when connected', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ConnectionStatusWidget(state: WsConnectionState.connected),
          ),
        ),
      );

      expect(find.text('LIVE'), findsOneWidget);
    });

    testWidgets('CyberSpiderWidget renders without crashing', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: CyberSpiderWidget(
              status: RoundStatus.running,
              multiplier: 1.85,
            ),
          ),
        ),
      );

      expect(find.byType(CyberSpiderWidget), findsOneWidget);
    });
  });
}
