import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/app_config.dart';
import '../../../core/theme/app_dimens.dart';
import '../../../core/widgets/app_background.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/status_message.dart';
import '../../../providers/auth_providers.dart';
import '../../controllers/auth_form_controller.dart';
import '../../widgets/auth/auth_tabs.dart';
import '../../widgets/auth/register_form.dart';
import '../../widgets/auth/sign_in_form.dart';

class AuthScreen extends ConsumerWidget {
  const AuthScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final form = ref.watch(authFormControllerProvider);
    final theme = Theme.of(context);

    return Scaffold(
      body: AppBackground(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppDimens.pagePadding),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 460),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          AppConfig.appName,
                          style: theme.textTheme.titleLarge,
                        ),
                        const SizedBox(width: 10),
                        Text(
                          AppConfig.appTagline,
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          AuthTabs(
                            mode: form.mode,
                            enabled: !form.isSubmitting,
                            onChanged: ref
                                .read(authFormControllerProvider.notifier)
                                .switchMode,
                          ),
                          const SizedBox(height: AppDimens.gapLg),
                          if (form.error != null) ...[
                            StatusMessage(text: form.error!),
                            const SizedBox(height: AppDimens.gap),
                          ],
                          // Keyed so switching tabs drops the other form's
                          // controllers instead of carrying a typed password
                          // across.
                          switch (form.mode) {
                            AuthMode.signIn => const SignInForm(
                                key: ValueKey('sign-in'),
                              ),
                            AuthMode.register => const RegisterForm(
                                key: ValueKey('register'),
                              ),
                          },
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
