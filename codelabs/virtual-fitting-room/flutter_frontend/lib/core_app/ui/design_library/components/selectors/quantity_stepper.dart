import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class QuantityStepper extends StatelessWidget {
  final int quantity;
  final ValueChanged<int> onQuantityChanged;

  const QuantityStepper({
    super.key,
    required this.quantity,
    required this.onQuantityChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: AppRadius.circular20,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.remove, size: AppSizes.iconExtraSmall),
            onPressed: () {
              if (quantity > 1) {
                onQuantityChanged(quantity - 1);
              }
            },
            padding: const EdgeInsets.all(AppSizes.s4),
            constraints: const BoxConstraints(),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSizes.s8),
            child: Text(
              '$quantity',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.add, size: AppSizes.iconExtraSmall),
            onPressed: () => onQuantityChanged(quantity + 1),
            padding: const EdgeInsets.all(AppSizes.s4),
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }
}
