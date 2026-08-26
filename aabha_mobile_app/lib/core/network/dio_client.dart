import 'package:dio/dio.dart';

import '../config/app_config.dart';
import 'error_interceptor.dart';

abstract final class DioClient {
  static Dio create({String baseUrl = AppConfig.apiBaseUrl}) {
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: AppConfig.connectTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
        contentType: Headers.jsonContentType,
        responseType: ResponseType.json,
      ),
    );

    dio.interceptors.add(const ErrorInterceptor());
    return dio;
  }
}
