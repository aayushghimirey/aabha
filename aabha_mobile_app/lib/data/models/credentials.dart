/// Mirrors `AuthRequest`.
///
/// Deliberately never persisted: login and token are two calls against the
/// same credentials, so the password only has to live as long as the sign-in.
class Credentials {
  const Credentials({required this.username, required this.password});

  final String username;
  final String password;

  Map<String, dynamic> toJson() => {
    'username': username,
    'password': password,
  };
}
