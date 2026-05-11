import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

/// A reusable wrapper for custom app bars that provides a standard 
/// safe area and horizontal/vertical padding.
class CustomAppBarWrapper extends StatelessWidget implements PreferredSizeWidget {
  final Widget child;

  const CustomAppBarWrapper({super.key, required this.child});

  static const Size standardSize = Size.fromHeight(kToolbarHeight + AppSizes.s16);

  @override
  Size get preferredSize => standardSize;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSizes.s16,
          vertical: AppSizes.s8,
        ),
        child: child,
      ),
    );
  }
}
