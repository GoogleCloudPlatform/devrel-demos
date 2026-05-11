import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/core_app/ui/design_library/components/cards/product_card.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/ui/1_product_detail_screen.dart';

class JustForYouSection extends StatelessWidget {
  final List<Product> products;

  const JustForYouSection({super.key, required this.products});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 24, 16, 12),
          child: Text(
            'Just For You',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.onSurface,
            ),
          ),
        ),
        Padding(
          padding: AppPadding.horizontal16,
          child: GridView.builder(
            padding: EdgeInsets.zero,
            physics: const NeverScrollableScrollPhysics(),
            shrinkWrap: true,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              mainAxisSpacing: 24,
              crossAxisSpacing: 16,
              childAspectRatio: 0.7,
            ),
            itemCount: products.length,
            itemBuilder: (context, index) {
              // Reversing list for variety
              final product = products[products.length - 1 - index];
              return ProductCard(
                imagePath: product.images.first,
                title: product.title,
                price: product.formattedPrice,
                width: null,
                margin: AppPadding.zero,
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
    );
  }
}
