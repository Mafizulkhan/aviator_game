import 'package:flutter/material.dart';
import '../core/constants/app_constants.dart';
import '../core/utils/formatters.dart';

class CashoutButton extends StatelessWidget {
  final int betAmount;
  final double currentMultiplier;
  final bool isEnabled;
  final bool isCashedOut;
  final int? cashedOutPayout;
  final VoidCallback onCashout;

  const CashoutButton({
    super.key,
    required this.betAmount,
    required this.currentMultiplier,
    required this.isEnabled,
    required this.isCashedOut,
    this.cashedOutPayout,
    required this.onCashout,
  });

  @override
  Widget build(BuildContext context) {
    if (isCashedOut) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 18),
        decoration: BoxDecoration(
          color: AppColors.successGreen.withValues(alpha: 0.2),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.successGreen, width: 2),
        ),
        child: Column(
          children: [
            const Text(
              'CASHED OUT!',
              style: TextStyle(
                fontFamily: 'Orbitron',
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppColors.successGreen,
                letterSpacing: 1.5,
              ),
            ),
            if (cashedOutPayout != null)
              Text(
                '+${Formatters.credits(cashedOutPayout!)}',
                style: const TextStyle(
                  fontFamily: 'Orbitron',
                  fontSize: 16,
                  color: AppColors.accentGold,
                  fontWeight: FontWeight.bold,
                ),
              ),
          ],
        ),
      );
    }

    final potentialPayout = (betAmount * currentMultiplier).floor();

    return SizedBox(
      width: double.infinity,
      height: 64,
      child: ElevatedButton(
        onPressed: isEnabled ? onCashout : null,
        style: ElevatedButton.styleFrom(
          backgroundColor: isEnabled ? AppColors.accentGold : AppColors.surfaceElevated,
          foregroundColor: AppColors.background,
          disabledBackgroundColor: AppColors.surfaceElevated,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          elevation: isEnabled ? 8 : 0,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'CASH OUT',
              style: AppTextStyles.button.copyWith(
                fontSize: 18,
                color: isEnabled ? AppColors.background : AppColors.textSecondary,
              ),
            ),
            if (isEnabled)
              Text(
                'Payout: ${Formatters.credits(potentialPayout)}',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: AppColors.background,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
