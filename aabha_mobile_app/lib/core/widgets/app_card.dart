import 'package:flutter/material.dart';

import '../theme/app_dimens.dart';

class AppCard extends StatelessWidget {
  const AppCard({super.key, required this.child, this.title, this.subtitle});

  final Widget child;
  final String? title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppDimens.cardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (title != null)
              Text(title!, style: theme.textTheme.titleMedium),
            if (subtitle != null) ...[
              const SizedBox(height: 4),
              Text(subtitle!, style: theme.textTheme.bodySmall),
            ],
            if (title != null || subtitle != null)
              const SizedBox(height: AppDimens.gapLg),
            child,
          ],
        ),
      ),
    );
  }
}
