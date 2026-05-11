import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppSizes {
  // Spacing and Paddings
  static const double s2 = 2.0;
  static const double s4 = 4.0;
  static const double s6 = 6.0;
  static const double s8 = 8.0;
  static const double s12 = 12.0;
  static const double s16 = 16.0;
  static const double s20 = 20.0;
  static const double s24 = 24.0;
  static const double s32 = 32.0;
  static const double s48 = 48.0;

  // Icon Sizes
  static const double iconExtraSmall = 16.0;
  static const double iconSmall = 18.0;
  static const double iconNormal = 20.0;
  static const double iconMedium = 28.0;
  static const double iconLarge = 30.0;
  static const double iconExtraLarge = 64.0;
}

class AppPadding {
  static const EdgeInsets zero = EdgeInsets.zero;

  static const EdgeInsets all8 = EdgeInsets.all(AppSizes.s8);
  static const EdgeInsets all12 = EdgeInsets.all(AppSizes.s12);
  static const EdgeInsets all16 = EdgeInsets.all(AppSizes.s16);
  static const EdgeInsets all20 = EdgeInsets.all(AppSizes.s20);
  static const EdgeInsets all24 = EdgeInsets.all(AppSizes.s24);

  static const EdgeInsets horizontal4 = EdgeInsets.symmetric(
    horizontal: AppSizes.s4,
  );
  static const EdgeInsets horizontal6 = EdgeInsets.symmetric(
    horizontal: AppSizes.s6,
  );
  static const EdgeInsets horizontal16 = EdgeInsets.symmetric(
    horizontal: AppSizes.s16,
  );
  static const EdgeInsets horizontal24 = EdgeInsets.symmetric(
    horizontal: AppSizes.s24,
  );
  static const EdgeInsets horizontal32 = EdgeInsets.symmetric(
    horizontal: AppSizes.s32,
  );
  static const EdgeInsets horizontal48 = EdgeInsets.symmetric(
    horizontal: AppSizes.s48,
  );

  static const EdgeInsets vertical8 = EdgeInsets.symmetric(
    vertical: AppSizes.s8,
  );
  static const EdgeInsets vertical16 = EdgeInsets.symmetric(
    vertical: AppSizes.s16,
  );
  static const EdgeInsets vertical20 = EdgeInsets.symmetric(
    vertical: AppSizes.s20,
  );
  static const EdgeInsets vertical24 = EdgeInsets.symmetric(
    vertical: AppSizes.s24,
  );
}

class AppRadius {
  static const BorderRadius circular4 = BorderRadius.all(Radius.circular(4.0));
  static const BorderRadius circular8 = BorderRadius.all(Radius.circular(8.0));
  static const BorderRadius circular12 = BorderRadius.all(
    Radius.circular(12.0),
  );
  static const BorderRadius circular16 = BorderRadius.all(
    Radius.circular(16.0),
  );
  static const BorderRadius circular20 = BorderRadius.all(
    Radius.circular(20.0),
  );
  static const BorderRadius circular24 = BorderRadius.all(
    Radius.circular(24.0),
  );
  static const BorderRadius circular30 = BorderRadius.all(
    Radius.circular(30.0),
  );
  static const BorderRadius circular32 = BorderRadius.all(
    Radius.circular(32.0),
  );
  static const BorderRadius verticalTop16 = BorderRadius.vertical(
    top: Radius.circular(16.0),
  );
  static const BorderRadius verticalTop24 = BorderRadius.vertical(
    top: Radius.circular(24.0),
  );
}

class AppDurations {
  static const Duration fast = Duration(milliseconds: 300);
  static const Duration medium = Duration(milliseconds: 500);
  static const Duration standard = Duration(milliseconds: 800);
  static const Duration slow = Duration(seconds: 3);
  static const Duration verySlow = Duration(seconds: 5);
  
  static const Duration loadingOverlayLoop = Duration(seconds: 60);
  static const Duration loadingOverlayMessageCycle = Duration(seconds: 4);
}

class AppTextStyles {
  static final TextStyle headlineLarge = GoogleFonts.plusJakartaSans(
    fontSize: 24,
    fontWeight: FontWeight.bold,
  );

  static final TextStyle bodyLarge = GoogleFonts.plusJakartaSans(
    fontSize: 16,
    height: 1.5,
  );

  static final TextStyle appBarTitle = GoogleFonts.plusJakartaSans(
    fontWeight: FontWeight.bold,
    fontSize: 20,
  );

  static final TextStyle productTitle = GoogleFonts.plusJakartaSans(
    fontSize: 14,
    fontWeight: FontWeight.bold,
  );

  static final TextStyle productSubtitle = GoogleFonts.plusJakartaSans(
    fontSize: 12,
    fontWeight: FontWeight.normal,
  );

  static final TextStyle productPrice = GoogleFonts.plusJakartaSans(
    fontSize: 14,
    fontWeight: FontWeight.w600,
  );

  static final TextStyle buttonLg = GoogleFonts.plusJakartaSans(
    fontSize: 18,
    fontWeight: FontWeight.bold,
  );

  static final TextStyle buttonSm = GoogleFonts.plusJakartaSans(
    fontSize: 16,
    fontWeight: FontWeight.bold,
  );

  static final TextStyle accordionTitle = GoogleFonts.plusJakartaSans(
    fontSize: 18,
    fontWeight: FontWeight.bold,
  );

  static final TextStyle textFieldText = GoogleFonts.plusJakartaSans();

  static final TextStyle textFieldHint = GoogleFonts.plusJakartaSans(
    fontSize: 14,
  );

  static final TextStyle filterChip = GoogleFonts.plusJakartaSans(
    fontSize: 18,
    fontWeight: FontWeight.w500,
  );

  static final TextStyle selectableChip = GoogleFonts.plusJakartaSans(
    fontWeight: FontWeight.bold,
  );
}

class AppShadows {
  static final List<BoxShadow> productCard = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.4),
      blurRadius: 15,
      offset: const Offset(0, 8),
    ),
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.2),
      blurRadius: 4,
      offset: const Offset(0, 2),
    ),
  ];

  static final List<BoxShadow> defaultCard = [
    BoxShadow(
      color: Colors.black.withValues(alpha: 0.05),
      blurRadius: 10,
      offset: const Offset(0, 5),
    ),
  ];
}
