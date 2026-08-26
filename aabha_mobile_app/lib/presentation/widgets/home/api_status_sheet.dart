import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_dimens.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../providers/health_providers.dart';
import '../../../providers/settings_providers.dart';
import 'health_dot.dart';

/// What the web client keeps in its header: where the API is, and whether it
/// is answering. Reachable by tapping the dot.
class ApiStatusSheet extends ConsumerStatefulWidget {
  const ApiStatusSheet({super.key});

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppColors.panel,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) => const ApiStatusSheet(),
    );
  }

  @override
  ConsumerState<ApiStatusSheet> createState() => _ApiStatusSheetState();
}

class _ApiStatusSheetState extends ConsumerState<ApiStatusSheet> {
  late final TextEditingController _baseUrl = TextEditingController(
    text: ref.read(apiBaseUrlProvider),
  );

  @override
  void dispose() {
    _baseUrl.dispose();
    super.dispose();
  }

  Future<void> _apply() async {
    await ref.read(apiBaseUrlProvider.notifier).setApiBaseUrl(_baseUrl.text);
    if (!mounted) return;

    // Changing the address restarts the poll on its own; this only closes up.
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final health = ref.watch(apiHealthProvider);

    return Padding(
      padding: EdgeInsets.only(
        left: AppDimens.pagePadding,
        right: AppDimens.pagePadding,
        top: AppDimens.pagePadding,
        bottom: MediaQuery.viewInsetsOf(context).bottom + AppDimens.pagePadding,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              HealthDot(health: health, size: 9),
              const SizedBox(width: 10),
              Text(health.label, style: theme.textTheme.titleMedium),
              const Spacer(),
              TextButton(
                onPressed: () => ref.read(apiHealthProvider.notifier).refresh(),
                child: const Text('Check now'),
              ),
            ],
          ),
          const SizedBox(height: AppDimens.gapLg),
          LabeledField(
            label: 'API base URL',
            child: TextField(
              controller: _baseUrl,
              autocorrect: false,
              keyboardType: TextInputType.url,
              onSubmitted: (_) => _apply(),
            ),
          ),
          Text(
            'The emulator reaches the host machine at 10.0.2.2; a physical '
            'device needs its LAN address. Applied here it survives a restart, '
            'so it need not be rebuilt in.',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: AppDimens.gapLg),
          FilledButton(onPressed: _apply, child: const Text('Apply')),
        ],
      ),
    );
  }
}
