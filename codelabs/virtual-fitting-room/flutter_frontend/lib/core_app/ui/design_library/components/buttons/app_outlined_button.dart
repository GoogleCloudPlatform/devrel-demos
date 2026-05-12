import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

/// A reusable outlined button component tailored for the core app design library.
class AppOutlinedButton extends StatelessWidget {
  /// Callback when the button is pressed
  final VoidCallback onPressed;

  /// The icon displayed leading the label
  final Widget icon;

  /// The text label displayed on the button
  final String label;

  /// The height of the button. Defaults to 56.0.
  final double height;

  /// Whether the button should expand to fill available space in a Row/Column.
  final bool isExpanded;

  const AppOutlinedButton({
    super.key,
    required this.onPressed,
    required this.icon,
    required this.label,
    this.height = 56.0,
    this.isExpanded = false,
  });

  @override
  Widget build(BuildContext context) {
    Widget button = SizedBox(
      height: height,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: Colors.white,
          side: BorderSide(
            color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.5),
            width: 2.0,
          ),
          shape: const RoundedRectangleBorder(
            borderRadius: AppRadius.circular12,
          ),
        ),
        icon: icon,
        label: Text(
          label,
          style: AppTextStyles.buttonLg.copyWith(
            color: Colors.white,
          ),
        ),
      ),
    );

    if (isExpanded) {
      return Expanded(child: button);
    }

    return button;
  }
}
