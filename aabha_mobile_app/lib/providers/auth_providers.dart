import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../presentation/controllers/auth_form_controller.dart';

/// Auto-disposed so leaving the sign-in screen clears the tab, the error, and
/// anything half-typed — signing out should not come back to a stale form.
final authFormControllerProvider =
    NotifierProvider<AuthFormController, AuthFormState>(
      AuthFormController.new,
      isAutoDispose: true,
    );
