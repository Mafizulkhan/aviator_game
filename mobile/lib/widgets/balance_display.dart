import 'package:flutter/material.dart';
import '../core/constants/app_constants.dart';
import '../core/utils/formatters.dart';

class BalanceDisplay extends StatelessWidget {
  final int balance;

  const BalanceDisplay({super.key, required this.balance});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.accentGold.withValues(alpha: 0.4)),
        boxShadow: [
          BoxShadow(
            color: AppColors.accentGold.withValues(alpha: 0.1),
            blurRadius: 8,
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.monetization_on_outlined,
            color: AppColors.accentGold,
            size: 18,
          ),
          const SizedBox(width: 6),
          Text(
            Formatters.credits(balance),
            style: const TextStyle(
              fontFamily: 'Orbitron',
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: AppColors.accentGold,
            ),
          ),
        ],
      ),
    );
  }
}
