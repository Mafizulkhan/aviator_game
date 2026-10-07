import 'package:flutter/material.dart';
import '../../core/constants/app_constants.dart';

class TutorialScreen extends StatelessWidget {
  const TutorialScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('HOW TO PLAY'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: const [
          _StepCard(
            step: '01',
            title: 'PLACE YOUR BET',
            desc: 'Select your virtual credit bet before the round starts. Minimum bet is 10 CR.',
            icon: Icons.touch_app,
          ),
          SizedBox(height: 14),
          _StepCard(
            step: '02',
            title: 'WATCH MULTIPLIER RISE',
            desc: 'The cyber spider begins climbing as the multiplier scales from 1.00x upward.',
            icon: Icons.trending_up,
          ),
          SizedBox(height: 14),
          _StepCard(
            step: '03',
            title: 'CASH OUT IN TIME',
            desc: 'Tap Cash Out before the spider crashes. You secure your bet multiplied by the current rate.',
            icon: Icons.monetization_on,
          ),
          SizedBox(height: 14),
          _StepCard(
            step: '04',
            title: 'PROVABLY FAIR SYSTEM',
            desc: 'Every round crash point is cryptographically sealed with SHA256 before the round starts.',
            icon: Icons.verified_user,
          ),
        ],
      ),
    );
  }
}

class _StepCard extends StatelessWidget {
  final String step;
  final String title;
  final String desc;
  final IconData icon;

  const _StepCard({
    required this.step,
    required this.title,
    required this.desc,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.primaryCyan),
              ),
              child: Icon(icon, color: AppColors.primaryCyan, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'STEP $step — $title',
                    style: const TextStyle(
                      fontFamily: 'Orbitron',
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: AppColors.accentGold,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    desc,
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
