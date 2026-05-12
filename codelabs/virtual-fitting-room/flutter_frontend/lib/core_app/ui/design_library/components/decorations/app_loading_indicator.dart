import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

/// A reusable loading indicator component that displays a standard spinner
/// with an optional [message] underneath.
class AppLoadingIndicator extends StatelessWidget {
  /// The loading message to display below the spinner.
  final String message;

  const AppLoadingIndicator({
    super.key,
    this.message = 'Loading...',
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: AppSizes.s16),
          Text(message),
        ],
      ),
    );
  }
}
