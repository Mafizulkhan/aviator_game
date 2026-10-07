import 'package:flutter_test/flutter_test.dart';
import 'package:zero_gravity/models/user.dart';
import 'package:zero_gravity/models/wallet.dart';
import 'package:zero_gravity/models/round.dart';
import 'package:zero_gravity/models/bet.dart';
import 'package:zero_gravity/models/transaction.dart';
import 'package:zero_gravity/models/fairness.dart';

void main() {
  group('Zero Gravity Domain Models Tests', () {
    test('User serialization and deserialization', () {
      final json = {
        'id': 1,
        'username': 'cyber_pilot',
        'email': 'pilot@zerogravity.game',
        'role': 'PLAYER',
        'status': 'ACTIVE',
        'created_at': '2026-10-07T12:00:00Z',
      };
      final user = User.fromJson(json);
      expect(user.id, 1);
      expect(user.username, 'cyber_pilot');
      expect(user.email, 'pilot@zerogravity.game');
      expect(user.role, 'PLAYER');
      expect(user.status, 'ACTIVE');
    });

    test('Wallet model parsing', () {
      final json = {'balance': 15000};
      final wallet = Wallet.fromJson(json);
      expect(wallet.balance, 15000);
    });

    test('GameRound model parsing and status derivation', () {
      final json = {
        'round_id': 101,
        'server_seed_hash': 'sha256_hash_value',
        'crash_multiplier': 2.45,
        'status': 'running',
      };
      final round = GameRound.fromJson(json);
      expect(round.id, 101);
      expect(round.serverSeedHash, 'sha256_hash_value');
      expect(round.crashMultiplier, 2.45);
      expect(round.status, RoundStatus.running);
    });

    test('Bet model parsing with cashout settlement', () {
      final json = {
        'id': 50,
        'round_id': 101,
        'amount': 200,
        'cashout_multiplier': 2.10,
        'payout': 420,
        'status': 'cashed_out',
        'created_at': '2026-10-07T12:05:00Z',
      };
      final bet = Bet.fromJson(json);
      expect(bet.id, 50);
      expect(bet.roundId, 101);
      expect(bet.amount, 200);
      expect(bet.cashoutMultiplier, 2.10);
      expect(bet.payout, 420);
      expect(bet.status, BetStatus.cashedOut);
    });

    test('WalletTransaction model parsing', () {
      final json = {
        'id': 12,
        'type': 'payout',
        'amount': 420,
        'balance_before': 10000,
        'balance_after': 10420,
        'round_id': 101,
        'created_at': '2026-10-07T12:05:00Z',
      };
      final tx = WalletTransaction.fromJson(json);
      expect(tx.id, 12);
      expect(tx.type, 'payout');
      expect(tx.amount, 420);
      expect(tx.balanceBefore, 10000);
      expect(tx.balanceAfter, 10420);
    });

    test('FairnessRecord model verification parsing', () {
      final json = {
        'round_id': 101,
        'server_seed_hash': 'abc123hash',
        'server_seed': 'secretseed123',
        'crash_multiplier': 2.45,
        'is_fair': true,
      };
      final fairness = FairnessRecord.fromJson(json);
      expect(fairness.roundId, 101);
      expect(fairness.isFair, true);
      expect(fairness.crashMultiplier, 2.45);
      expect(fairness.serverSeed, 'secretseed123');
    });
  });
}
