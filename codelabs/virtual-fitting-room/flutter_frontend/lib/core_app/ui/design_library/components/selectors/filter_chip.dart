import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class FilterChip extends StatelessWidget {
  final IconData? icon;
  final String label;
  final bool hasDropdown;

  const FilterChip({
    super.key,
    this.icon,
    required this.label,
    this.hasDropdown = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.1),
        borderRadius: AppRadius.circular20,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(
              icon,
              color: Theme.of(context).colorScheme.tertiary,
              size: AppSizes.iconSmall,
            ),
            const SizedBox(width: AppSizes.s8),
          ],
          Text(
            label,
            style: AppTextStyles.filterChip.copyWith(
              color: Theme.of(context).colorScheme.onSurface,
            ),
          ),
          if (hasDropdown) ...[
            const SizedBox(width: AppSizes.s8),
            Icon(
              Icons.expand_more,
              color: Theme.of(context).colorScheme.tertiary,
              size: AppSizes.iconSmall,
            ),
          ],
        ],
      ),
    );
  }
}
