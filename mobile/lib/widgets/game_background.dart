import 'dart:math';
import 'package:flutter/material.dart';
import '../core/constants/app_constants.dart';

class GameBackground extends StatelessWidget {
  final Widget child;

  const GameBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Dark background base
        Container(
          color: AppColors.background,
        ),
        // Cyber Neon Grid / Starfield Canvas
        Positioned.fill(
          child: CustomPaint(
            painter: _SpaceGridPainter(),
          ),
        ),
        // Child content on top
        child,
      ],
    );
  }
}

class _SpaceGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = AppColors.border.withValues(alpha: 0.25)
      ..strokeWidth = 1.0;

    const double step = 45.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    // Distant cyber stars
    final starPaint = Paint()
      ..color = AppColors.primaryCyan.withValues(alpha: 0.4)
      ..style = PaintingStyle.fill;

    final random = Random(42);
    for (int i = 0; i < 35; i++) {
      final x = random.nextDouble() * size.width;
      final y = random.nextDouble() * size.height;
      final radius = random.nextDouble() * 1.5 + 0.5;
      canvas.drawCircle(Offset(x, y), radius, starPaint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
