import 'package:flutter/material.dart';

import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/app_button.dart';

class PrimaryButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final String text;
  final Widget? child;
  final bool isFullWidth;
  final double height;
  final EdgeInsetsGeometry padding;

  const PrimaryButton({
    super.key,
    required this.onPressed,
    this.text = '',
    this.child,
    this.isFullWidth = true,
    this.height = 56.0,
    this.padding = AppPadding.horizontal24,
  });

  @override
  Widget build(BuildContext context) {
    return AppButton(
      onPressed: onPressed,
      backgroundColor: Theme.of(context).colorScheme.primary,
      foregroundColor: Colors.white,
      text: text,
      isFullWidth: isFullWidth,
      height: height,
      padding: padding,
      child: child,
    );
  }
}
