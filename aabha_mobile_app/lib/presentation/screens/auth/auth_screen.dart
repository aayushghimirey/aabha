import 'package:flutter/material.dart';

import '../../../core/theme/app_dimens.dart';
import '../../../core/widgets/app_card.dart';

class AuthScreen extends StatelessWidget {
  const AuthScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppDimens.pagePadding),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: const AppCard(
                title: 'Sign in',
                subtitle: 'Authentication arrives in a later step.',
                child: SizedBox.shrink(),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
