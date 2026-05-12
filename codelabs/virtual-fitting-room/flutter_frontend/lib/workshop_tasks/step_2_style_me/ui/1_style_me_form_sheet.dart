import 'package:flutter/material.dart';

import 'package:provider/provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/providers/try_it_on_provider.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/primary_button.dart';
import 'package:fashion_app/core_app/ui/design_library/components/inputs/app_form_field.dart';
import 'package:fashion_app/core_app/ui/design_library/components/bottom_sheets/app_bottom_sheet_form.dart';

import 'package:fashion_app/workshop_tasks/step_2_style_me/models/style_request.dart';

class StyleMeFormSheet extends StatefulWidget {
  const StyleMeFormSheet({super.key});

  @override
  State<StyleMeFormSheet> createState() => _StyleMeFormSheetState();
}

class _StyleMeFormSheetState extends State<StyleMeFormSheet> {
  final _formKey = GlobalKey<FormState>();
  final _locationController = TextEditingController();
  final _occasionController = TextEditingController();
  final _notesController = TextEditingController();

  bool _isSubmitting = false;

  @override
  void dispose() {
    _locationController.dispose();
    _occasionController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  // START_WORKSHOP_CALLOUT 7
  String? _validateContext(String? value) {
    if (_locationController.text.trim().isEmpty &&
        _occasionController.text.trim().isEmpty) {
      return 'Please provide either a location or occasion';
    }
    return null;
  }

  Future<void> _submitRequest() async {
    if (_formKey.currentState!.validate()) {
      setState(() {
        _isSubmitting = true;
      });
      final provider = context.read<TryItOnProvider>();
      if (mounted) {
        Navigator.pop(
          context,
          StyleRequest(
            location: _locationController.text.trim(),
            occasion: _occasionController.text.trim(),
            notes: _notesController.text.trim(),
            // Prefer the GCS URL (fitting result) over raw bytes so the
            // stylist agent reuses the same rendered person.
            gcsUserImageUrl: provider.fittingGcsUrl,
            userImageData: provider.fittingGcsUrl == null
                ? provider.userImageBytes
                : null,
            selectedProductId: provider.selectedProduct?.id,
            selectedProductTitle: provider.selectedProduct?.title,
          ),
        );
      }
    }
    // END_WORKSHOP_CALLOUT
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => FocusManager.instance.primaryFocus?.unfocus(),
      behavior: HitTestBehavior.opaque,
      child: AppBottomSheetForm(
        formKey: _formKey,
      children: [
        Text(
          'Style Me',
          style: AppTextStyles.headlineLarge.copyWith(
            color: Theme.of(context).colorScheme.onSurface,
          ),
        ),
        const SizedBox(height: AppSizes.s8),
        Text(
          'Tell us what you\'re styling for and we\'ll curate options.',
          style: AppTextStyles.textFieldHint.copyWith(
            color: Theme.of(
              context,
            ).colorScheme.onSurface.withValues(alpha: 0.6),
          ),
        ),
        const SizedBox(height: AppSizes.s24),
        // START_WORKSHOP_STEP 6
        AppFormField(
          label: 'Location',
          hint: 'e.g., Paris, Beach Resort, Office',
          controller: _locationController,
          icon: Icons.location_on_outlined,
          validator: _validateContext,
          autofocus: true,
        ),
        const SizedBox(height: AppSizes.s16),
        AppFormField(
          label: 'Occasion',
          hint: 'e.g., Summer Vacation, Wedding, Casual',
          controller: _occasionController,
          icon: Icons.event_outlined,
          validator: _validateContext,
        ),
        const SizedBox(height: AppSizes.s16),
        AppFormField(
          label: 'Additional Notes',
          hint: 'Any specific styles or preferences?',
          controller: _notesController,
          icon: Icons.notes_outlined,
          maxLines: 3,
        ),
        const SizedBox(height: AppSizes.s32),
        PrimaryButton(
          onPressed: _isSubmitting ? null : _submitRequest,
          text: 'Submit Request',
        ),
        // END_WORKSHOP_STEP
      ],
      ),
    );
  }
}
