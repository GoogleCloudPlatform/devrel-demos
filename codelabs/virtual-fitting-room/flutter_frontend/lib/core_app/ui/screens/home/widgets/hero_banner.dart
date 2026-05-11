import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/primary_button.dart';

class HeroBanner extends StatelessWidget {
  final String imagePath;
  final String title;
  final VoidCallback onActionPressed;
  final String actionLabel;

  const HeroBanner({
    super.key,
    required this.imagePath,
    required this.title,
    required this.onActionPressed,
    this.actionLabel = 'Shop Now',
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: AppPadding.all16,
      height: 320, // Taller hero as per reference
      decoration: BoxDecoration(
        borderRadius: AppRadius.circular16,
        image: DecorationImage(
          image: AssetImage(imagePath),
          fit: BoxFit.cover,
          alignment: Alignment.topCenter,
        ),
      ),
      child: Stack(
        children: [
          // Gradient Overlay
          Container(
            decoration: BoxDecoration(
              borderRadius: AppRadius.circular16,
              gradient: LinearGradient(
                begin: Alignment.bottomCenter,
                end: Alignment.topCenter,
                colors: [
                  Colors.black.withValues(alpha: 0.4),
                  Colors.transparent,
                ],
                stops: const [0.0, 0.4],
              ),
            ),
          ),
          // Content
          Padding(
            padding: AppPadding.all20,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 16),
                PrimaryButton(
                  onPressed: onActionPressed,
                  text: actionLabel,
                  isFullWidth: false,
                  height: 48,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
