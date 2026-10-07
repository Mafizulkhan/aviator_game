import 'package:intl/intl.dart';

class Formatters {
  static final _numberFormat = NumberFormat('#,##0', 'en_US');

  static String credits(int amount) {
    return '${_numberFormat.format(amount)} CR';
  }

  static String multiplier(double value) {
    return '${value.toStringAsFixed(2)}x';
  }

  static String dateTime(DateTime dt) {
    return DateFormat('HH:mm:ss dd/MM').format(dt.toLocal());
  }
}
