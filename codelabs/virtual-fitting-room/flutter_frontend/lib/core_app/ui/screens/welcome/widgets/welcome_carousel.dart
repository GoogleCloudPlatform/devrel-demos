import 'package:flutter/material.dart';

class WelcomeCarousel extends StatelessWidget {
  final List<String> images;
  final PageController pageController;
  final ValueChanged<int> onPageChanged;

  const WelcomeCarousel({
    super.key,
    required this.images,
    required this.pageController,
    required this.onPageChanged,
  });

  @override
  Widget build(BuildContext context) {
    return PageView.builder(
      controller: pageController,
      itemCount: images.length,
      onPageChanged: onPageChanged,
      itemBuilder: (context, index) {
        return Image.asset(images[index], fit: BoxFit.cover);
      },
    );
  }
}
