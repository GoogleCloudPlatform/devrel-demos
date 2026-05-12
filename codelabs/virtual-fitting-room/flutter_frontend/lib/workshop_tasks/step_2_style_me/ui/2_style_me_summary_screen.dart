import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/app_bar/app_bar.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/scaffold_with_background_noise.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/app_loading_indicator.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/app_empty_state.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/app_error_banner.dart';
import 'package:fashion_app/core_app/ui/design_library/components/layout/screen_with_overlays.dart';
import 'package:fashion_app/core_app/ui/design_library/components/layout/outfit_carousel.dart';
import 'package:fashion_app/core_app/ui/design_library/components/inputs/feedback_chat_bar.dart';
import 'package:fashion_app/core_app/ui/design_library/components/bottom_sheets/styling_brief_bottom_sheet.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/providers/styling_provider.dart';

class StyleMeSummaryScreen extends StatelessWidget {
  const StyleMeSummaryScreen({super.key});

  // START_WORKSHOP_STEP 10
  void _handleFeedback(BuildContext context, String text) async {
    final provider = context.read<StylingProvider>();
    await provider.refineWithFeedback(text);
  }
  // END_WORKSHOP_STEP

  @override
  Widget build(BuildContext context) {
    return ScaffoldWithBackgroundNoise(
      resizeToAvoidBottomInset: false,
      appBar: ThreadCountAppBar(
        title: 'Your Styling Brief',
        showBackButton: true,
        //START_WORKSHOP_STEP 8
        actionIcon: Icons.info_outline,
        onActionPressed: () {
          _showStylingBriefDetails(context);
        },
        // END_WORKSHOP_STEP
      ),

      body: Consumer<StylingProvider>(
        builder: (context, provider, child) {
          return ScreenWithOverlays(
            // START_WORKSHOP_STEP 9
            body: AnimatedSwitcher(
              duration: AppDurations.medium,
              transitionBuilder: (child, animation) {
                return FadeTransition(
                  opacity: CurveTween(
                    curve: Curves.easeInOut,
                  ).animate(animation),
                  child: ScaleTransition(
                    scale: Tween<double>(begin: 0.95, end: 1.0).animate(
                      CurveTween(curve: Curves.easeOutBack).animate(animation),
                    ),
                    child: child,
                  ),
                );
              },
              child: provider.isLoading
                  ? const AppLoadingIndicator(
                      key: ValueKey('loading_indicator'),
                      message: 'Curating your looks...',
                    )
                  : provider.outfits.isEmpty
                  ? AppEmptyState(
                      key: const ValueKey('empty_state'),
                      message: 'No suggestions available.',
                    )
                  : OutfitCarousel(
                      key: const ValueKey('page_view'),
                      outfits: provider.outfits,
                    ),
            ),
            overlays: [
              if (provider.hasError && !provider.isLoading)
                AppErrorBanner(message: provider.errorMessage!),
              FeedbackChatBar(
                isLoading: provider.isLoading,
                onSubmitted: (text) => _handleFeedback(context, text),
              ),
            ],
          );
        },
      ),
      // END_WORKSHOP_STEP
    );
  }

  void _showStylingBriefDetails(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => StylingBriefBottomSheet(
        request: context.read<StylingProvider>().currentRequest!,
      ),
    );
  }
}
