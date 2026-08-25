import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/constants/storage_keys.dart';

/// The API base URL, which the web client keeps editable in its header.
///
/// A phone has no address bar to correct, and the host it should reach differs
/// between an emulator, a LAN device, and a deployment — so it stays settable
/// at runtime rather than baked in at build time.
class SettingsLocalDataSource {
  const SettingsLocalDataSource(this._storage);

  final FlutterSecureStorage _storage;

  Future<String?> readApiBaseUrl() async {
    final value = await _storage.read(key: StorageKeys.apiBaseUrl);
    return (value == null || value.isEmpty) ? null : value;
  }

  Future<void> writeApiBaseUrl(String baseUrl) {
    return _storage.write(key: StorageKeys.apiBaseUrl, value: baseUrl);
  }
}
