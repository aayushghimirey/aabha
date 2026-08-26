import '../data_sources/remote/user_remote_data_source.dart';
import '../models/user.dart';
import '../models/user_update.dart';

class UserRepository {
  const UserRepository(this._users);

  final UserRemoteDataSource _users;

  Future<User> fetch(String userId) => _users.fetch(userId);

  Future<User> update(String userId, UserUpdate update) =>
      _users.update(userId, update);
}
