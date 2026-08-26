import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// One storage instance for the whole app. The v11 defaults are already
/// AES-GCM under a KeyStore-wrapped key, so nothing needs overriding.
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage();
});
