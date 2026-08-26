import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/constants/storage_keys.dart';
import '../../models/session.dart';

/// Keeps the signed-in session across launches.
///
/// The web client parks this in `sessionStorage`, which dies with the tab. An
/// app has no tab to close, and the LiveKit grant is a bearer credential, so
/// it goes to the keychain / EncryptedSharedPreferences instead.
class SessionLocalDataSource {
  const SessionLocalDataSource(this._storage);

  final FlutterSecureStorage _storage;

  Future<Session?> read() async {
    final raw = await _storage.read(key: StorageKeys.session);
    if (raw == null || raw.isEmpty) return null;

    try {
      return Session.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      // A session written by an older build is not worth crashing over, and
      // signing in again rewrites it.
      await clear();
      return null;
    }
  }

  Future<void> write(Session session) {
    return _storage.write(
      key: StorageKeys.session,
      value: jsonEncode(session.toJson()),
    );
  }

  Future<void> clear() => _storage.delete(key: StorageKeys.session);
}
