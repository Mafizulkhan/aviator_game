class WalletTransaction {
  final int id;
  final String type;
  final int amount;
  final int balanceBefore;
  final int balanceAfter;
  final int? roundId;
  final DateTime createdAt;

  WalletTransaction({
    required this.id,
    required this.type,
    required this.amount,
    required this.balanceBefore,
    required this.balanceAfter,
    this.roundId,
    required this.createdAt,
  });

  factory WalletTransaction.fromJson(Map<String, dynamic> json) {
    return WalletTransaction(
      id: (json['id'] ?? 0) as int,
      type: json['type'] as String? ?? 'transaction',
      amount: (json['amount'] as num?)?.toInt() ?? 0,
      balanceBefore: (json['balance_before'] as num?)?.toInt() ?? 0,
      balanceAfter: (json['balance_after'] as num?)?.toInt() ?? 0,
      roundId: json['round_id'] as int?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}
