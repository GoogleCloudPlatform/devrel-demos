import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/screens/product_listing/widgets/filter_chip_widget.dart';

class FilterBar extends StatelessWidget {
  const FilterBar({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Theme.of(context).scaffoldBackgroundColor.withValues(alpha: 0.8),
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: const [
            FilterChipWidget(icon: Icons.tune, label: 'Filters'),
            SizedBox(width: 12),
            FilterChipWidget(label: 'Sort by: Price Low', hasDropdown: true),
            SizedBox(width: 12),
            FilterChipWidget(label: 'Size', hasDropdown: true),
            SizedBox(width: 12),
            FilterChipWidget(label: 'Color', hasDropdown: true),
            SizedBox(width: 12),
            FilterChipWidget(label: 'Brand', hasDropdown: true),
          ],
        ),
      ),
    );
  }
}
