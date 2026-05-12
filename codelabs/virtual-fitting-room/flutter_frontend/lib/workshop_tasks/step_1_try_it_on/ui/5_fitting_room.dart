import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/providers/try_it_on_provider.dart';
import 'package:fashion_app/core_app/ui/design_library/components/nav_bar/try_on_bottom_controls.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/add_to_bag_button.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/app_outlined_button.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/ui/1_style_me_form_sheet.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/style_request.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/ui/2_style_me_summary_screen.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/providers/styling_provider.dart';

/// The final state screen displaying the AI-generated Try-On image.
///
/// This screen contains:
/// * The `provider.generatedImage` displaying the result.
/// * The `ProductSelectorList` carousel to swap items.
/// * The "Style Me" button, navigating to the subsequent styling step.
class FittingRoomScreen extends StatelessWidget {
  const FittingRoomScreen({super.key});

  void _showStyleMeForm(BuildContext context) async {
    // START_WORKSHOP_CALLOUT 7
    // Shows a modal for the user's styling request, then routes to the "Style Me" flow.
    final result = await showModalBottomSheet<StyleRequest>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      showDragHandle: true,
      useSafeArea: true,
      builder: (context) => const StyleMeFormSheet(),
    );

    if (result != null && context.mounted) {
      context.read<StylingProvider>().getStyleSuggestions(result);
      // Navigate to the summary screen with info from StyleMeForm
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => const StyleMeSummaryScreen()),
      );
    }
    // END_WORKSHOP_CALLOUT
  }

  @override
  Widget build(BuildContext context) {
    // START_WORKSHOP_STEP 4
    // Subscribes to the Provider to fetch and display the generated Try-On image.
    final provider = context.watch<TryItOnProvider>();
    final generatedImage = provider.generatedImage;

    return Column(
      children: [
        Expanded(child: Image.memory(generatedImage!, fit: BoxFit.fitHeight)),
        // END_WORKSHOP_STEP 4
        TryOnBottomControls(
          children: [
            // START_WORKSHOP_STEP BONUS
            // Renders a horizontal product selector that lets the user swap items, triggering a new generation request.
            /*ProductSelectorList(
              products: provider.products,
              selectedProductIndex: provider.selectedProductIndex,
              onProductSelected: (index) async {
                if (provider.state != TryOnState.generating) {
                  provider.setSelectedProductIndex(index);
                  final error = await provider.processTryOn(
                    provider.products[index].productImage,
                  );
                  if (context.mounted) {
                    context.showTryOnResult(provider, error);
                  }
                }
              },
            ),
            const SizedBox(height: AppSizes.s2),
            */
            // END_WORKSHOP_STEP BONUS
            Row(
              children: [
                // START_WORKSHOP_STEP 5
                // Connects the current screen to the "Style Me" form, allowing the user to request AI styling advice.
                AppOutlinedButton(
                  onPressed: () => _showStyleMeForm(context),
                  icon: const Icon(Icons.auto_awesome, color: Colors.amber),
                  label: 'Style Me',
                  isExpanded: true,
                ),
                const SizedBox(width: AppSizes.s16),
                // END_WORKSHOP_STEP
                AddToBagButton(
                  product: provider.products[provider.selectedProductIndex],
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}
