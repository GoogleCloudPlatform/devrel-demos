import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/app_button.dart';

class ChangePhotoButton extends StatelessWidget {
  final VoidCallback? onPressed;

  const ChangePhotoButton({super.key, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return AppButton(
      isFullWidth: false,
      height: 40,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      backgroundColor: Theme.of(
        context,
      ).colorScheme.secondary.withValues(alpha: 0.5),
      foregroundColor: Theme.of(context).colorScheme.onSurface,
      borderRadius: AppRadius.circular20,
      onPressed: onPressed,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.edit,
            color: Theme.of(context).colorScheme.onSurface,
            size: 18,
          ),
          const SizedBox(width: 8),
          Text(
            'Change Photo',
            style: GoogleFonts.plusJakartaSans(
              color: Theme.of(context).colorScheme.onSurface,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
