import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class AppButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final String text;
  final Widget? child;
  final bool isFullWidth;
  final double height;
  final EdgeInsetsGeometry padding;
  final Color backgroundColor;
  final Color foregroundColor;
  final Color? disabledBackgroundColor;
  final Color? disabledForegroundColor;
  final BorderRadiusGeometry? borderRadius;

  const AppButton({
    super.key,
    required this.onPressed,
    required this.backgroundColor,
    required this.foregroundColor,
    this.text = '',
    this.child,
    this.isFullWidth = true,
    this.height = 56.0,
    this.padding = AppPadding.horizontal24,
    this.disabledBackgroundColor,
    this.disabledForegroundColor,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: isFullWidth ? double.infinity : null,
      height: height,
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: backgroundColor,
          foregroundColor: foregroundColor,
          disabledBackgroundColor: disabledBackgroundColor ?? backgroundColor.withValues(alpha: 0.5),
          disabledForegroundColor: disabledForegroundColor ?? foregroundColor.withValues(alpha: 0.8),
          shape: RoundedRectangleBorder(
            borderRadius: borderRadius ?? AppRadius.circular12,
          ),
          padding: padding,
          elevation: 0,
        ),
        child: child ?? Text(
          text,
          style: height >= 56 ? AppTextStyles.buttonLg : AppTextStyles.buttonSm,
        ),
      ),
    );
  }
}
