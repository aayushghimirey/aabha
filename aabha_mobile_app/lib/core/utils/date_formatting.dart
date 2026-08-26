/// Date handling for the one date the API takes: `dob`.
///
/// The server types it as a datetime but only ever means a calendar day, so it
/// is sent as `YYYY-MM-DD` — the same shape the web client's date input emits.
extension ApiDateFormatting on DateTime {
  String get apiDate =>
      '${year.toString().padLeft(4, '0')}-${_two(month)}-${_two(day)}';

  /// Midnight local time, which is what a picked calendar day means here.
  DateTime get dateOnly => DateTime(year, month, day);
}

String _two(int value) => value.toString().padLeft(2, '0');

/// Parses a server timestamp, falling back to the epoch rather than throwing:
/// a malformed date is not worth losing a whole session over.
DateTime parseApiDate(Object? value) {
  if (value is String) {
    final parsed = DateTime.tryParse(value);
    if (parsed != null) return parsed;
  }
  return DateTime.fromMillisecondsSinceEpoch(0);
}
