import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../repositories/player_repository.dart';
import '../../core/constants/app_constants.dart';
import '../../core/utils/formatters.dart';
import '../../models/bet.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Bet> _history = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _isLoading = true);
    try {
      final playerRepo = context.read<PlayerRepository>();
      final list = await playerRepo.getPlayerHistory();
      setState(() => _history = list);
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('MISSION HISTORY'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primaryCyan))
          : _history.isEmpty
              ? const Center(
                  child: Text(
                    'No flight history recorded yet.',
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _history.length,
                  itemBuilder: (context, index) {
                    final item = _history[index];
                    final isWin = item.status == BetStatus.cashedOut;

                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'ROUND #AG-${item.roundId}',
                                  style: const TextStyle(
                                    fontFamily: 'Orbitron',
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.primaryCyan,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  Formatters.dateTime(item.createdAt),
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'Bet: ${Formatters.credits(item.amount)}',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                              ],
                            ),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: isWin
                                        ? AppColors.successGreen.withValues(alpha: 0.2)
                                        : AppColors.dangerRed.withValues(alpha: 0.2),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    item.status.name.toUpperCase(),
                                    style: TextStyle(
                                      fontFamily: 'Orbitron',
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      color: isWin ? AppColors.successGreen : AppColors.dangerRed,
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                if (isWin && item.payout != null)
                                  Text(
                                    '+${Formatters.credits(item.payout!)}',
                                    style: const TextStyle(
                                      fontFamily: 'Orbitron',
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                      color: AppColors.accentGold,
                                    ),
                                  )
                                else
                                  Text(
                                    '-${Formatters.credits(item.amount)}',
                                    style: const TextStyle(
                                      fontFamily: 'Orbitron',
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
