import 'package:flutter/material.dart';
import '../core/constants/app_constants.dart';
import '../models/round.dart';

class MultiplierDisplay extends StatelessWidget {
  final double multiplier;
  final RoundStatus status;

  const MultiplierDisplay({
    super.key,
    required this.multiplier,
    required this.status,
  });

  @override
  Widget build(BuildContext context) {
    Color textColor = AppColors.primaryCyan;
    String statusText = '';

    if (status == RoundStatus.crashed) {
      textColor = AppColors.dangerRed;
      statusText = 'CRASHED';
    } else if (status == RoundStatus.waiting) {
      textColor = AppColors.textSecondary;
      statusText = 'PREPARING ROUND...';
    } else if (status == RoundStatus.ended) {
      textColor = AppColors.accentGold;
      statusText = 'ROUND FINISHED';
    } else if (multiplier >= 10.0) {
      textColor = AppColors.accentGold;
    } else if (multiplier >= 2.0) {
      textColor = AppColors.successGreen;
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (statusText.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 6.0),
            child: Text(
              statusText,
              style: TextStyle(
                fontFamily: 'Orbitron',
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: textColor,
                letterSpacing: 2.0,
              ),
            ),
          ),
        Text(
          '${multiplier.toStringAsFixed(2)}x',
          style: AppTextStyles.multiplier.copyWith(
            color: textColor,
            shadows: [
              Shadow(
                color: textColor.withValues(alpha: 0.8),
                blurRadius: 20,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
