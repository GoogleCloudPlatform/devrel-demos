import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class ProductSelectorList extends StatelessWidget {
  final List<Product> products;
  final int selectedProductIndex;
  final void Function(int) onProductSelected;

  const ProductSelectorList({
    super.key,
    required this.products,
    required this.selectedProductIndex,
    required this.onProductSelected,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 80,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: products.length,
        itemBuilder: (context, index) {
          final isSelected = selectedProductIndex == index;
          return GestureDetector(
            onTap: () => onProductSelected(index),
            child: Container(
              margin: const EdgeInsets.only(right: AppSizes.s16),
              width: 80,
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(
                color: Theme.of(
                  context,
                ).colorScheme.onSurface.withValues(alpha: 0.1),
                borderRadius: AppRadius.circular16,
                border: isSelected
                    ? Border.all(
                        color: Theme.of(context).colorScheme.primary,
                        width: 2,
                      )
                    : null,
              ),
              padding: AppPadding.all8,
              child: ClipRRect(
                borderRadius: AppRadius.circular8,
                child: Image.asset(
                  products[index].productImage,
                  fit: BoxFit.contain,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
