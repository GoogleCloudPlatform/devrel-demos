import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class AppTextField extends StatelessWidget {
  final TextEditingController? controller;
  final String? hintText;
  final Widget? prefixIcon;
  final int maxLines;
  final String? Function(String?)? validator;
  final ValueChanged<String>? onSubmitted;
  final TextInputAction? textInputAction;
  final bool enabled;
  final bool isDense;
  final BorderRadius borderRadius;
  final bool autofocus;

  const AppTextField({
    super.key,
    this.controller,
    this.hintText,
    this.prefixIcon,
    this.maxLines = 1,
    this.validator,
    this.onSubmitted,
    this.textInputAction,
    this.enabled = true,
    this.isDense = false,
    this.borderRadius = AppRadius.circular12,
    this.autofocus = false,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      enabled: enabled,
      maxLines: maxLines,
      textInputAction: textInputAction,
      onFieldSubmitted: onSubmitted,
      autofocus: autofocus,
      style: AppTextStyles.textFieldText.copyWith(
        color: Theme.of(context).colorScheme.onSurface,
      ),
      validator: validator,
      decoration: InputDecoration(
        isDense: isDense,
        hintText: hintText,
        hintStyle: AppTextStyles.textFieldHint.copyWith(
          color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.3),
          fontSize: isDense ? 14 : null,
        ),
        prefixIcon: prefixIcon,
        filled: true,
        fillColor: Theme.of(
          context,
        ).colorScheme.onSurface.withValues(alpha: 0.05),
        border: OutlineInputBorder(
          borderRadius: borderRadius,
          borderSide: BorderSide.none,
        ),
        contentPadding: AppPadding.all16,
      ),
    );
  }
}
