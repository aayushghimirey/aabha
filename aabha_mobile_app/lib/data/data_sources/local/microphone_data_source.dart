import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../core/network/api_exception.dart';

/// Asked for before the room is opened.
///
/// Publishing the mic would prompt on its own, but it does so from inside the
/// connect, where a refusal surfaces as an opaque failure. Asking first turns
/// "no" into something the screen can explain.
class MicrophoneDataSource {
  const MicrophoneDataSource();

  /// Only the mobile platforms have a permission to ask for. Desktop has no
  /// permission_handler implementation at all, so asking there throws a
  /// missing-plugin error and takes down a connect that would have worked —
  /// the capture prompt handles it instead.
  static const Set<TargetPlatform> _asks = {
    TargetPlatform.android,
    TargetPlatform.iOS,
  };

  Future<void> ensurePermission() async {
    if (kIsWeb || !_asks.contains(defaultTargetPlatform)) return;

    final status = await Permission.microphone.request();
    if (status.isGranted) return;

    throw ApiException(
      status.isPermanentlyDenied
          ? 'aabha cannot hear you without microphone access.\n'
                'Enable it for aabha in your device settings.'
          : 'aabha cannot hear you without microphone access.',
    );
  }
}
