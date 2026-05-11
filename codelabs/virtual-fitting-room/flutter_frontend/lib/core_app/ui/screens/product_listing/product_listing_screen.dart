import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/cards/product_card.dart';
import 'package:fashion_app/core_app/ui/screens/product_listing/widgets/filter_bar.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/core_app/services/mock/mock_data_service.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/ui/1_product_detail_screen.dart';

class ProductListingScreen extends StatefulWidget {
  const ProductListingScreen({super.key});

  @override
  State<ProductListingScreen> createState() => _ProductListingScreenState();
}

class _ProductListingScreenState extends State<ProductListingScreen> {
  // Dummy data matching the reference design
  final List<Product> _products = MockDataService.products;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(
        context,
      ).scaffoldBackgroundColor, // Dark background
      body: Stack(
        children: [
          // Background Noise Texture
          Positioned.fill(
            child: Opacity(
              opacity: 0.1,
              child: Image.asset(
                'assets/images/noise.png',
                repeat: ImageRepeat.repeat,
              ),
            ),
          ),
          SafeArea(
            bottom: false,
            child: CustomScrollView(
              slivers: [
                const SliverAppBar(
                  floating: true,
                  snap: true,
                  automaticallyImplyLeading: false,
                  backgroundColor: Colors.transparent,
                  elevation: 0,
                  toolbarHeight: 70,
                  flexibleSpace: FlexibleSpaceBar(background: FilterBar()),
                ),
                // Product Grid
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 140),
                  sliver: SliverGrid.builder(
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          mainAxisSpacing: 24,
                          crossAxisSpacing: 16,
                          childAspectRatio: 0.65, // Adjusted for subtitle
                        ),
                    itemCount: _products.length,
                    itemBuilder: (context, index) {
                      final product = _products[index];
                      return ProductCard(
                        imagePath: product.images.first,
                        title: product.title,
                        subtitle: product.subtitle,
                        price: product.formattedPrice,
                        width: null, // Allow flexible width
                        margin: AppPadding.zero, // No margin in grid
                        onTap: () {
                          Navigator.of(context, rootNavigator: true).push(
                            MaterialPageRoute(
                              builder: (context) =>
                                  ProductDetailScreen(product: product),
                            ),
                          );
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
