import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/repository_providers.dart';

/// The API address the app is pointed at.
///
/// The web client keeps this editable in its header because the host differs
/// between an emulator, a phone on the LAN, and a deployment. A phone has no
/// address bar to correct, so it gets the same control behind the health dot.
class SettingsController extends Notifier<String> {
  @override
  String build() {
    // Whatever was stored has already been applied to Dio by the session
    // restore, which the app waits on before any of this is reachable.
    return ref.read(settingsRepositoryProvider).apiBaseUrl;
  }

  Future<void> setApiBaseUrl(String value) async {
    final normalized = await ref
        .read(settingsRepositoryProvider)
        .setApiBaseUrl(value);

    state = normalized;
  }
}
