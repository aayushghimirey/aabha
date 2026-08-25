import 'package:flutter/material.dart';

import '../../../core/config/app_config.dart';
import '../../../core/theme/app_dimens.dart';
import '../../../core/widgets/app_card.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Text(AppConfig.appName, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(width: 10),
            Text(
              AppConfig.appTagline,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(AppDimens.pagePadding),
        children: const [
          AppCard(
            title: 'Talk to aabha',
            subtitle: 'The voice session arrives in a later step.',
            child: SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}
