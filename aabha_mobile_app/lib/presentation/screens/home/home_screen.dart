import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/app_config.dart';
import '../../../core/theme/app_dimens.dart';
import '../../../core/widgets/app_background.dart';
import '../../../core/widgets/app_card.dart';
import '../../../providers/session_providers.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final user = ref.watch(currentUserProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Text(AppConfig.appName, style: theme.textTheme.titleLarge),
            const SizedBox(width: 10),
            Text(AppConfig.appTagline, style: theme.textTheme.bodySmall),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () =>
                ref.read(sessionControllerProvider.notifier).signOut(),
            child: const Text('Sign out'),
          ),
          const SizedBox(width: AppDimens.gap),
        ],
      ),
      body: AppBackground(
        child: ListView(
          padding: const EdgeInsets.all(AppDimens.pagePadding),
          children: [
            AppCard(
              title: 'Signed in as ${user?.username ?? '—'}',
              subtitle: 'The voice session and profile arrive in later steps.',
              child: const SizedBox.shrink(),
            ),
          ],
        ),
      ),
    );
  }
}
