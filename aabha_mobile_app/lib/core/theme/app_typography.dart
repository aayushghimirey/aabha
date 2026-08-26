import 'package:flutter/material.dart';

import 'app_colors.dart';

abstract final class AppTypography {
  static const TextTheme textTheme = TextTheme(
    titleLarge: TextStyle(
      fontSize: 22,
      height: 1.3,
      letterSpacing: -0.44,
      fontWeight: FontWeight.w600,
      color: AppColors.text,
    ),
    titleMedium: TextStyle(
      fontSize: 15,
      height: 1.4,
      letterSpacing: -0.15,
      fontWeight: FontWeight.w600,
      color: AppColors.text,
    ),
    bodyLarge: TextStyle(fontSize: 15, height: 1.5, color: AppColors.text),
    bodyMedium: TextStyle(fontSize: 14, height: 1.5, color: AppColors.text),
    bodySmall: TextStyle(fontSize: 13, height: 1.5, color: AppColors.muted),
    labelSmall: TextStyle(fontSize: 11, height: 1.4, color: AppColors.muted),
    labelMedium: TextStyle(fontSize: 12, height: 1.4, color: AppColors.muted),
  );
}
