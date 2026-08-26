import 'package:dio/dio.dart';

import '../../../core/constants/api_endpoints.dart';
import '../../../core/network/api_guard.dart';
import '../../models/credentials.dart';
import '../../models/livekit_token.dart';
import '../../models/user.dart';

class AuthRemoteDataSource {
  const AuthRemoteDataSource(this._dio);

  final Dio _dio;

  Future<User> login(Credentials credentials) {
    return guardApiCall(() async {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiEndpoints.login,
        data: credentials.toJson(),
      );
      return User.fromJson(response.data!);
    });
  }

  Future<LivekitToken> issueToken(Credentials credentials) {
    return guardApiCall(() async {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiEndpoints.token,
        data: credentials.toJson(),
      );
      return LivekitToken.fromJson(response.data!);
    });
  }

  /// Starts an agent job for the room the token grants.
  ///
  /// Called on every connect, not just at sign-in: room names are stable per
  /// user, so a rejoin can land in a room LiveKit already created — one that
  /// fires no automatic dispatch of its own.
  Future<void> dispatch(String livekitToken) {
    return guardApiCall(() async {
      await _dio.post<void>(
        ApiEndpoints.dispatch,
        options: Options(
          headers: {'Authorization': 'Bearer $livekitToken'},
        ),
      );
    });
  }
}
