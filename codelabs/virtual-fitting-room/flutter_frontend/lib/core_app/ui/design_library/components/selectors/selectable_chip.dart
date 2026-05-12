import 'package:flutter/material.dart';

import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class SelectableChip extends StatelessWidget {
  final bool isSelected;
  final VoidCallback onTap;
  final String? label;
  final Widget? child;
  final double width;
  final double height;
  final EdgeInsetsGeometry margin;
  final Color? activeColor;
  final BoxShape shape;
  final BorderRadiusGeometry? borderRadius;

  const SelectableChip({
    super.key,
    required this.isSelected,
    required this.onTap,
    this.label,
    this.child,
    this.width = AppSizes.s48,
    this.height = AppSizes.s48,
    this.margin = const EdgeInsets.only(right: AppSizes.s12),
    this.activeColor,
    this.shape = BoxShape.rectangle,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    final primaryColor = activeColor ?? Theme.of(context).colorScheme.primary;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: margin,
        width: width,
        height: height,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: isSelected
              ? primaryColor.withValues(alpha: 0.2)
              : Colors.transparent,
          shape: shape,
          borderRadius: shape == BoxShape.rectangle
              ? (borderRadius ?? AppRadius.circular8)
              : null,
          border: Border.all(
            color: isSelected
                ? primaryColor
                : Theme.of(context).colorScheme.secondary,
            width: isSelected ? 2.0 : 1.0,
          ),
        ),
        child:
            child ??
            (label != null
                ? Text(
                    label!,
                    style: AppTextStyles.selectableChip.copyWith(
                      color: isSelected
                          ? primaryColor
                          : Theme.of(context).colorScheme.onSurface,
                    ),
                  )
                : null),
      ),
    );
  }
}
