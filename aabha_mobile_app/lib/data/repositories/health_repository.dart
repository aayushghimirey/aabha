import '../../core/network/api_exception.dart';
import '../data_sources/remote/health_remote_data_source.dart';

class HealthRepository {
  const HealthRepository(this._health);

  final HealthRemoteDataSource _health;

  /// A failed poll is an answer, not an error: it means the dot goes red.
  Future<bool> isHealthy() async {
    try {
      return await _health.isHealthy();
    } on ApiException {
      return false;
    }
  }
}
