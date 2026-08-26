import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/validators.dart';
import '../../../core/widgets/date_field.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../core/widgets/submit_button.dart';
import '../../../data/models/user_registration.dart';
import '../../../providers/auth_providers.dart';

class RegisterForm extends ConsumerStatefulWidget {
  const RegisterForm({super.key});

  @override
  ConsumerState<RegisterForm> createState() => _RegisterFormState();
}

class _RegisterFormState extends ConsumerState<RegisterForm> {
  final _formKey = GlobalKey<FormState>();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();

  DateTime? _dob;

  // The date picker sits outside the Form's validation, so its error has to
  // be held and shown by hand.
  bool _dobMissing = false;

  @override
  void dispose() {
    _username.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final dob = _dob;
    setState(() => _dobMissing = dob == null);

    final formOk = _formKey.currentState!.validate();
    if (!formOk || dob == null) return;

    await ref.read(authFormControllerProvider.notifier).register(
          UserRegistration(
            username: _username.text.trim(),
            email: _email.text.trim(),
            password: _password.text,
            dob: dob,
          ),
        );
  }

  @override
  Widget build(BuildContext context) {
    final isSubmitting = ref.watch(
      authFormControllerProvider.select((state) => state.isSubmitting),
    );

    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          LabeledField(
            label: 'Username',
            hint: '${UserRegistration.usernameMin}–'
                '${UserRegistration.usernameMax} characters',
            child: TextFormField(
              controller: _username,
              enabled: !isSubmitting,
              autocorrect: false,
              textInputAction: TextInputAction.next,
              validator: Validators.username,
            ),
          ),
          LabeledField(
            label: 'Email',
            child: TextFormField(
              controller: _email,
              enabled: !isSubmitting,
              autocorrect: false,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              validator: Validators.email,
            ),
          ),
          LabeledField(
            label: 'Password',
            hint: 'at least ${UserRegistration.passwordMin} characters',
            child: TextFormField(
              controller: _password,
              enabled: !isSubmitting,
              obscureText: true,
              textInputAction: TextInputAction.done,
              validator: Validators.password,
            ),
          ),
          LabeledField(
            label: 'Date of birth',
            child: DateField(
              value: _dob,
              errorText: _dobMissing ? 'Date of birth is required' : null,
              onChanged: (value) => setState(() {
                _dob = value;
                _dobMissing = false;
              }),
            ),
          ),
          formGap,
          SubmitButton(
            label: 'Create account',
            busyLabel: 'Creating…',
            isBusy: isSubmitting,
            onPressed: _submit,
          ),
        ],
      ),
    );
  }
}
