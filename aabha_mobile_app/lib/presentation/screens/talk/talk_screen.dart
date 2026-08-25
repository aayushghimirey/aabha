import 'package:flutter/material.dart';

import '../../../core/theme/app_dimens.dart';
import '../../../core/widgets/app_card.dart';

class TalkScreen extends StatelessWidget {
  const TalkScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(AppDimens.pagePadding),
      children: const [
        AppCard(
          title: 'Talk to aabha',
          subtitle: 'The LiveKit room and transcript arrive in the next step.',
          child: SizedBox.shrink(),
        ),
      ],
    );
  }
}
