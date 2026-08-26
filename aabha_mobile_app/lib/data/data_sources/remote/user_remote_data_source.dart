import 'package:dio/dio.dart';

import '../../../core/constants/api_endpoints.dart';
import '../../../core/network/api_guard.dart';
import '../../models/user.dart';
import '../../models/user_registration.dart';
import '../../models/user_update.dart';

class UserRemoteDataSource {
  const UserRemoteDataSource(this._dio);

  final Dio _dio;

  Future<User> register(UserRegistration registration) {
    return guardApiCall(() async {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiEndpoints.register,
        data: registration.toJson(),
      );
      return User.fromJson(response.data!);
    });
  }

  Future<User> fetch(String userId) {
    return guardApiCall(() async {
      final response = await _dio.get<Map<String, dynamic>>(
        ApiEndpoints.user(userId),
      );
      return User.fromJson(response.data!);
    });
  }

  Future<User> update(String userId, UserUpdate update) {
    return guardApiCall(() async {
      final response = await _dio.put<Map<String, dynamic>>(
        ApiEndpoints.user(userId),
        data: update.toJson(),
      );
      return User.fromJson(response.data!);
    });
  }
}
