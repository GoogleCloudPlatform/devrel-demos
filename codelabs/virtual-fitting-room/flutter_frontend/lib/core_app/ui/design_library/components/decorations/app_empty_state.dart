import 'package:flutter/material.dart';

/// A reusable empty state component that displays a standard [message] 
/// centered on the screen.
class AppEmptyState extends StatelessWidget {
  /// The message to display when there is no data.
  final String message;

  const AppEmptyState({
    super.key,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        message,
        textAlign: TextAlign.center,
      ),
    );
  }
}
