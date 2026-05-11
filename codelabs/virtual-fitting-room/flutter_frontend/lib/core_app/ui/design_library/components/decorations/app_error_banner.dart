import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

/// A floating error banner intended to be used as an overlay.
/// It must be placed within a [Stack] since it returns a [Positioned] widget.
class AppErrorBanner extends StatelessWidget {
  /// The error message to display.
  final String message;

  const AppErrorBanner({
    super.key,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: 8,
      left: 24,
      right: 24,
      child: Material(
        color: Colors.transparent,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSizes.s16,
            vertical: AppSizes.s12,
          ),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.errorContainer,
            borderRadius: AppRadius.circular12,
          ),
          child: Text(
            message,
            style: TextStyle(
              color: Theme.of(context).colorScheme.onErrorContainer,
              fontSize: 13,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}
