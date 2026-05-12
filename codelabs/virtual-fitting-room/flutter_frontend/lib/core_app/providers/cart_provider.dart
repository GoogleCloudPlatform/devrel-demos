import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/models/cart_item.dart';
import 'package:fashion_app/core_app/models/product.dart';

/// `CartProvider` manages the global state for the shopping cart.
/// It extends `ChangeNotifier`, which allows it to broadcast updates to the UI
/// whenever the cart's data changes, causing only the relevant widgets to rebuild.
class CartProvider extends ChangeNotifier {
  /// The internal list of cart items. It is private (`_`) to enforce encapsulation.
  /// UI components cannot directly mutate this list (e.g., `_items.add()`) without
  /// using the designated methods, ensuring `notifyListeners()` is always called.
  final List<CartItem> _items = [];

  /// Exposes the cart items to the UI as a read-only list.
  /// This prevents external code from accidentally modifying the underlying array array
  /// without triggering a UI rebuild.
  List<CartItem> get items => List.unmodifiable(_items);

  /// Computed property that calculates the total cost of all items.
  /// Using a getter instead of calculating this in the UI centralizes business logic.
  /// The `fold` method iterates over the list to accumulate a single double value.
  double get subtotal {
    return _items.fold(0.0, (sum, item) => sum + item.totalPrice);
  }

  double get tax {
    // Mock 8% tax
    return subtotal * 0.08;
  }

  double get total {
    return subtotal + tax;
  }

  int get totalItemCount {
    return _items.fold(0, (sum, item) => sum + item.quantity);
  }

  bool hasProduct(Product product, {String? size, Color? color}) {
    return _items.any(
      (item) =>
          item.product.id == product.id &&
          (size == null || item.selectedSize == size) &&
          (color == null || item.selectedColor == color),
    );
  }

  bool hasOutfit(List<Product> products) {
    if (products.isEmpty) return false;
    // Check if EVERY product in the outfit is currently in the cart
    return products.every((product) => hasProduct(product));
  }

  /// Adds a product to the cart or increments its quantity if it already exists.
  /// We handle the cart business logic here (like grouping identical items) so the UI
  /// only has to say "add this".
  void addItem(Product product, {String? size, Color? color}) {
    // Check if identical item (same product ID, size, and color) exists in the cart.
    // This acts as a collision check to avoid creating duplicate rows in the UI.
    final index = _items.indexWhere(
      (item) =>
          item.product.id == product.id &&
          item.selectedSize == size &&
          item.selectedColor == color,
    );

    if (index >= 0) {
      // If found, increment quantity.
      // We use `.copyWith()` to replace the existing item with a brand new,
      // immutable CartItem instance that has the updated quantity.
      final existingItem = _items[index];
      _items[index] = existingItem.copyWith(
        quantity: existingItem.quantity + 1,
      );
    } else {
      // Add new item
      _items.add(
        CartItem(
          product: product,
          selectedSize: size,
          selectedColor: color,
          quantity: 1,
        ),
      );
    }
    notifyListeners();
  }

  /// A convenience method to add an entire outfit (multiple products)
  /// to the cart with a single action. It delegates to `addItem` in a loop.
  void addMultipleItems(List<Product> products) {
    for (var product in products) {
      addItem(product);
    }
    notifyListeners();
  }

  void removeItem(CartItem itemToRemove) {
    _items.remove(itemToRemove);
    notifyListeners();
  }

  void updateQuantity(CartItem item, int newQuantity) {
    if (newQuantity <= 0) {
      _items.remove(item);
    } else {
      final index = _items.indexOf(item);
      if (index >= 0) {
        _items[index] = item.copyWith(quantity: newQuantity);
      }
    }
    notifyListeners();
  }

  void clearCart() {
    _items.clear();
    notifyListeners();
  }
}
