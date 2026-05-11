import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/scaffold_with_background_noise.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/core_app/ui/design_library/components/nav_bar/product_sticky_footer.dart';
import 'package:fashion_app/core_app/ui/screens/product_detail/widgets/product_detail_scroll_content.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/app_icon_button.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/ui/2_try_it_on_screen.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/add_to_bag_button.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/providers/try_it_on_provider.dart';
import 'package:fashion_app/core_app/ui/design_library/utils/fade_page_route.dart';

/// The main product detail page for a selected retail item.
///
/// This screen displays the product image, color/size selection, and the
/// sticky footer. During the workshop, developers add the `AppIconButton`
/// to the footer as the entry point to the Virtual Try-On flow.
class ProductDetailScreen extends StatefulWidget {
  final Product product;

  const ProductDetailScreen({super.key, required this.product});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  int _selectedColorIndex = 0;
  int _selectedSizeIndex = 1; // Default to 'S'

  final List<Color> _colors = [
    const Color(0xFF3B3B3B),
    const Color(0xFF8E5A35),
    const Color(0xFFC7C7C7),
    const Color(0xFF3A5B8E),
  ];

  final List<String> _sizes = ['XS', 'S', 'M', 'L', 'XL'];

  @override
  Widget build(BuildContext context) {
    final color = _colors[_selectedColorIndex];
    final size = _sizes[_selectedSizeIndex];

    return ScaffoldWithBackgroundNoise(
      body: Stack(
        children: [
          ProductDetailScrollContent(
            product: widget.product,
            colors: _colors,
            selectedColorIndex: _selectedColorIndex,
            onColorSelected: (index) {
              setState(() {
                _selectedColorIndex = index;
              });
            },
            sizes: _sizes,
            selectedSizeIndex: _selectedSizeIndex,
            onSizeSelected: (index) {
              setState(() {
                _selectedSizeIndex = index;
              });
            },
          ),
          ProductStickyFooter(
            children: [
              // START_WORKSHOP_STEP 1
              // Initializes the Try-On provider with the selected product and navigates to the Try-On flow.
              AppIconButton(
                icon: Icons.person_outline,
                onPressed: () {
                  context.read<TryItOnProvider>().initializeWithProduct(
                    widget.product,
                  );
                  Navigator.push(
                    context,
                    FadePageRoute(page: const TryItOnScreen()),
                  );
                },
              ),
              const SizedBox(width: 12),
              // END_WORKSHOP_STEP
              AddToBagButton(
                product: widget.product,
                selectedColor: color,
                selectedSize: size,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
