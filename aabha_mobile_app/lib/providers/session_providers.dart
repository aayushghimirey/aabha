import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/session.dart';
import '../data/models/user.dart';
import '../presentation/controllers/session_controller.dart';

final sessionControllerProvider =
    AsyncNotifierProvider<SessionController, Session?>(SessionController.new);

/// The session once it has settled — null while restoring, and null when
/// signed out. Screens behind the auth wall can rely on it being there.
final currentSessionProvider = Provider<Session?>((ref) {
  return ref.watch(sessionControllerProvider).value;
});

final currentUserProvider = Provider<User?>((ref) {
  return ref.watch(currentSessionProvider)?.user;
});
