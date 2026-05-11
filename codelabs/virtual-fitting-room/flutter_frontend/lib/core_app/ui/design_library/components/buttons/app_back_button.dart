import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class AppBackButton extends StatelessWidget {
  final VoidCallback? onPressed;

  const AppBackButton({super.key, this.onPressed});

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(
        Icons.close,
        color: Theme.of(context).colorScheme.onSurface,
        size: AppSizes.iconLarge,
      ),
      onPressed: onPressed ?? () => Navigator.pop(context),
    );
  }
}
