import 'dart:typed_data';
import 'package:fashion_app/core_app/models/product.dart';

class Outfit {
  final String imagePath;
  final Uint8List? imageData;
  final List<Product> products;
  final String commentary;

  const Outfit({
    required this.imagePath,
    this.imageData,
    required this.products,
    this.commentary = '',
  });
}
