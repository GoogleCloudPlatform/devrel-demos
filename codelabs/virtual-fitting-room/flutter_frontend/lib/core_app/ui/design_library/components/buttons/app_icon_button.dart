import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class AppIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onPressed;
  final double size;
  final Color? backgroundColor;
  final Color? iconColor;
  final BorderRadiusGeometry? borderRadius;

  const AppIconButton({
    super.key,
    required this.icon,
    required this.onPressed,
    this.size = AppSizes.s48,
    this.backgroundColor,
    this.iconColor,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: backgroundColor ?? Theme.of(context).colorScheme.secondary,
        borderRadius: borderRadius ?? AppRadius.circular12,
      ),
      child: IconButton(
        icon: Icon(
          icon,
          color: iconColor ?? Theme.of(context).colorScheme.onSurface,
        ),
        onPressed: onPressed,
      ),
    );
  }
}
