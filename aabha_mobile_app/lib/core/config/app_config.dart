/// Compile-time configuration.
///
/// `apiBaseUrl` is overridable with `--dart-define=AABHA_API_BASE_URL=...` so a
/// physical device can reach a host machine that is not `localhost`.
abstract final class AppConfig {
  static const String appName = 'aabha';
  static const String appTagline = 'voice companion';

  static const String apiBaseUrl = String.fromEnvironment(
    'AABHA_API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8080',
  );

  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 20);
  static const Duration healthPollInterval = Duration(seconds: 20);
}
