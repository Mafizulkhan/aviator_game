enum RoundStatus { waiting, running, crashed, ended }

RoundStatus parseRoundStatus(String? status) {
  switch (status?.toLowerCase()) {
    case 'running':
      return RoundStatus.running;
    case 'crashed':
      return RoundStatus.crashed;
    case 'ended':
      return RoundStatus.ended;
    default:
      return RoundStatus.waiting;
  }
}

class GameRound {
  final int id;
  final String? serverSeedHash;
  final String? serverSeed;
  final double? crashMultiplier;
  final RoundStatus status;
  final DateTime? startTime;

  GameRound({
    required this.id,
    this.serverSeedHash,
    this.serverSeed,
    this.crashMultiplier,
    required this.status,
    this.startTime,
  });

  factory GameRound.fromJson(Map<String, dynamic> json) {
    return GameRound(
      id: (json['round_id'] ?? json['id']) as int,
      serverSeedHash: json['server_seed_hash'] as String?,
      serverSeed: json['server_seed'] as String?,
      crashMultiplier: (json['crash_multiplier'] as num?)?.toDouble(),
      status: parseRoundStatus(json['status'] as String?),
      startTime: json['start_time'] != null
          ? DateTime.tryParse(json['start_time'].toString())
          : null,
    );
  }
}
