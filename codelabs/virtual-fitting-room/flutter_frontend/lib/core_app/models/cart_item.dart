import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/models/product.dart';

class CartItem {
  final Product product;
  final int quantity;
  final String? selectedSize;
  final Color? selectedColor;

  const CartItem({
    required this.product,
    this.quantity = 1,
    this.selectedSize,
    this.selectedColor,
  });

  double get totalPrice {
    return product.price * quantity;
  }

  String get formattedTotalPrice => '\$${totalPrice.toStringAsFixed(2)}';

  CartItem copyWith({
    Product? product,
    int? quantity,
    String? selectedSize,
    Color? selectedColor,
  }) {
    return CartItem(
      product: product ?? this.product,
      quantity: quantity ?? this.quantity,
      selectedSize: selectedSize ?? this.selectedSize,
      selectedColor: selectedColor ?? this.selectedColor,
    );
  }
}
