import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/outfit.dart';

class MockDataService {
  static const List<Product> products = [
    Product(
      id: '1',
      images: [
        'assets/images/product_1.png',
        'assets/images/prod1_var1.png',
        'assets/images/prod1_var2.png',
      ],
      title: 'Floral Summer Dress',
      subtitle: 'Summer Collection',
      price: 49.99,
    ),
    Product(
      id: '2',
      images: [
        'assets/images/product_2.png',
        'assets/images/prod2_var1.png',
        'assets/images/prod2_var2.png',
      ],
      title: 'Classic Denim Jeans',
      subtitle: 'Premium Denim',
      price: 59.99,
    ),
    Product(
      id: '3',
      images: [
        'assets/images/product_3.png',
        'assets/images/prod3_var1.png',
        'assets/images/prod3_var2.png',
      ],
      title: 'White Cotton Tee',
      subtitle: 'Organic Cotton',
      price: 24.99,
    ),
    Product(
      id: '4',
      images: [
        'assets/images/product_4.png',
        'assets/images/prod4_var1.png',
        'assets/images/prod4_var2.png',
      ],
      title: 'Leather Ankle Boots',
      subtitle: 'Genuine Leather',
      price: 89.99,
    ),
    Product(
      id: '5',
      images: [
        'assets/images/product_1.png',
        'assets/images/prod5_var1.png',
        'assets/images/prod5_var2.png',
      ],
      title: 'Red Cocktail Dress',
      subtitle: 'Evening Glam',
      price: 129.00,
    ),
    Product(
      id: '6',
      images: [
        'assets/images/product_2.png',
        'assets/images/prod6_var1.png',
        'assets/images/prod6_var2.png',
      ],
      title: 'Denim Shirt Dress',
      subtitle: 'Casual Day',
      price: 55.99,
    ),
    Product(
      id: '7',
      images: [
        'assets/images/bomber_jacket.png',
        'assets/images/prod7_var1.png',
        'assets/images/prod7_var2.png',
      ],
      title: 'Cropped Bomber',
      subtitle: 'Street Style',
      price: 85.00,
    ),
    Product(
      id: '8',
      images: [
        'assets/images/hightop.png',
        'assets/images/prod8_var1.png',
        'assets/images/prod8_var2.png',
      ],
      title: 'Classic High Tops',
      subtitle: 'Kicks & Co.',
      price: 95.00,
    ),
    Product(
      id: '9',
      images: [
        'assets/images/plaid_shirt.png',
        'assets/images/prod9_var1.png',
        'assets/images/prod9_var2.png',
      ],
      title: 'Plaid Button Up',
      subtitle: 'Cozy Flannel',
      price: 45.00,
    ),
    Product(
      id: '10',
      images: [
        'assets/images/quarter-zip.png',
        'assets/images/prod10_var1.png',
        'assets/images/prod10_var2.png',
      ],
      title: 'Quarter-Zip Pullover',
      subtitle: 'Active Wear',
      price: 60.00,
    ),
    Product(
      id: '11',
      images: [
        'assets/images/flutter_hat.png',
        'assets/images/prod11_var1.png',
        'assets/images/prod11_var2.png',
      ],
      title: 'Flutter Hat',
      subtitle: 'Headwear',
      price: 25.00,
    ),
    Product(
      id: '12',
      images: [
        'assets/images/flutter_letterman.png',
        'assets/images/prod12_var1.png',
        'assets/images/prod12_var2.png',
      ],
      title: 'Letterman Jacket',
      subtitle: 'Varsity Style',
      price: 110.00,
    ),
  ];

  static List<Product> pick(int count) {
    var shuffledList = List<Product>.from(products)..shuffle();
    return shuffledList.take(count).toList();
  }

  static List<Outfit> getMockOutfits() {
    final list = List<Product>.from(products)..shuffle();
    return [
      Outfit(
        imagePath: 'assets/images/outfit_casual.png',
        products: list.sublist(0, 3),
        commentary:
            'A classic, relaxed look perfect for daytime errands or casual hangouts. The breathable fabrics keep it effortless and comfortable.',
      ),
      Outfit(
        imagePath: 'assets/images/outfit_floral.png',
        products: list.sublist(3, 5),
        commentary:
            'Soft and feminine. The floral patterns inject a cheerful vibe, making this the ideal ensemble for a sunny brunch or outdoor date.',
      ),
      Outfit(
        imagePath: 'assets/images/outfit_streetwear.png',
        products: list.sublist(5, 9),
        commentary:
            'Edgy and modern streetwear. Layering these pieces adds great depth, while the strong silhouettes ensure you stand out in the city.',
      ),
      Outfit(
        imagePath: 'assets/images/outfit_evening.png',
        products: list.sublist(9, 12),
        commentary:
            'Sleek and sophisticated. This curated evening look relies on elegant lines to provide a confident, premium aesthetic for night events.',
      ),
    ];
  }

  static Future<List<Outfit>> getAlternativeOutfits(String feedback) async {
    // Simulate network delay for AI processing
    await Future.delayed(const Duration(seconds: 2));

    // Return new random combinations of products out of the mock data as new outfits
    final list = List<Product>.from(products)..shuffle();
    return [
      Outfit(
        imagePath: 'assets/images/outfit_casual.png',
        products: list.sublist(0, 4),
        commentary:
            'Based on your feedback, I leaned into a more grounded everyday look. The extra layering piece adds versatility while keeping the focus on comfort.',
      ),
      Outfit(
        imagePath: 'assets/images/outfit_floral.png',
        products: list.sublist(4, 7),
        commentary:
            'Pivoting slightly, this variation emphasizes lighter tones and subtle patterns per your notes. It feels fresh and highly approachable.',
      ),
      Outfit(
        imagePath: 'assets/images/outfit_streetwear.png',
        products: list.sublist(7, 10),
        commentary:
            'A bolder take on the previous direction. I swapped out the basics for more structured, eye-catching items that elevate the entire fit.',
      ),
    ];
  }
}
