import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_config.dart';
import '../../providers/repository_providers.dart';
import '../../providers/settings_providers.dart';

enum ApiHealth { unknown, healthy, unreachable }

/// Polls `GET /health` on a timer, the way the web client's dot does.
class HealthController extends Notifier<ApiHealth> {
  Timer? _timer;

  @override
  ApiHealth build() {
    // Pointing the app somewhere else makes the previous verdict meaningless,
    // so the poll restarts from unknown against the new address.
    ref.watch(apiBaseUrlProvider);

    _timer?.cancel();
    _timer = Timer.periodic(
      AppConfig.healthPollInterval,
      (_) => refresh(),
    );
    ref.onDispose(() => _timer?.cancel());

    // Deferred: the first poll cannot write state while build is still running.
    scheduleMicrotask(refresh);

    return ApiHealth.unknown;
  }

  Future<void> refresh() async {
    final healthy = await ref.read(healthRepositoryProvider).isHealthy();

    // The poll outlives nothing: a request in flight when the provider is torn
    // down must not write back into it.
    if (!ref.mounted) return;

    state = healthy ? ApiHealth.healthy : ApiHealth.unreachable;
  }
}
