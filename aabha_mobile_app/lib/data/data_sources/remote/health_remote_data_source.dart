import 'package:dio/dio.dart';

import '../../../core/constants/api_endpoints.dart';
import '../../../core/network/api_guard.dart';

class HealthRemoteDataSource {
  const HealthRemoteDataSource(this._dio);

  final Dio _dio;

  Future<bool> isHealthy() {
    return guardApiCall(() async {
      final response = await _dio.get<Map<String, dynamic>>(
        ApiEndpoints.health,
      );
      return response.data?['status'] == 'ok';
    });
  }
}
