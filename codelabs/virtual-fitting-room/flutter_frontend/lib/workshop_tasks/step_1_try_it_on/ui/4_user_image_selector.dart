import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/providers/try_it_on_provider.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/try_on_ui_context.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/primary_icon_button.dart';
import 'package:fashion_app/core_app/ui/design_library/components/animations/animated_pulse_icon.dart';

/// The initial state screen prompting the user to upload a photo of themselves.
///
/// This screen renders the select image UI and a primary action button.
/// When tapped, it calls `provider.processTryOn`, taking the
/// user's selected product and chosen image to start the
/// AI image generation process.
class ChooseImageScreen extends StatelessWidget {
  const ChooseImageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: AppPadding.all24,
            decoration: BoxDecoration(
              color: Theme.of(
                context,
              ).colorScheme.primary.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: AnimatedPulseIcon(
              icon: Icons.add_a_photo_outlined,
              size: AppSizes.iconExtraLarge,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(height: AppSizes.s24),
          Text(
            'See it on you',
            style: AppTextStyles.headlineLarge.copyWith(
              color: Theme.of(context).colorScheme.onSurface,
            ),
          ),
          const SizedBox(height: AppSizes.s12),
          Padding(
            padding: AppPadding.horizontal48,
            child: Text(
              'Upload a photo from your gallery to see how this item looks on you.',
              textAlign: TextAlign.center,
              style: AppTextStyles.bodyLarge.copyWith(
                color: Theme.of(context).colorScheme.tertiary,
              ),
            ),
          ),
          const SizedBox(height: AppSizes.s48),
          // START_WORKSHOP_STEP 3
          // The primary action that calls the Provider to start the backend AI Try-On request using the selected product.
          PrimaryIconButton(
            onPressed: () async {
              final provider = context.read<TryItOnProvider>();
              final error = await provider.processTryOn(
                provider.products[provider.selectedProductIndex].productImage,
                pickNewImage: true,
              );
              if (context.mounted) {
                context.showTryOnResult(provider, error);
              }
            },
            icon: const Icon(Icons.photo_library),
            label: 'Upload from Gallery',
          ),
          // END_WORKSHOP_STEP
        ],
      ),
    );
  }
}
