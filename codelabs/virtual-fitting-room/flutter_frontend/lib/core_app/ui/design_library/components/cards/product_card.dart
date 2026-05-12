import 'package:flutter/material.dart';

import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/cards/app_card.dart';

class ProductCard extends StatelessWidget {
  final String imagePath;
  final String title;
  final String? subtitle;
  final String price;
  final VoidCallback? onTap;
  final double? width;
  final EdgeInsetsGeometry? margin;

  const ProductCard({
    super.key,
    required this.imagePath,
    required this.title,
    this.subtitle,
    required this.price,
    this.onTap,
    this.width = 160,
    this.margin = const EdgeInsets.only(right: AppSizes.s16),
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AppCard(
        width: width,
        margin: margin,
        borderRadius: AppRadius.circular16,
        shadows: AppShadows.productCard,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: ProductImage(imagePath: imagePath)),
            ProductDetails(title: title, subtitle: subtitle, price: price),
          ],
        ),
      ),
    );
  }
}

class ProductImage extends StatelessWidget {
  final String imagePath;

  const ProductImage({super.key, required this.imagePath});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: AppRadius.verticalTop16,
      child: Image.asset(
        imagePath,
        fit: BoxFit.cover,
        width: double.infinity,
        height: double.infinity,
      ),
    );
  }
}

class ProductDetails extends StatelessWidget {
  final String title;
  final String? subtitle;
  final String price;

  const ProductDetails({
    super.key,
    required this.title,
    this.subtitle,
    required this.price,
  });

  @override
  Widget build(BuildContext context) {
    final currentSubtitle = subtitle;

    return Padding(
      padding: AppPadding.all12,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.productTitle.copyWith(
              color: Theme.of(context).colorScheme.onSurface,
            ),
          ),
          if (currentSubtitle != null) ...[
            const SizedBox(height: AppSizes.s2),
            Text(
              currentSubtitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTextStyles.productSubtitle.copyWith(
                color: Theme.of(context).colorScheme.tertiary, // gray-400
              ),
            ),
          ],
          const SizedBox(height: AppSizes.s4),
          Text(
            price,
            style: AppTextStyles.productPrice.copyWith(
              color: Theme.of(context).colorScheme.primary.withValues(
                alpha: 0.8,
              ), // Muted pink derived from primary
            ),
          ),
        ],
      ),
    );
  }
}
