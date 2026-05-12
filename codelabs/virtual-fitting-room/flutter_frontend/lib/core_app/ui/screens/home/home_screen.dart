import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/core_app/services/mock/mock_data_service.dart';
import 'package:fashion_app/core_app/ui/screens/home/widgets/hero_banner.dart';
import 'package:fashion_app/core_app/ui/screens/home/widgets/new_in_section.dart';
import 'package:fashion_app/core_app/ui/screens/home/widgets/just_for_you_section.dart';
import 'package:fashion_app/core_app/ui/screens/product_listing/product_listing_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final List<Product> _products = MockDataService.products.take(4).toList();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface, // Dark background
      body: Stack(
        children: [
          // Background Noise Texture
          Positioned.fill(
            child: Opacity(
              opacity: 0.1,
              child: Image.asset(
                'assets/images/noise.png', // Assuming we have or will add this
                repeat: ImageRepeat.repeat,
              ),
            ),
          ),
          CustomScrollView(
            slivers: [
              // Hero Banner
              SliverToBoxAdapter(
                child: HeroBanner(
                  imagePath: 'assets/images/product_1.png',
                  title: 'The Summer Edit\nis Here',
                  onActionPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const ProductListingScreen(),
                      ),
                    );
                  },
                ),
              ),

              // New In Section
              SliverToBoxAdapter(child: NewInSection(products: _products)),

              // Just For You Section
              SliverToBoxAdapter(child: JustForYouSection(products: _products)),

              // Bottom Padding for Nav Bar
              const SliverToBoxAdapter(child: SizedBox(height: 150)),
            ],
          ),
        ],
      ),
    );
  }
}
