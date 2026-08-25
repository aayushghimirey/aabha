import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/app_config.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_dimens.dart';
import '../../../core/widgets/app_background.dart';
import '../../../providers/health_providers.dart';
import '../../../providers/session_providers.dart';
import '../../widgets/home/api_status_sheet.dart';
import '../../widgets/home/health_dot.dart';

/// The frame every signed-in screen sits in: the brand, the health dot, sign
/// out, and the switch between talking and everything else.
class HomeShell extends ConsumerWidget {
  const HomeShell({super.key, required this.shell});

  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final health = ref.watch(apiHealthProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        titleSpacing: AppDimens.pagePadding,
        title: Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Text(AppConfig.appName, style: theme.textTheme.titleLarge),
            const SizedBox(width: 10),
            Flexible(
              child: Text(
                AppConfig.appTagline,
                style: theme.textTheme.bodySmall,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: () => ApiStatusSheet.show(context),
            tooltip: health.label,
            icon: HealthDot(health: health, size: 9),
          ),
          TextButton(
            onPressed: () =>
                ref.read(sessionControllerProvider.notifier).signOut(),
            child: const Text('Sign out'),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: AppBackground(child: shell),
      bottomNavigationBar: NavigationBar(
        backgroundColor: AppColors.panel,
        indicatorColor: AppColors.accent.withValues(alpha: 0.18),
        selectedIndex: shell.currentIndex,
        // `goBranch` keeps each tab's own navigation stack, which matters once
        // talking has state worth not losing on a tab switch.
        onDestinationSelected: (index) => shell.goBranch(
          index,
          initialLocation: index == shell.currentIndex,
        ),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.graphic_eq),
            label: 'Talk',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
