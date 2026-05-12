import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/outfit.dart';
import 'package:fashion_app/core_app/ui/design_library/components/cards/outfit_card.dart';

/// A horizontally scrolling carousel that displays a list of [outfits].
class OutfitCarousel extends StatefulWidget {
  /// The list of generated outfits.
  final List<Outfit> outfits;

  const OutfitCarousel({
    super.key,
    required this.outfits,
  });

  @override
  State<OutfitCarousel> createState() => _OutfitCarouselState();
}

class _OutfitCarouselState extends State<OutfitCarousel> {
  late PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(viewportFraction: 0.82);
  }

  @override
  void didUpdateWidget(covariant OutfitCarousel oldWidget) {
    super.didUpdateWidget(oldWidget);
    // If the outfits list reference changes (e.g., new suggestions from feedback),
    // automatically jump the carousel back to the first card.
    if (oldWidget.outfits != widget.outfits && _pageController.hasClients) {
      _pageController.jumpToPage(0);
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PageView.builder(
      controller: _pageController,
      itemCount: widget.outfits.length,
      itemBuilder: (context, index) {
        return AnimatedBuilder(
          animation: _pageController,
          builder: (context, child) {
            double value = 1.0;
            if (_pageController.position.haveDimensions) {
              value = (_pageController.page! - index).abs();
            } else {
              value = index.toDouble();
            }
            final scale = (1 - (value * 0.12)).clamp(0.85, 1.0);
            final opacity = (1 - (value * 0.4)).clamp(0.4, 1.0);

            return Transform.scale(
              scale: scale,
              child: Opacity(
                opacity: opacity,
                child: child,
              ),
            );
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSizes.s4,
            ),
            child: OutfitCard(outfit: widget.outfits[index]),
          ),
        );
      },
    );
  }
}
