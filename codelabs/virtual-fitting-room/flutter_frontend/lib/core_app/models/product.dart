class Product {
  final String id;
  final String title;
  final String subtitle;
  final double price;
  final List<String> images;

  const Product({
    required this.id,
    required this.title,
    this.subtitle = '',
    required this.price,
    required this.images,
  });

  String get formattedPrice => '\$${price.toStringAsFixed(2)}';

  String get productImage => images.isNotEmpty ? images.first : '';
}
