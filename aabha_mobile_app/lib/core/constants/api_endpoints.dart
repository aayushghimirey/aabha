abstract final class ApiEndpoints {
  static const String health = '/health';

  static const String login = '/auth/login';
  static const String token = '/auth/token';
  static const String dispatch = '/auth/dispatch';

  static const String register = '/users/register';

  static String user(String id) => '/users/$id';
}
