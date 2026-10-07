import 'package:flutter_test/flutter_test.dart';
import 'package:zero_gravity/core/networking/websocket_client.dart';

void main() {
  group('WebSocketClient State Tests', () {
    test('Initial state is disconnected', () {
      final wsClient = WebSocketClient();
      expect(wsClient.state, WsConnectionState.disconnected);
    });

    test('Disconnect sets state to disconnected cleanly', () {
      final wsClient = WebSocketClient();
      wsClient.disconnect();
      expect(wsClient.state, WsConnectionState.disconnected);
    });
  });
}
