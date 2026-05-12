import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/core_app/providers/cart_provider.dart';
import 'package:fashion_app/core_app/ui/screens/cart/shopping_cart_screen.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/primary_button.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/secondary_button.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

/// Reusable "Add to Bag" button that encapsulates cart state logic,
/// handling both initial additions and navigating to the cart if already added.
/// [selectedColor] and [selectedSize] are optional to support generic catalog usage.
class AddToBagButton extends StatelessWidget {
  final Product product;
  final Color? selectedColor;
  final String? selectedSize;

  const AddToBagButton({
    super.key,
    required this.product,
    this.selectedColor,
    this.selectedSize,
  });

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<CartProvider>();
    final inCart = cart.hasProduct(
      product,
      color: selectedColor,
      size: selectedSize,
    );

    return Expanded(
      child: inCart
          ? SecondaryButton(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const ShoppingCartScreen(),
                  ),
                );
              },
              text: 'View Bag',
            )
          : PrimaryButton(
              onPressed: () {
                context.read<CartProvider>().addItem(
                  product,
                  color: selectedColor,
                  size: selectedSize,
                );
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Row(
                      children: [
                        Icon(Icons.check_circle_outline, color: Colors.green),
                        SizedBox(width: AppSizes.s8),
                        Text('Added to Bag'),
                      ],
                    ),
                    duration: AppDurations.standard,
                  ),
                );
              },
              text: 'Add to Bag',
            ),
    );
  }
}
