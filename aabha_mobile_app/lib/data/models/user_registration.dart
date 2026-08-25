import '../../core/utils/date_formatting.dart';

/// Mirrors `UserRegister`. The server enforces the lengths; the form mirrors
/// them so a typo is caught before it costs a round trip.
class UserRegistration {
  const UserRegistration({
    required this.username,
    required this.email,
    required this.password,
    required this.dob,
  });

  static const int usernameMin = 3;
  static const int usernameMax = 32;
  static const int passwordMin = 6;
  static const int passwordMax = 128;

  final String username;
  final String email;
  final String password;
  final DateTime dob;

  Map<String, dynamic> toJson() => {
    'username': username,
    'email': email,
    'password': password,
    'dob': dob.apiDate,
  };
}
