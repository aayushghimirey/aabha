import 'package:dio/dio.dart';

import 'api_exception.dart';

/// Turns every Dio failure into an [ApiException] carrying a readable message.
///
/// FastAPI reports validation failures as a list of `{loc, msg}` and everything
/// else as a plain `detail` string; both are flattened to one line of text.
class ErrorInterceptor extends Interceptor {
  const ErrorInterceptor();

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    handler.reject(
      DioException(
        requestOptions: err.requestOptions,
        response: err.response,
        type: err.type,
        error: _translate(err),
      ),
    );
  }

  ApiException _translate(DioException err) {
    final status = err.response?.statusCode;

    if (status == null) {
      final host = err.requestOptions.baseUrl;
      return ApiException(
        'Cannot reach the API at $host.\n'
        'Check that the server is running and reachable from this device.',
      );
    }

    return ApiException(
      describeDetail(err.response?.data, status),
      statusCode: status,
    );
  }
}

String describeDetail(Object? payload, int status) {
  final detail = payload is Map ? payload['detail'] : null;

  if (detail is String && detail.isNotEmpty) return detail;

  if (detail is List) {
    final lines = detail.whereType<Map>().map((entry) {
      final loc = entry['loc'];
      final field = loc is List && loc.isNotEmpty ? loc.last : 'request';
      return '$field: ${entry['msg']}';
    });
    if (lines.isNotEmpty) return lines.join('\n');
  }

  return 'Request failed ($status)';
}
