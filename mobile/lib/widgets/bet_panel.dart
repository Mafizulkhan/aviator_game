import 'package:flutter/material.dart';
import '../core/constants/app_constants.dart';
import '../core/utils/formatters.dart';

class BetPanel extends StatefulWidget {
  final int currentBalance;
  final bool isBettingAllowed;
  final Function(int) onPlaceBet;

  const BetPanel({
    super.key,
    required this.currentBalance,
    required this.isBettingAllowed,
    required this.onPlaceBet,
  });

  @override
  State<BetPanel> createState() => _BetPanelState();
}

class _BetPanelState extends State<BetPanel> {
  int _selectedBet = 100;
  final TextEditingController _customController = TextEditingController(text: '100');

  void _setBet(int amount) {
    final clamped = amount.clamp(10, widget.currentBalance > 0 ? widget.currentBalance : 5000);
    setState(() {
      _selectedBet = clamped;
      _customController.text = clamped.toString();
    });
  }

  @override
  Widget build(BuildContext context) {
    final presets = [10, 50, 100, 500];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'BET AMOUNT',
                style: TextStyle(
                  fontFamily: 'Orbitron',
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textSecondary,
                  letterSpacing: 1.0,
                ),
              ),
              Text(
                'Balance: ${Formatters.credits(widget.currentBalance)}',
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.accentGold,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Presets row
          Row(
            children: [
              ...presets.map((amount) {
                final isSelected = _selectedBet == amount;
                return Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 3.0),
                    child: OutlinedButton(
                      onPressed: widget.isBettingAllowed ? () => _setBet(amount) : null,
                      style: OutlinedButton.styleFrom(
                        backgroundColor: isSelected
                            ? AppColors.primaryCyan.withValues(alpha: 0.25)
                            : AppColors.surfaceElevated,
                        side: BorderSide(
                          color: isSelected ? AppColors.primaryCyan : AppColors.border,
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 10),
                      ),
                      child: Text(
                        '$amount',
                        style: TextStyle(
                          fontFamily: 'Orbitron',
                          fontWeight: FontWeight.bold,
                          color: isSelected ? AppColors.primaryCyan : AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ),
                );
              }),
            ],
          ),
          const SizedBox(height: 12),
          // Place Bet Action
          SizedBox(
            height: 52,
            child: ElevatedButton(
              onPressed: widget.isBettingAllowed && widget.currentBalance >= _selectedBet
                  ? () => widget.onPlaceBet(_selectedBet)
                  : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primaryCyan,
                foregroundColor: AppColors.background,
                disabledBackgroundColor: AppColors.surfaceElevated,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: Text(
                'PLACE BET (${Formatters.credits(_selectedBet)})',
                style: AppTextStyles.button.copyWith(
                  color: widget.isBettingAllowed && widget.currentBalance >= _selectedBet
                      ? AppColors.background
                      : AppColors.textSecondary,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
