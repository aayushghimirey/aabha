import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/session.dart';
import '../../data/models/user.dart';
import '../../data/models/user_registration.dart';
import '../../providers/repository_providers.dart';

/// The signed-in session, and the single source of truth for whether the app
/// is past the auth wall.
///
/// `build` doubles as the startup gate: while it runs, the router holds on the
/// splash screen rather than flashing the sign-in form at someone who is
/// already signed in.
class SessionController extends AsyncNotifier<Session?> {
  @override
  Future<Session?> build() async {
    // The stored base URL has to reach Dio before anything is requested with
    // it — including the restore below, indirectly, on the next call out.
    await ref.read(settingsRepositoryProvider).loadApiBaseUrl();

    return ref.read(sessionRepositoryProvider).restore();
  }

  /// Failures are rethrown rather than parked in [state]: a bad password is
  /// the form's problem to report, and turning the session itself into an
  /// error would bounce the router somewhere nobody asked to go.
  Future<void> signIn(String username, String password) async {
    final session = await ref
        .read(authRepositoryProvider)
        .signIn(username, password);

    state = AsyncData(session);
  }

  Future<void> register(UserRegistration registration) async {
    final session = await ref.read(authRepositoryProvider).register(registration);
    state = AsyncData(session);
  }

  Future<void> signOut() async {
    await ref.read(authRepositoryProvider).signOut();
    state = const AsyncData(null);
  }

  /// Saving the profile changes the user everywhere it is shown, so the stored
  /// session is rewritten with it — the LiveKit grant is untouched.
  Future<void> replaceUser(User user) async {
    final current = state.value;
    if (current == null) return;

    final updated = current.copyWith(user: user);
    await ref.read(sessionRepositoryProvider).save(updated);
    state = AsyncData(updated);
  }
}
