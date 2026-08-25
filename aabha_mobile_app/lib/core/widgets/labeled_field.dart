import 'package:flutter/material.dart';

import '../theme/app_dimens.dart';

/// A label sitting above its field, the way the web client lays them out —
/// rather than Material's floating label.
class LabeledField extends StatelessWidget {
  const LabeledField({
    super.key,
    required this.label,
    required this.child,
    this.hint,
  });

  final String label;
  final String? hint;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              children: [
                Text(label, style: theme.textTheme.labelMedium),
                if (hint != null) ...[
                  const SizedBox(width: 6),
                  Text(hint!, style: theme.textTheme.labelSmall),
                ],
              ],
            ),
          ),
          child,
        ],
      ),
    );
  }
}

/// Spacing used between the fields of a form and the button that submits it.
const SizedBox formGap = SizedBox(height: AppDimens.gap);
