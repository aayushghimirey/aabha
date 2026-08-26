import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../controllers/auth_form_controller.dart';

/// The pill switch between signing in and creating an account.
class AuthTabs extends StatelessWidget {
  const AuthTabs({
    super.key,
    required this.mode,
    required this.onChanged,
    this.enabled = true,
  });

  final AuthMode mode;
  final ValueChanged<AuthMode> onChanged;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppColors.panelAlt,
        borderRadius: BorderRadius.circular(11),
      ),
      child: Row(
        children: [
          _tab(context, AuthMode.signIn, 'Sign in'),
          _tab(context, AuthMode.register, 'Create account'),
        ],
      ),
    );
  }

  Widget _tab(BuildContext context, AuthMode value, String label) {
    final selected = mode == value;

    return Expanded(
      child: GestureDetector(
        onTap: enabled && !selected ? () => onChanged(value) : null,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(vertical: 9),
          decoration: BoxDecoration(
            color: selected ? AppColors.panel : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            boxShadow: selected
                ? const [
                    BoxShadow(
                      color: Color(0x66000000),
                      blurRadius: 2,
                      offset: Offset(0, 1),
                    ),
                  ]
                : null,
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: selected ? AppColors.text : AppColors.muted,
            ),
          ),
        ),
      ),
    );
  }
}
