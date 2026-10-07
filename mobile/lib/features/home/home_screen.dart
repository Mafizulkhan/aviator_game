import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../repositories/auth_repository.dart';
import '../../repositories/player_repository.dart';
import '../../core/constants/app_constants.dart';
import '../../widgets/balance_display.dart';
import '../../widgets/game_background.dart';
import '../game/game_screen.dart';
import '../history/history_screen.dart';
import '../profile/profile_screen.dart';
import '../settings/settings_screen.dart';
import '../tutorial/tutorial_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _balance = 10000;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _fetchBalance();
  }

  Future<void> _fetchBalance() async {
    setState(() => _isLoading = true);
    try {
      final playerRepo = context.read<PlayerRepository>();
      final wallet = await playerRepo.getBalance();
      setState(() => _balance = wallet.balance);
    } catch (_) {
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthRepository>().currentUser;

    return Scaffold(
      body: GameBackground(
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Top Header Row
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'PILOT',
                          style: TextStyle(
                            fontFamily: 'Orbitron',
                            fontSize: 10,
                            color: AppColors.textSecondary,
                            letterSpacing: 1.2,
                          ),
                        ),
                        Text(
                          user?.username.toUpperCase() ?? 'CYBER_PILOT',
                          style: const TextStyle(
                            fontFamily: 'Orbitron',
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: AppColors.primaryCyan,
                          ),
                        ),
                      ],
                    ),
                    BalanceDisplay(balance: _balance),
                  ],
                ),
                const Spacer(),

                // Center Logo & Graphic
                Center(
                  child: Column(
                    children: [
                      Container(
                        width: 120,
                        height: 120,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.surface,
                          border: Border.all(color: AppColors.primaryCyan, width: 2),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primaryCyan.withValues(alpha: 0.35),
                              blurRadius: 35,
                              spreadRadius: 5,
                            ),
                          ],
                        ),
                        child: const Center(
                          child: Text('🕸️', style: TextStyle(fontSize: 60)),
                        ),
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        'ZERO GRAVITY',
                        style: AppTextStyles.titleLarge,
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Cyber Spider Crash Arena',
                        style: TextStyle(color: AppColors.textSecondary, letterSpacing: 1.5),
                      ),
                    ],
                  ),
                ),
                const Spacer(),

                // Action Menu
                SizedBox(
                  height: 64,
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const GameScreen()),
                      ).then((_) => _fetchBalance());
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primaryCyan,
                      foregroundColor: AppColors.background,
                      elevation: 8,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                    child: const Text(
                      'ENTER ARENA',
                      style: TextStyle(
                        fontFamily: 'Orbitron',
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 2.0,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                // Quick Navigation Grid
                Row(
                  children: [
                    Expanded(
                      child: _NavButton(
                        icon: Icons.history,
                        label: 'HISTORY',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const HistoryScreen()),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _NavButton(
                        icon: Icons.person_outline,
                        label: 'PROFILE',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const ProfileScreen()),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: _NavButton(
                        icon: Icons.help_outline,
                        label: 'HOW TO PLAY',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const TutorialScreen()),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _NavButton(
                        icon: Icons.settings_outlined,
                        label: 'SETTINGS',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const SettingsScreen()),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _NavButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: OutlinedButton.icon(
        onPressed: onTap,
        icon: Icon(icon, size: 18, color: AppColors.primaryCyan),
        label: Text(
          label,
          style: const TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 11,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        style: OutlinedButton.styleFrom(
          backgroundColor: AppColors.surface,
          side: const BorderSide(color: AppColors.border),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }
}
