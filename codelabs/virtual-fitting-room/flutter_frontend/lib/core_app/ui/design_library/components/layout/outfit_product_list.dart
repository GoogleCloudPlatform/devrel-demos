import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/providers/cart_provider.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/outfit.dart';
import 'package:fashion_app/core_app/ui/screens/cart/shopping_cart_screen.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/primary_button.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/secondary_button.dart';

class OutfitProductList extends StatelessWidget {
  final Outfit outfit;

  const OutfitProductList({super.key, required this.outfit});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          height: 172,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: outfit.products.length,
            separatorBuilder: (context, index) => const SizedBox(width: AppSizes.s8),
            itemBuilder: (context, index) {
              final product = outfit.products[index];
              return SizedBox(
                width: 120,
                child: Container(
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surface,
                    borderRadius: AppRadius.circular12,
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.2),
                    ),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      AspectRatio(
                        aspectRatio: 1,
                        child: Image.asset(
                          product.productImage.isNotEmpty
                              ? product.productImage
                              : 'assets/images/placeholder.png',
                          fit: BoxFit.cover,
                          cacheWidth: 300,
                        ),
                      ),
                      Padding(
                        padding: AppPadding.all8,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              product.title,
                              style: Theme.of(context).textTheme.bodySmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.w600,
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.onSurface,
                                  ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: AppSizes.s2),
                            Text(
                              product.formattedPrice,
                              style: Theme.of(context).textTheme.labelSmall
                                  ?.copyWith(
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.onSurfaceVariant,
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: AppSizes.s12),
        Consumer<CartProvider>(
          builder: (context, cart, child) {
            final inCart = cart.hasOutfit(outfit.products);
            void handlePress() {
              if (inCart) {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const ShoppingCartScreen(),
                  ),
                );
              } else {
                cart.addMultipleItems(outfit.products);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Row(
                      children: [
                        Icon(Icons.check_circle_outline, color: Colors.green),
                        SizedBox(width: AppSizes.s8),
                        Text('Outfit added to Bag'),
                      ],
                    ),
                    duration: AppDurations.slow,
                  ),
                );
              }
            }

            return inCart
                ? SecondaryButton(
                    onPressed: handlePress,
                    text: 'View Bag',
                  )
                : PrimaryButton(
                    onPressed: handlePress,
                    text: 'Add Outfit to Bag',
                  );
          },
        ),
      ],
    );
  }
}
