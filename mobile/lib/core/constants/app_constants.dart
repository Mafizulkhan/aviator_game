import 'package:flutter/material.dart';

class AppColors {
  static const Color background = Color(0xFF0A0A16);
  static const Color surface = Color(0xFF14142B);
  static const Color surfaceElevated = Color(0xFF1E1E3F);
  static const Color primaryCyan = Color(0xFF00F0FF);
  static const Color secondaryPurple = Color(0xFFB026FF);
  static const Color accentGold = Color(0xFFFFD700);
  static const Color dangerRed = Color(0xFFFF3366);
  static const Color successGreen = Color(0xFF00FF88);
  static const Color warningOrange = Color(0xFFFF9900);
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFF8E8EA8);
  static const Color border = Color(0xFF2A2A55);
}

class AppTextStyles {
  static const TextStyle titleLarge = TextStyle(
    fontFamily: 'Orbitron',
    fontSize: 26,
    fontWeight: FontWeight.bold,
    color: AppColors.textPrimary,
    letterSpacing: 1.5,
  );

  static const TextStyle multiplier = TextStyle(
    fontFamily: 'Orbitron',
    fontSize: 54,
    fontWeight: FontWeight.w900,
    color: AppColors.primaryCyan,
  );

  static const TextStyle body = TextStyle(
    fontSize: 14,
    color: AppColors.textSecondary,
  );

  static const TextStyle button = TextStyle(
    fontFamily: 'Orbitron',
    fontSize: 16,
    fontWeight: FontWeight.bold,
    letterSpacing: 1.2,
  );
}
