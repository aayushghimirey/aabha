import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/router/app_router.dart';
import 'session_providers.dart';

/// Bridges Riverpod to GoRouter.
///
/// The router is built once and kept: rebuilding it on every session change
/// would throw away the navigation stack. Instead a [ChangeNotifier] pokes it
/// to re-run its guard, which reads the session back through `ref.read`.
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _RouterRefresh();

  ref.listen(sessionControllerProvider, (_, _) => refresh.poke());

  final router = AppRouter.create(
    refresh: refresh,
    isRestoring: () => ref.read(sessionControllerProvider).isLoading,
    isSignedIn: () => ref.read(sessionControllerProvider).value != null,
  );

  ref.onDispose(() {
    router.dispose();
    refresh.dispose();
  });

  return router;
});

class _RouterRefresh extends ChangeNotifier {
  void poke() => notifyListeners();
}
