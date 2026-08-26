/// A network or API failure with a message that is safe to show to the user.
///
/// `statusCode` is null when the request never reached the server.
class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  bool get isUnauthorized => statusCode == 401;
  bool get isUnreachable => statusCode == null;

  @override
  String toString() => 'ApiException($statusCode): $message';
}
