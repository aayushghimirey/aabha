import 'package:permission_handler/permission_handler.dart';

import '../../../core/network/api_exception.dart';

/// Asked for before the room is opened.
///
/// Publishing the mic would prompt on its own, but it does so from inside the
/// connect, where a refusal surfaces as an opaque failure. Asking first turns
/// "no" into something the screen can explain.
class MicrophoneDataSource {
  const MicrophoneDataSource();

  Future<void> ensurePermission() async {
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
