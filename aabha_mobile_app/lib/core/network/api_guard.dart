import 'package:dio/dio.dart';

import 'api_exception.dart';

/// Runs a Dio call and lets only [ApiException] escape.
///
/// [ErrorInterceptor] has already translated the failure; this unwraps it so
/// nothing above the data layer ever has to know Dio exists.
Future<T> guardApiCall<T>(Future<T> Function() request) async {
  try {
    return await request();
  } on DioException catch (err) {
    final translated = err.error;
    if (translated is ApiException) throw translated;

    throw ApiException(
      err.message ?? 'Request failed',
      statusCode: err.response?.statusCode,
    );
  }
}
