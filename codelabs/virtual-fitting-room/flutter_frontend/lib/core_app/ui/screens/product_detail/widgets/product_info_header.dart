import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class ProductInfoHeader extends StatelessWidget {
  final String title;
  final String price;

  const ProductInfoHeader({
    super.key,
    required this.title,
    required this.price,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: AppPadding.all16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Theme.of(context).colorScheme.onSurface,
                    height: 1.1,
                  ),
                ),
              ),
              Text(
                price,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              const Icon(Icons.star, color: Color(0xFFFACC15), size: 18),
              const Icon(Icons.star, color: Color(0xFFFACC15), size: 18),
              const Icon(Icons.star, color: Color(0xFFFACC15), size: 18),
              const Icon(Icons.star, color: Color(0xFFFACC15), size: 18),
              const Icon(Icons.star, color: Color(0xFFFACC15), size: 18),
              const SizedBox(width: 8),
              Text(
                '(132 Reviews)',
                style: GoogleFonts.plusJakartaSans(
                  color: Theme.of(context).colorScheme.tertiary, // gray-400
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
