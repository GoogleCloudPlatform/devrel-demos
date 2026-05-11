import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/app_accordion.dart';
import 'package:google_fonts/google_fonts.dart';

class ExpandableSection extends StatelessWidget {
  final String title;
  final String content;

  const ExpandableSection({
    super.key,
    required this.title,
    required this.content,
  });

  @override
  Widget build(BuildContext context) {
    return AppAccordion(
      title: title,
      child: Text(
        content,
        style: GoogleFonts.plusJakartaSans(
          fontSize: 14,
          color: Theme.of(context).colorScheme.tertiary,
          height: 1.5,
        ),
      ),
    );
  }
}
