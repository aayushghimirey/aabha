import 'package:flutter/foundation.dart';
import 'package:go_router/go_router.dart';

import '../../presentation/screens/auth/auth_screen.dart';
import '../../presentation/screens/home/home_screen.dart';
import '../../presentation/screens/splash/splash_screen.dart';
import 'app_routes.dart';

abstract final class AppRouter {
  /// The guard is fed by callbacks rather than by the session itself, so the
  /// routing config stays unaware of what a session is made of — Riverpod
  /// wires the two together in `routerProvider`.
  static GoRouter create({
    required Listenable refresh,
    required bool Function() isRestoring,
    required bool Function() isSignedIn,
  }) {
    return GoRouter(
      initialLocation: AppRoutes.splash,
      refreshListenable: refresh,
      redirect: (context, state) {
        final location = state.matchedLocation;

        // Nothing is known yet — hold rather than guess, or an already
        // signed-in user gets a flash of the sign-in form.
        if (isRestoring()) {
          return location == AppRoutes.splash ? null : AppRoutes.splash;
        }

        if (!isSignedIn()) {
          return location == AppRoutes.auth ? null : AppRoutes.auth;
        }

        // Signed in, but sitting somewhere that only exists for the signed
        // out — the splash included, which has nothing left to wait for.
        if (location == AppRoutes.auth || location == AppRoutes.splash) {
          return AppRoutes.home;
        }

        return null;
      },
      routes: [
        GoRoute(
          path: AppRoutes.splash,
          name: AppRoutes.splashName,
          builder: (context, state) => const SplashScreen(),
        ),
        GoRoute(
          path: AppRoutes.auth,
          name: AppRoutes.authName,
          builder: (context, state) => const AuthScreen(),
        ),
        GoRoute(
          path: AppRoutes.home,
          name: AppRoutes.homeName,
          builder: (context, state) => const HomeScreen(),
        ),
      ],
    );
  }
}
