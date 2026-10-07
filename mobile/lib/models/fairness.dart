class FairnessRecord {
  final int roundId;
  final String serverSeedHash;
  final String? serverSeed;
  final double crashMultiplier;
  final bool isFair;

  FairnessRecord({
    required this.roundId,
    required this.serverSeedHash,
    this.serverSeed,
    required this.crashMultiplier,
    required this.isFair,
  });

  factory FairnessRecord.fromJson(Map<String, dynamic> json) {
    return FairnessRecord(
      roundId: (json['round_id'] ?? json['id'] ?? 0) as int,
      serverSeedHash: json['server_seed_hash'] as String? ?? '',
      serverSeed: json['server_seed'] as String?,
      crashMultiplier: (json['crash_multiplier'] as num?)?.toDouble() ?? 1.0,
      isFair: json['is_fair'] as bool? ?? true,
    );
  }
}
