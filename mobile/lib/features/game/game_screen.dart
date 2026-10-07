import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../repositories/game_repository.dart';
import '../../repositories/player_repository.dart';
import '../../core/constants/app_constants.dart';
import '../../models/round.dart';
import '../../widgets/cyber_spider.dart';
import '../../widgets/multiplier_display.dart';
import '../../widgets/cashout_button.dart';
import '../../widgets/bet_panel.dart';
import '../../widgets/game_background.dart';
import '../../widgets/connection_status.dart';
import '../../widgets/balance_display.dart';

class GameScreen extends StatefulWidget {
  const GameScreen({super.key});

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  int _balance = 10000;
  String? _statusBanner;

  @override
  void initState() {
    super.initState();
    _fetchBalance();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<GameRepository>().connectWebSocket();
    });
  }

  Future<void> _fetchBalance() async {
    try {
      final playerRepo = context.read<PlayerRepository>();
      final wallet = await playerRepo.getBalance();
      if (mounted) {
        setState(() => _balance = wallet.balance);
      }
    } catch (_) {}
  }

  Future<void> _handlePlaceBet(int amount) async {
    final gameRepo = context.read<GameRepository>();
    final round = gameRepo.currentRound;
    final roundId = round?.id ?? 1;

    try {
      await gameRepo.placeBet(roundId: roundId, amount: amount);
      setState(() {
        _balance -= amount;
        _statusBanner = 'BET PLACED FOR NEXT ROUND';
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e.toString()),
            backgroundColor: AppColors.dangerRed,
          ),
        );
      }
    }
  }

  Future<void> _handleCashout() async {
    final gameRepo = context.read<GameRepository>();
    final round = gameRepo.currentRound;
    if (round == null) return;

    try {
      final res = await gameRepo.cashOut(roundId: round.id);
      final payout = (res['payout'] as num?)?.toInt() ?? 0;
      await _fetchBalance();
      setState(() {
        _statusBanner = 'CASHED OUT! +$payout CR';
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e.toString()),
            backgroundColor: AppColors.dangerRed,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final gameRepo = context.watch<GameRepository>();
    final isRunning = gameRepo.gameStatus == RoundStatus.running;
    final isWaiting = gameRepo.gameStatus == RoundStatus.waiting || gameRepo.gameStatus == RoundStatus.ended;
    final hasActiveBet = gameRepo.activeBet != null && !gameRepo.isCashedOut && isRunning;

    return Scaffold(
      body: GameBackground(
        child: SafeArea(
          child: Column(
            children: [
              // Top HUD
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back_ios_new, color: AppColors.textPrimary, size: 20),
                      onPressed: () => Navigator.pop(context),
                    ),
                    BalanceDisplay(balance: _balance),
                    ConnectionStatusWidget(state: gameRepo.connectionState),
                  ],
                ),
              ),

              // Round Info Header
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.surface.withValues(alpha: 0.8),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'ROUND: AG-${gameRepo.currentRound?.id ?? "---"}',
                      style: const TextStyle(
                        fontFamily: 'Orbitron',
                        fontSize: 11,
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'STATUS: ${gameRepo.gameStatus.name.toUpperCase()}',
                      style: TextStyle(
                        fontFamily: 'Orbitron',
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: isRunning ? AppColors.primaryCyan : AppColors.accentGold,
                      ),
                    ),
                  ],
                ),
              ),

              // Game Arena Display
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CyberSpiderWidget(
                        status: gameRepo.gameStatus,
                        multiplier: gameRepo.currentMultiplier,
                      ),
                      const SizedBox(height: 18),
                      MultiplierDisplay(
                        multiplier: gameRepo.currentMultiplier,
                        status: gameRepo.gameStatus,
                      ),
                    ],
                  ),
                ),
              ),

              // Status notification banner
              if (_statusBanner != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Text(
                    _statusBanner!,
                    style: const TextStyle(
                      fontFamily: 'Orbitron',
                      fontSize: 12,
                      color: AppColors.accentGold,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),

              // Bottom Interaction Controls
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                child: isRunning && hasActiveBet
                    ? CashoutButton(
                        betAmount: gameRepo.activeBet!.amount,
                        currentMultiplier: gameRepo.currentMultiplier,
                        isEnabled: isRunning && !gameRepo.isCashedOut,
                        isCashedOut: gameRepo.isCashedOut,
                        cashedOutPayout: gameRepo.lastPayout,
                        onCashout: _handleCashout,
                      )
                    : BetPanel(
                        currentBalance: _balance,
                        isBettingAllowed: isWaiting,
                        onPlaceBet: _handlePlaceBet,
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
