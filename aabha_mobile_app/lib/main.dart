import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livekit_client/livekit_client.dart';

import 'app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await _prepareAudio();

  runApp(const ProviderScope(child: AabhaApp()));
}

/// Claims the platform audio session for two-way voice before WebRTC starts.
///
/// This has to happen at launch, not at connect: Android reads these
/// attributes when WebRTC builds its audio device module, and that happens
/// once. Left to the default the module comes up configured for media
/// playback, which captures the microphone until the agent first speaks and
/// then stops — one turn in, and silence after.
Future<void> _prepareAudio() async {
  if (kIsWeb) return;

  await LiveKitClient.initialize(
    // Marked experimental by the SDK, and still the only way to set this: the
    // attributes are read once, at WebRTC init, so there is no later hook.
    // ignore: experimental_member_use
    initialAudioSessionOptions: const AudioSessionOptions.communication(),
  );
}
