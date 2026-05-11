import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/buttons/primary_button.dart';

class StyleMeButton extends StatelessWidget {
  final VoidCallback onPressed;

  const StyleMeButton({super.key, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return PrimaryButton(
      onPressed: onPressed,
      text: 'Style Me',
    );
  }
}
