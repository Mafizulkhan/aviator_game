enum BetStatus { placed, cashedOut, lost, refunded }

BetStatus parseBetStatus(String? status) {
  switch (status?.toLowerCase()) {
    case 'cashed_out':
      return BetStatus.cashedOut;
    case 'lost':
      return BetStatus.lost;
    case 'refunded':
      return BetStatus.refunded;
    default:
      return BetStatus.placed;
  }
}

class Bet {
  final int id;
  final int roundId;
  final int amount;
  final double? cashoutMultiplier;
  final int? payout;
  final BetStatus status;
  final DateTime createdAt;

  Bet({
    required this.id,
    required this.roundId,
    required this.amount,
    this.cashoutMultiplier,
    this.payout,
    required this.status,
    required this.createdAt,
  });

  factory Bet.fromJson(Map<String, dynamic> json) {
    return Bet(
      id: (json['id'] ?? 0) as int,
      roundId: (json['round_id'] ?? 0) as int,
      amount: (json['amount'] as num?)?.toInt() ?? 0,
      cashoutMultiplier: (json['cashout_multiplier'] as num?)?.toDouble(),
      payout: (json['payout'] as num?)?.toInt(),
      status: parseBetStatus(json['status'] as String?),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}
