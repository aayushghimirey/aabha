import '../data_sources/remote/auth_remote_data_source.dart';
import '../data_sources/remote/user_remote_data_source.dart';
import '../models/credentials.dart';
import '../models/session.dart';
import '../models/user_registration.dart';
import 'session_repository.dart';

class AuthRepository {
  const AuthRepository({
    required this._auth,
    required this._users,
    required this._sessions,
  });

  final AuthRemoteDataSource _auth;
  final UserRemoteDataSource _users;
  final SessionRepository _sessions;

  /// Login and token are two calls against the same credentials: the first
  /// confirms who you are, the second buys the LiveKit grant. Doing both here
  /// means the password never has to be held anywhere.
  Future<Session> signIn(String username, String password) async {
    final credentials = Credentials(username: username, password: password);

    final user = await _auth.login(credentials);
    final token = await _auth.issueToken(credentials);

    final session = Session(user: user, token: token);
    await _sessions.save(session);
    return session;
  }

  /// Registering signs you straight in, which is also the only way to get a
  /// LiveKit grant — `POST /users/register` hands back a user and nothing else.
  Future<Session> register(UserRegistration registration) async {
    await _users.register(registration);
    return signIn(registration.username, registration.password);
  }

  Future<void> signOut() => _sessions.clear();

  Future<void> dispatchAgent(Session session) =>
      _auth.dispatch(session.token.token);
}
