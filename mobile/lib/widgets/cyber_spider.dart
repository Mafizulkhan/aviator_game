import 'dart:math';
import 'package:flutter/material.dart';
import '../core/constants/app_constants.dart';
import '../models/round.dart';

class CyberSpiderWidget extends StatefulWidget {
  final RoundStatus status;
  final double multiplier;

  const CyberSpiderWidget({
    super.key,
    required this.status,
    required this.multiplier,
  });

  @override
  State<CyberSpiderWidget> createState() => _CyberSpiderWidgetState();
}

class _CyberSpiderWidgetState extends State<CyberSpiderWidget> with SingleTickerProviderStateMixin {
  late AnimationController _animController;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animController,
      builder: (context, child) {
        final isRunning = widget.status == RoundStatus.running;
        final isCrashed = widget.status == RoundStatus.crashed;

        final pulse = isRunning ? sin(_animController.value * 2 * pi) * 0.1 : 0.0;
        final spiderColor = isCrashed
            ? AppColors.dangerRed
            : (isRunning ? AppColors.primaryCyan : AppColors.secondaryPurple);

        return Stack(
          alignment: Alignment.center,
          children: [
            // Glowing energy aura behind spider
            Container(
              width: 140,
              height: 140,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: spiderColor.withValues(alpha: isRunning ? 0.45 : 0.15),
                    blurRadius: 35 + (pulse * 20),
                    spreadRadius: 8,
                  ),
                ],
              ),
            ),
            // Custom Cyber Spider Painter
            Transform.scale(
              scale: 1.0 + pulse,
              child: CustomPaint(
                size: const Size(120, 120),
                painter: _CyberSpiderPainter(
                  color: spiderColor,
                  animProgress: _animController.value,
                  isCrashed: isCrashed,
                  isRunning: isRunning,
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _CyberSpiderPainter extends CustomPainter {
  final Color color;
  final double animProgress;
  final bool isCrashed;
  final bool isRunning;

  _CyberSpiderPainter({
    required this.color,
    required this.animProgress,
    required this.isCrashed,
    required this.isRunning,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final paint = Paint()
      ..color = color
      ..strokeWidth = 3.0
      ..style = PaintingStyle.stroke;

    final fillPaint = Paint()
      ..color = color.withValues(alpha: 0.3)
      ..style = PaintingStyle.fill;

    // Spider Abdomen (Hexagonal Cyber Body)
    final path = Path();
    const double radius = 22.0;
    for (int i = 0; i < 6; i++) {
      final angle = (i * 60) * pi / 180;
      final point = Offset(
        center.dx + radius * cos(angle),
        center.dy + radius * sin(angle),
      );
      if (i == 0) {
        path.moveTo(point.dx, point.dy);
      } else {
        path.lineTo(point.dx, point.dy);
      }
    }
    path.close();
    canvas.drawPath(path, fillPaint);
    canvas.drawPath(path, paint);

    // Spider Head (Cyber Core)
    final headCenter = Offset(center.dx, center.dy - 26);
    canvas.drawCircle(headCenter, 10, fillPaint);
    canvas.drawCircle(headCenter, 10, paint);

    // Glowing Eyes
    final eyePaint = Paint()
      ..color = isCrashed ? Colors.white : AppColors.accentGold
      ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(headCenter.dx - 4, headCenter.dy - 2), 2.5, eyePaint);
    canvas.drawCircle(Offset(headCenter.dx + 4, headCenter.dy - 2), 2.5, eyePaint);

    // Cyber Limbs (8 legs with robotic joints)
    final legPaint = Paint()
      ..color = color
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;

    final legOffset = isRunning ? sin(animProgress * pi * 2) * 6 : 0.0;

    for (int side = -1; side <= 1; side += 2) {
      for (int i = 0; i < 4; i++) {
        final legAngle = (-50 + (i * 35)) * pi / 180;
        final joint1 = Offset(
          center.dx + (side * 18),
          center.dy - 10 + (i * 9),
        );
        final joint2 = Offset(
          center.dx + (side * (38 + (i * 4))),
          center.dy - 25 + (i * 18) + (side * legOffset * (i % 2 == 0 ? 1 : -1)),
        );
        final foot = Offset(
          center.dx + (side * (55 + (i * 6))),
          center.dy - 10 + (i * 22) + (side * legOffset * (i % 2 == 0 ? -1 : 1)),
        );

        canvas.drawLine(joint1, joint2, legPaint);
        canvas.drawLine(joint2, foot, legPaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _CyberSpiderPainter oldDelegate) {
    return oldDelegate.animProgress != animProgress ||
        oldDelegate.color != color ||
        oldDelegate.isCrashed != isCrashed;
  }
}
