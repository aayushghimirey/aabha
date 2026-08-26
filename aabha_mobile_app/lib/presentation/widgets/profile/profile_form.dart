import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_dimens.dart';
import '../../../core/utils/validators.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/date_field.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../core/widgets/status_message.dart';
import '../../../core/widgets/submit_button.dart';
import '../../../data/models/user.dart';
import '../../../data/models/user_update.dart';
import '../../../providers/profile_providers.dart';
import '../../../providers/session_providers.dart';

class ProfileForm extends ConsumerStatefulWidget {
  const ProfileForm({super.key});

  @override
  ConsumerState<ProfileForm> createState() => _ProfileFormState();
}

class _ProfileFormState extends ConsumerState<ProfileForm> {
  final _formKey = GlobalKey<FormState>();
  final _username = TextEditingController();
  final _email = TextEditingController();

  DateTime? _dob;

  @override
  void initState() {
    super.initState();
    _fill(ref.read(currentUserProvider));
  }

  @override
  void dispose() {
    _username.dispose();
    _email.dispose();
    super.dispose();
  }

  /// Repaints the form from the user the app currently holds — after a save,
  /// after a reload, and once when the screen opens.
  void _fill(User? user) {
    if (user == null) return;
    _username.text = user.username;
    _email.text = user.email;
    _dob = user.dob;
  }

  Future<void> _save() async {
    final dob = _dob;
    if (!_formKey.currentState!.validate() || dob == null) return;

    await ref.read(profileControllerProvider.notifier).save(
          UserUpdate(
            username: _username.text.trim(),
            email: _email.text.trim(),
            dob: dob,
          ),
        );
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(currentUserProvider, (_, next) => setState(() => _fill(next)));

    final profile = ref.watch(profileControllerProvider);
    final controller = ref.read(profileControllerProvider.notifier);

    return AppCard(
      title: 'Your profile',
      subtitle: 'Reads GET /users/{id}, saves with PUT.',
      child: Form(
        key: _formKey,
        onChanged: controller.clearFeedback,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (profile.error != null) ...[
              StatusMessage(text: profile.error!),
              const SizedBox(height: AppDimens.gap),
            ] else if (profile.justSaved) ...[
              const StatusMessage(text: 'Saved.', kind: StatusKind.success),
              const SizedBox(height: AppDimens.gap),
            ],
            LabeledField(
              label: 'Username',
              child: TextFormField(
                controller: _username,
                enabled: !profile.isBusy,
                autocorrect: false,
                validator: Validators.username,
              ),
            ),
            LabeledField(
              label: 'Email',
              child: TextFormField(
                controller: _email,
                enabled: !profile.isBusy,
                autocorrect: false,
                keyboardType: TextInputType.emailAddress,
                validator: Validators.email,
              ),
            ),
            LabeledField(
              label: 'Date of birth',
              child: DateField(
                value: _dob,
                onChanged: (value) {
                  setState(() => _dob = value);
                  controller.clearFeedback();
                },
              ),
            ),
            formGap,
            Row(
              children: [
                Expanded(
                  child: SubmitButton(
                    label: 'Save changes',
                    busyLabel: 'Saving…',
                    isBusy: profile.isSaving,
                    onPressed: _save,
                  ),
                ),
                const SizedBox(width: AppDimens.gap),
                Expanded(
                  child: OutlinedButton(
                    onPressed: profile.isBusy ? null : controller.reload,
                    child: Text(
                      profile.isReloading ? 'Reloading…' : 'Reload',
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
