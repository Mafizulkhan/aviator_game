import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../repositories/auth_repository.dart';
import '../../repositories/player_repository.dart';
import '../../core/constants/app_constants.dart';
import '../../core/utils/formatters.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  int _balance = 0;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final playerRepo = context.read<PlayerRepository>();
      final wallet = await playerRepo.getBalance();
      setState(() => _balance = wallet.balance);
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthRepository>().currentUser;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('PILOT DOSSIER'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primaryCyan))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  // Pilot Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20.0),
                      child: Column(
                        children: [
                          Container(
                            width: 80,
                            height: 80,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: AppColors.surfaceElevated,
                              border: Border.all(color: AppColors.primaryCyan, width: 2),
                            ),
                            child: const Center(
                              child: Icon(Icons.person, size: 48, color: AppColors.primaryCyan),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            user?.username.toUpperCase() ?? 'PILOT',
                            style: const TextStyle(
                              fontFamily: 'Orbitron',
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            user?.email ?? '',
                            style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                          ),
                          const SizedBox(height: 16),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                            decoration: BoxDecoration(
                              color: AppColors.accentGold.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppColors.accentGold),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.stars, color: AppColors.accentGold, size: 18),
                                const SizedBox(width: 8),
                                Text(
                                  'Balance: ${Formatters.credits(_balance)}',
                                  style: const TextStyle(
                                    fontFamily: 'Orbitron',
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.accentGold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Pilot Stats
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'PILOT METRICS',
                            style: TextStyle(
                              fontFamily: 'Orbitron',
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: AppColors.primaryCyan,
                            ),
                          ),
                          const SizedBox(height: 12),
                          _StatRow(label: 'Security Role', value: user?.role ?? 'PLAYER'),
                          _StatRow(label: 'Account Status', value: user?.status ?? 'ACTIVE'),
                          _StatRow(label: 'Registered On', value: Formatters.dateTime(user?.createdAt ?? DateTime.now())),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

class _StatRow extends StatelessWidget {
  final String label;
  final String value;

  const _StatRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          Text(
            value,
            style: const TextStyle(
              fontFamily: 'Orbitron',
              color: AppColors.textPrimary,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
