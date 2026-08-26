import '../data_sources/local/session_local_data_source.dart';
import '../models/session.dart';

/// Owns the stored session, and nothing else.
///
/// Kept apart from [AuthRepository] because the profile screen also has to
/// rewrite the session — a saved username changes what is shown everywhere —
/// without going anywhere near the sign-in path.
class SessionRepository {
  const SessionRepository(this._local);

  final SessionLocalDataSource _local;

  Future<Session?> restore() => _local.read();

  Future<void> save(Session session) => _local.write(session);

  Future<void> clear() => _local.clear();
}
