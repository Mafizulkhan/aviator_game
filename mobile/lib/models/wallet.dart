class Wallet {
  final int balance;

  Wallet({required this.balance});

  factory Wallet.fromJson(Map<String, dynamic> json) {
    return Wallet(
      balance: (json['balance'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'balance': balance,
      };
}
