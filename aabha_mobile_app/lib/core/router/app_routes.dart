abstract final class AppRoutes {
  static const String splash = '/splash';
  static const String auth = '/auth';

  /// Branches of the signed-in shell.
  static const String talk = '/';
  static const String profile = '/profile';

  static const String splashName = 'splash';
  static const String authName = 'auth';
  static const String talkName = 'talk';
  static const String profileName = 'profile';

  /// Where a redirect sends someone who has just signed in.
  static const String home = talk;
}
