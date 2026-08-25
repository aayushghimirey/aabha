import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';

/// One `dt`/`dd` pair from the web client's session list.
class InfoRow extends StatelessWidget {
  const InfoRow({super.key, required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 78,
            child: Text(label, style: theme.textTheme.bodySmall),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: SelectableText(
              value?.isNotEmpty == true ? value! : '—',
              style: theme.textTheme.bodySmall?.copyWith(
                color: AppColors.text,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
