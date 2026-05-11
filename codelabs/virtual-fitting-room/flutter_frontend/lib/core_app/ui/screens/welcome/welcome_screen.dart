import 'package:flutter/material.dart';
import 'dart:async';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/screens/welcome/widgets/welcome_carousel.dart';
import 'package:fashion_app/core_app/ui/screens/welcome/widgets/welcome_content.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  final List<String> _images = [
    'assets/images/product_1.png',
    'assets/images/product_2.png',
    'assets/images/product_3.png',
    'assets/images/product_4.png',
  ];

  int _currentPage = 0;
  late PageController _pageController;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(initialPage: 0);
    _startAutoScroll();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pageController.dispose();
    super.dispose();
  }

  void _startAutoScroll() {
    _timer = Timer.periodic(AppDurations.slow, (Timer timer) {
      if (_currentPage < _images.length - 1) {
        _currentPage++;
      } else {
        _currentPage = 0;
      }

      if (_pageController.hasClients) {
        _pageController.animateToPage(
          _currentPage,
          duration: AppDurations.standard,
          curve: Curves.easeInOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Background Image Carousel
          Positioned.fill(
            child: WelcomeCarousel(
              images: _images,
              pageController: _pageController,
              onPageChanged: (index) {
                setState(() {
                  _currentPage = index;
                });
              },
            ),
          ),
          // Gradient Overlay
          Positioned.fill(
            child: IgnorePointer(
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      const Color(
                        0xFF221015,
                      ).withValues(alpha: 0.0), // rgba(34, 16, 21, 0)
                      const Color(
                        0xFF221015,
                      ).withValues(alpha: 0.6), // rgba(34, 16, 21, 0.6)
                    ],
                    stops: const [0.4, 1.0],
                  ),
                ),
              ),
            ),
          ),
          // Content
          WelcomeContent(totalPages: _images.length, currentPage: _currentPage),
        ],
      ),
    );
  }
}
