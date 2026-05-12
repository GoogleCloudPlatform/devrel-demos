import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/screens/main_screen.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/primary_button.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/secondary_button.dart';

class WelcomeContent extends StatelessWidget {
  final int totalPages;
  final int currentPage;

  const WelcomeContent({
    super.key,
    required this.totalPages,
    required this.currentPage,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        children: [
          // Skip Button
          Align(
            alignment: Alignment.topRight,
            child: TextButton(
              onPressed: () {
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (context) => const MainScreen()),
                );
              },
              child: Text(
                'Skip',
                style: GoogleFonts.plusJakartaSans(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
            ),
          ),
          const Spacer(),
          // Headline
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSizes.s16,
              vertical: AppSizes.s8,
            ),
            child: Text(
              'Discover Your Style',
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                color: Colors.white,
                fontSize: 30,
                fontWeight: FontWeight.bold,
                height: 1.2,
              ),
            ),
          ),
          // Body Text
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSizes.s16,
              vertical: AppSizes.s4,
            ),
            child: Text(
              'Explore curated collections and get personalized recommendations tailored just for you.',
              textAlign: TextAlign.center,
              style: GoogleFonts.plusJakartaSans(
                color: Theme.of(context).colorScheme.tertiary, // gray-300
                fontSize: 16,
                fontWeight: FontWeight.normal,
              ),
            ),
          ),
          // Page Indicators
          Padding(
            padding: AppPadding.vertical20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(totalPages, (index) {
                return Container(
                  margin: AppPadding.horizontal6,
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: currentPage == index
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).colorScheme.secondary, // gray-700
                    shape: BoxShape.circle,
                  ),
                );
              }),
            ),
          ),
          // Buttons
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSizes.s16,
              vertical: AppSizes.s12,
            ),
            child: Column(
              children: [
                PrimaryButton(
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const MainScreen(),
                      ),
                    );
                  },
                  text: 'Create Account',
                  height: 48,
                ),
                const SizedBox(height: 12),
                SecondaryButton(
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const MainScreen(),
                      ),
                    );
                  },
                  text: 'Log In',
                  height: 48,
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}
