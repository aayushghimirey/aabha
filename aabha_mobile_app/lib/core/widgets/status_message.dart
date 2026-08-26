import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';

enum StatusKind { error, success }

class StatusMessage extends StatelessWidget {
  const StatusMessage({super.key, required this.text, this.kind = StatusKind.error});

  final String text;
  final StatusKind kind;

  @override
  Widget build(BuildContext context) {
    final isError = kind == StatusKind.error;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
      decoration: BoxDecoration(
        color: isError ? AppColors.dangerSurface : AppColors.okSurface,
        border: Border.all(
          color: isError ? AppColors.dangerBorder : AppColors.okBorder,
        ),
        borderRadius: BorderRadius.circular(AppDimens.radiusSm),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 13,
          height: 1.45,
          color: isError ? AppColors.dangerText : AppColors.okText,
        ),
      ),
    );
  }
}
