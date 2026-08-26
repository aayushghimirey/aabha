import 'package:flutter/material.dart';

import '../../../core/theme/app_dimens.dart';
import '../../widgets/profile/profile_form.dart';
import '../../widgets/profile/session_info_card.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(AppDimens.pagePadding),
      children: const [
        ProfileForm(),
        SizedBox(height: AppDimens.gapLg),
        SessionInfoCard(),
      ],
    );
  }
}
