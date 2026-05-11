import 'package:flutter/material.dart';

/// A [Positioned] widget that automatically adjusts its bottom padding
/// to react to the keyboard (`MediaQuery.viewInsets.bottom`) and the
/// device's safe area (`MediaQuery.padding.bottom`).
class KeyboardAwarePositioned extends StatelessWidget {
  /// The widget below this widget in the tree.
  final Widget child;

  /// Distance from the left edge of the Stack.
  final double left;

  /// Distance from the right edge of the Stack.
  final double right;

  /// The padding to add above the standard bottom safe area when the keyboard is closed.
  final double defaultBottomPadding;

  /// The padding to add above the keyboard when the keyboard is open.
  final double keyboardOpenPadding;

  const KeyboardAwarePositioned({
    super.key,
    required this.child,
    this.left = 24.0,
    this.right = 24.0,
    this.defaultBottomPadding = 24.0,
    this.keyboardOpenPadding = 12.0,
  });

  @override
  Widget build(BuildContext context) {
    // If the keyboard is visible, viewInsets.bottom is > 0
    final double keyboardHeight = MediaQuery.of(context).viewInsets.bottom;
    final double bottomSafeArea = MediaQuery.of(context).padding.bottom;

    final double bottomOffset = keyboardHeight > 0
        ? keyboardHeight + keyboardOpenPadding
        : bottomSafeArea + defaultBottomPadding;

    return Positioned(
      left: left,
      right: right,
      bottom: bottomOffset,
      child: child,
    );
  }
}
