import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../utils/date_formatting.dart';

/// The `<input type="date">` equivalent: tapping opens the platform picker.
///
/// Shared by registration and the profile form, which take the same `dob`.
class DateField extends StatelessWidget {
  const DateField({
    super.key,
    required this.value,
    required this.onChanged,
    this.errorText,
  });

  final DateTime? value;
  final ValueChanged<DateTime> onChanged;
  final String? errorText;

  static final DateTime _earliest = DateTime(1900);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final chosen = value;

    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: () => _pick(context),
      child: InputDecorator(
        decoration: InputDecoration(errorText: errorText),
        child: Row(
          children: [
            Expanded(
              child: Text(
                chosen == null ? 'Select a date' : chosen.apiDate,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: chosen == null ? AppColors.muted : AppColors.text,
                ),
              ),
            ),
            const Icon(Icons.calendar_today_outlined,
                size: 17, color: AppColors.muted),
          ],
        ),
      ),
    );
  }

  Future<void> _pick(BuildContext context) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: value ?? DateTime(now.year - 20, now.month, now.day),
      firstDate: _earliest,
      lastDate: now,
    );

    if (picked != null) onChanged(picked.dateOnly);
  }
}
