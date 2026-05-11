import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/inputs/app_text_field.dart';

class AppFormField extends StatelessWidget {
  final String label;
  final String hint;
  final TextEditingController controller;
  final IconData icon;
  final int maxLines;
  final String? Function(String?)? validator;
  final bool autofocus;

  const AppFormField({
    super.key,
    required this.label,
    required this.hint,
    required this.controller,
    required this.icon,
    this.maxLines = 1,
    this.validator,
    this.autofocus = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: AppTextStyles.productPrice.copyWith(
            color: Theme.of(context).colorScheme.onSurface,
          ),
        ),
        const SizedBox(height: AppSizes.s8),
        AnimatedSize(
          duration: AppDurations.fast,
          curve: Curves.easeInOut,
          child: AppTextField(
          controller: controller,
          maxLines: maxLines,
          validator: validator,
          hintText: hint,
          prefixIcon: maxLines == 1
              ? Icon(
                  icon,
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withValues(alpha: 0.5),
                )
              : null,
          autofocus: autofocus,
        ),
        ),
      ],
    );
  }
}
