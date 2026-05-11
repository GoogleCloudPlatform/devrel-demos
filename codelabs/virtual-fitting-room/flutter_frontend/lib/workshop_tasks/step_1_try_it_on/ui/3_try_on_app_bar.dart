import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/providers/try_it_on_provider.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/change_photo_button.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/try_on_ui_context.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/app_back_button.dart';
import 'package:fashion_app/core_app/ui/design_library/components/app_bar/custom_app_bar_wrapper.dart';

/// A custom app bar used throughout the Virtual Try-On flow.
///
/// It provides a consistent back button and dynamically renders the
/// "Change Photo" button. The "Change Photo" button is only visible when
/// the user has an active photo and handles the logic to
/// restart the AI image generation process when the user selects a new image.
class TryOnAppBar extends StatelessWidget implements PreferredSizeWidget {
  const TryOnAppBar({super.key});

  @override
  Size get preferredSize => CustomAppBarWrapper.standardSize;

  @override
  Widget build(BuildContext context) {
    return Consumer<TryItOnProvider>(
      builder: (context, provider, child) {
        return CustomAppBarWrapper(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              AppBackButton(),
              // START_WORKSHOP_CALLOUT 1.5
              // Only displays the "Change Photo" action if safety conditions are met, and restarts the AI generation pipeline if tapped.
              if (provider.userImageBytes != null &&
                  provider.state == TryOnState.success)
                ChangePhotoButton(
                  onPressed: () async {
                    final provider = context.read<TryItOnProvider>();
                    final picked = await provider.pickImage();
                    if (picked && context.mounted) {
                      final productPath = provider
                          .products[provider.selectedProductIndex]
                          .productImage;
                      final error = await provider.processTryOn(productPath);
                      if (context.mounted) {
                        context.showTryOnResult(provider, error);
                      }
                    }
                  },
                ),
              // END_WORKSHOP_CALLOUT
            ],
          ),
        );
      },
    );
  }
}
