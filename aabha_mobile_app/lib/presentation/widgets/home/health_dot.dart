import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../controllers/health_controller.dart';

class HealthDot extends StatelessWidget {
  const HealthDot({super.key, required this.health, this.size = 8});

  final ApiHealth health;
  final double size;

  Color get _color => switch (health) {
    ApiHealth.unknown => AppColors.muted,
    ApiHealth.healthy => AppColors.ok,
    ApiHealth.unreachable => AppColors.danger,
  };

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: _color,
        shape: BoxShape.circle,
        // The glow the web dot wears once it knows something.
        boxShadow: health == ApiHealth.unknown
            ? null
            : [
                BoxShadow(
                  color: _color.withValues(alpha: 0.15),
                  spreadRadius: 4,
                ),
              ],
      ),
    );
  }
}

extension ApiHealthLabel on ApiHealth {
  String get label => switch (this) {
    ApiHealth.unknown => 'Checking…',
    ApiHealth.healthy => 'API healthy',
    ApiHealth.unreachable => 'No response',
  };
}
