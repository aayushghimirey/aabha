import '../../data/models/user_registration.dart';

/// Client-side mirrors of the server's own rules.
///
/// The API is still the authority — these only save a round trip for the
/// mistakes that are obvious before one is spent.
abstract final class Validators {
  static final RegExp _email = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

  static String? username(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return 'Username is required';
    if (text.length < UserRegistration.usernameMin) {
      return 'At least ${UserRegistration.usernameMin} characters';
    }
    if (text.length > UserRegistration.usernameMax) {
      return 'At most ${UserRegistration.usernameMax} characters';
    }
    return null;
  }

  static String? email(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return 'Email is required';
    if (!_email.hasMatch(text)) return 'That does not look like an email';
    return null;
  }

  static String? password(String? value) {
    final text = value ?? '';
    if (text.isEmpty) return 'Password is required';
    if (text.length < UserRegistration.passwordMin) {
      return 'At least ${UserRegistration.passwordMin} characters';
    }
    if (text.length > UserRegistration.passwordMax) {
      return 'At most ${UserRegistration.passwordMax} characters';
    }
    return null;
  }

  /// Sign-in only checks that something was typed: the rules may have been
  /// different when the account was made, and the server decides anyway.
  static String? required(String? value, String label) {
    if ((value ?? '').trim().isEmpty) return '$label is required';
    return null;
  }
}
