import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/core_app/ui/screens/product_detail/widgets/image_carousel.dart';
import 'package:fashion_app/core_app/ui/screens/product_detail/widgets/expandable_section.dart';
import 'package:fashion_app/core_app/ui/screens/product_detail/widgets/product_detail_app_bar.dart';
import 'package:fashion_app/core_app/ui/screens/product_detail/widgets/product_info_header.dart';
import 'package:fashion_app/core_app/ui/screens/product_detail/widgets/color_selector.dart';
import 'package:fashion_app/core_app/ui/screens/product_detail/widgets/size_selector.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class ProductDetailScrollContent extends StatelessWidget {
  final Product product;
  final List<Color> colors;
  final int selectedColorIndex;
  final ValueChanged<int> onColorSelected;
  final List<String> sizes;
  final int selectedSizeIndex;
  final ValueChanged<int> onSizeSelected;

  const ProductDetailScrollContent({
    super.key,
    required this.product,
    required this.colors,
    required this.selectedColorIndex,
    required this.onColorSelected,
    required this.sizes,
    required this.selectedSizeIndex,
    required this.onSizeSelected,
  });

  @override
  Widget build(BuildContext context) {
    final String title = product.title;
    final String price = product.formattedPrice;
    final String image = product.productImage;
    final List<String> currentProductImages = product.images.isNotEmpty
        ? product.images
        : [image, image, image];

    return CustomScrollView(
      slivers: [
        // Hero Image with AppBar
        ProductDetailAppBar(
          background: ImageCarousel(images: currentProductImages),
        ),

        // Product Info
        SliverToBoxAdapter(
          child: ProductInfoHeader(title: title, price: price),
        ),

        // Color Selector
        SliverToBoxAdapter(
          child: ColorSelector(
            colors: colors,
            selectedIndex: selectedColorIndex,
            onColorSelected: onColorSelected,
          ),
        ),

        // Size Selector
        SliverToBoxAdapter(
          child: SizeSelector(
            sizes: sizes,
            selectedIndex: selectedSizeIndex,
            onSizeSelected: onSizeSelected,
          ),
        ),

        // Expandable Details
        SliverToBoxAdapter(
          child: Padding(
            padding: AppPadding.horizontal16,
            child: Column(
              children: [
                const ExpandableSection(
                  title: 'Product Details',
                  content:
                      'This Modern Fit Jacket is crafted from a premium wool blend, offering both style and warmth. It features a tailored silhouette, notched lapels, and a single-breasted front for a timeless look.',
                ),
                const ExpandableSection(
                  title: 'Sizing & Fit',
                  content: 'True to size. Model is 6\'1" wearing size M.',
                ),
                const ExpandableSection(
                  title: 'Customer Reviews (132)',
                  content: 'Rated 4.8/5 based on 132 reviews.',
                ),
                const ExpandableSection(
                  title: 'Shipping & Returns',
                  content:
                      'Free shipping on orders over \$50. Free returns within 30 days.',
                ),
              ],
            ),
          ),
        ),

        // Bottom Padding for Sticky Footer
        const SliverToBoxAdapter(child: SizedBox(height: 140)),
      ],
    );
  }
}
