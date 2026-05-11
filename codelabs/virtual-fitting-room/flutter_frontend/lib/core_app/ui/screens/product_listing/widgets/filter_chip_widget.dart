import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/selectors/filter_chip.dart' as dl;

class FilterChipWidget extends StatelessWidget {
  final IconData? icon;
  final String label;
  final bool hasDropdown;

  const FilterChipWidget({
    super.key,
    this.icon,
    required this.label,
    this.hasDropdown = false,
  });

  @override
  Widget build(BuildContext context) {
    return dl.FilterChip(
      icon: icon,
      label: label,
      hasDropdown: hasDropdown,
    );
  }
}
