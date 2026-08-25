import '../../core/utils/date_formatting.dart';

/// Mirrors `UserUpdate` — a full replacement, so every field is required.
class UserUpdate {
  const UserUpdate({
    required this.username,
    required this.email,
    required this.dob,
  });

  final String username;
  final String email;
  final DateTime dob;

  Map<String, dynamic> toJson() => {
    'username': username,
    'email': email,
    'dob': dob.apiDate,
  };
}
