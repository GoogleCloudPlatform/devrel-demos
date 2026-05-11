import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class BottomNavItem extends StatelessWidget {
  final IconData icon;
  final IconData? selectedIcon;
  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  final int badgeCount;

  const BottomNavItem({
    super.key,
    required this.icon,
    this.selectedIcon,
    required this.label,
    this.isSelected = false,
    required this.onTap,
    this.badgeCount = 0,
  });

  @override
  Widget build(BuildContext context) {
    Widget iconWidget = Icon(
      isSelected && selectedIcon != null ? selectedIcon : icon,
      size: AppSizes.iconMedium,
      color: isSelected
          ? Theme.of(context).colorScheme.primary
          : Theme.of(context).colorScheme.tertiary,
    );

    if (badgeCount > 0) {
      iconWidget = Badge(label: Text('$badgeCount'), child: iconWidget);
    }

    return GestureDetector(
      onTap: onTap,
      child: SizedBox(width: 64.0, child: Center(child: iconWidget)),
    );
  }
}
