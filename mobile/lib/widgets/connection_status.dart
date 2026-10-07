import 'package:flutter/material.dart';
import '../core/networking/websocket_client.dart';
import '../core/constants/app_constants.dart';

class ConnectionStatusWidget extends StatelessWidget {
  final WsConnectionState state;

  const ConnectionStatusWidget({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    Color dotColor;
    String statusText;

    switch (state) {
      case WsConnectionState.connected:
        dotColor = AppColors.successGreen;
        statusText = 'LIVE';
        break;
      case WsConnectionState.connecting:
      case WsConnectionState.reconnecting:
        dotColor = AppColors.warningOrange;
        statusText = 'CONNECTING...';
        break;
      case WsConnectionState.error:
      case WsConnectionState.disconnected:
        dotColor = AppColors.dangerRed;
        statusText = 'OFFLINE';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: dotColor.withValues(alpha: 0.5)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: dotColor,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: dotColor.withValues(alpha: 0.6),
                  blurRadius: 6,
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
          const SizedBox(width: 6),
          Text(
            statusText,
            style: TextStyle(
              fontFamily: 'Orbitron',
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: dotColor,
            ),
          ),
        ],
      ),
    );
  }
}
