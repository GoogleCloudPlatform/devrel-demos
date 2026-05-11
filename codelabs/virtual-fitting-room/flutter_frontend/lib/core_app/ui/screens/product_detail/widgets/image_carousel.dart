import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class ImageCarousel extends StatefulWidget {
  final List<String> images;

  const ImageCarousel({super.key, required this.images});

  @override
  State<ImageCarousel> createState() => _ImageCarouselState();
}

class _ImageCarouselState extends State<ImageCarousel> {
  int _currentImageIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        PageView.builder(
          itemCount: widget.images.length,
          onPageChanged: (index) {
            setState(() {
              _currentImageIndex = index;
            });
          },
          itemBuilder: (context, index) {
            return Hero(
              tag: 'product_image_$index',
              child: Image.asset(widget.images[index], fit: BoxFit.cover),
            );
          },
        ),
        // Simple Carousel Indicator
        Positioned(
          bottom: 24,
          left: 0,
          right: 0,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(widget.images.length, (index) {
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: CarouselIndicator(isActive: index == _currentImageIndex),
              );
            }),
          ),
        ),
      ],
    );
  }
}

class CarouselIndicator extends StatelessWidget {
  final bool isActive;

  const CarouselIndicator({super.key, required this.isActive});

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      height: 8,
      width: isActive ? 24 : 8,
      decoration: BoxDecoration(
        color: isActive
            ? Theme.of(context).colorScheme.primary
            : Theme.of(
                context,
              ).scaffoldBackgroundColor, // Dark maroon app background
        borderRadius: AppRadius.circular4,
        border: Border.all(
          color: Colors.white.withValues(
            alpha: 0.8,
          ), // White rim for light/dark contrast
          width: 0.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.4), // Stronger shadow
            blurRadius: 3,
            offset: const Offset(0, 1),
          ),
        ],
      ),
    );
  }
}
