import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_exception.dart';
import '../../data/models/user_registration.dart';
import '../../providers/session_providers.dart';

enum AuthMode { signIn, register }

class AuthFormState {
  const AuthFormState({
    this.mode = AuthMode.signIn,
    this.isSubmitting = false,
    this.error,
  });

  final AuthMode mode;
  final bool isSubmitting;
  final String? error;

  AuthFormState copyWith({
    AuthMode? mode,
    bool? isSubmitting,
    String? error,
    bool clearError = false,
  }) {
    return AuthFormState(
      mode: mode ?? this.mode,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Owns only what the sign-in card shows: which tab, whether a submit is in
/// flight, and the last failure. The session itself lives in
/// [SessionController], so this can be thrown away when the screen is.
class AuthFormController extends Notifier<AuthFormState> {
  @override
  AuthFormState build() => const AuthFormState();

  void switchMode(AuthMode mode) {
    if (state.mode == mode) return;
    state = state.copyWith(mode: mode, clearError: true);
  }

  Future<bool> signIn(String username, String password) {
    return _submit(
      () => ref
          .read(sessionControllerProvider.notifier)
          .signIn(username.trim(), password),
    );
  }

  Future<bool> register(UserRegistration registration) {
    return _submit(
      () => ref.read(sessionControllerProvider.notifier).register(registration),
    );
  }

  /// Returns whether it worked, so the screen can decide what to do next
  /// without having to read the state back.
  ///
  /// Nothing is written back on success: the session change redirects this
  /// screen away and disposes this controller with it, so the only safe thing
  /// to do is leave the button busy on the way out.
  Future<bool> _submit(Future<void> Function() action) async {
    state = state.copyWith(isSubmitting: true, clearError: true);

    try {
      await action();
      return true;
    } on ApiException catch (error) {
      state = state.copyWith(isSubmitting: false, error: error.message);
      return false;
    } catch (_) {
      state = state.copyWith(
        isSubmitting: false,
        error: 'Something went wrong. Please try again.',
      );
      return false;
    }
  }
}
