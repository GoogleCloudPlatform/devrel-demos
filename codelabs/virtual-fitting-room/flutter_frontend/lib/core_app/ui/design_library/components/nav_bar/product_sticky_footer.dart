import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/nav_bar/bottom_bar.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

/// Sticky footer for the product detail screen that handles layout composition.
/// It delegates cart state management entirely to [AddToBagButton] to keep
/// this component purely focused on UI layout and navigation.
class ProductStickyFooter extends StatelessWidget {
  final List<Widget> children;

  const ProductStickyFooter({super.key, required this.children});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: BottomBar(
        padding: AppPadding.all16,
        child: Row(children: children),
      ),
    );
  }
}
