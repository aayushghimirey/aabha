import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/utils/validators.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../core/widgets/submit_button.dart';
import '../../../providers/auth_providers.dart';

class SignInForm extends ConsumerStatefulWidget {
  const SignInForm({super.key});

  @override
  ConsumerState<SignInForm> createState() => _SignInFormState();
}

class _SignInFormState extends ConsumerState<SignInForm> {
  final _formKey = GlobalKey<FormState>();
  final _username = TextEditingController();
  final _password = TextEditingController();

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    await ref
        .read(authFormControllerProvider.notifier)
        .signIn(_username.text, _password.text);
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
            child: TextFormField(
              controller: _username,
              enabled: !isSubmitting,
              autocorrect: false,
              textInputAction: TextInputAction.next,
              validator: (value) => Validators.required(value, 'Username'),
            ),
          ),
          LabeledField(
            label: 'Password',
            child: TextFormField(
              controller: _password,
              enabled: !isSubmitting,
              obscureText: true,
              textInputAction: TextInputAction.done,
              onFieldSubmitted: (_) => _submit(),
              validator: (value) => Validators.required(value, 'Password'),
            ),
          ),
          formGap,
          SubmitButton(
            label: 'Sign in',
            busyLabel: 'Signing in…',
            isBusy: isSubmitting,
            onPressed: _submit,
          ),
        ],
      ),
    );
  }
}
