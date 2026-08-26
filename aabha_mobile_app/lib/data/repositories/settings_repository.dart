import 'package:dio/dio.dart';

import '../data_sources/local/settings_local_data_source.dart';

class SettingsRepository {
  const SettingsRepository({required this._local, required this._dio});

  final SettingsLocalDataSource _local;
  final Dio _dio;

  String get apiBaseUrl => _dio.options.baseUrl;

  /// Applies any stored override to the live client. Called once at startup,
  /// before the first request goes out.
  Future<String> loadApiBaseUrl() async {
    final stored = await _local.readApiBaseUrl();
    if (stored != null) _dio.options.baseUrl = stored;
    return apiBaseUrl;
  }

  Future<String> setApiBaseUrl(String value) async {
    final normalized = normalizeBaseUrl(value);
    _dio.options.baseUrl = normalized;
    await _local.writeApiBaseUrl(normalized);
    return normalized;
  }

  /// Every endpoint starts with a slash, so a trailing one would double up.
  static String normalizeBaseUrl(String value) {
    var trimmed = value.trim();
    while (trimmed.endsWith('/')) {
      trimmed = trimmed.substring(0, trimmed.length - 1);
    }
    return trimmed;
  }
}
