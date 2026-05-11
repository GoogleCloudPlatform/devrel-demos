import 'package:fashion_app/core_app/ui/design_library/components/decorations/try_on_loading_screen/loading_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/providers/try_it_on_provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/ui/4_user_image_selector.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/ui/3_try_on_app_bar.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/ui/5_fitting_room.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/scaffold_with_background_noise.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

/// The root navigation wrapper for the Virtual Try-On experience.
///
/// This screen acts as a state router. It listens to the
/// [TryItOnProvider.state] and switches its `body` to display
/// either the image picker, the loading state, or the final fitting room
/// result.
class TryItOnScreen extends StatelessWidget {
  const TryItOnScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final tryOnProvider = context.watch<TryItOnProvider>();

    return ScaffoldWithBackgroundNoise(
      appBar: const TryOnAppBar(),
      body:
          // START_WORKSHOP_STEP 2
          // State Router: Uses pattern matching to display the correct screen based on the AI image generation status.
          AnimatedSwitcher(
            duration: AppDurations.medium,
            child: switch (tryOnProvider.state) {
              TryOnState.initial || TryOnState.error => const ChooseImageScreen(),
              TryOnState.imagePicked || TryOnState.generating => LoadingScreen(
                userImage: tryOnProvider.userImageBytes,
              ),
              TryOnState.success => const FittingRoomScreen(),
            },
          ),
      // END_WORKSHOP_STEP 2
    );
  }
}
