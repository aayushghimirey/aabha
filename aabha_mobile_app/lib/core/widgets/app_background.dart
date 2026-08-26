import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// The two radial glows the web client paints behind everything — violet from
/// the top left, teal from the top right.
class AppBackground extends StatelessWidget {
  const AppBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.background,
        gradient: RadialGradient(
          center: Alignment(-0.7, -1.1),
          radius: 1.1,
          colors: [Color(0x227C6CFF), Color(0x000B0C10)],
          stops: [0, 0.6],
        ),
      ),
      child: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(1, -1),
            radius: 0.9,
            colors: [Color(0x184AD2C4), Color(0x000B0C10)],
            stops: [0, 0.55],
          ),
        ),
        child: child,
      ),
    );
  }
}
