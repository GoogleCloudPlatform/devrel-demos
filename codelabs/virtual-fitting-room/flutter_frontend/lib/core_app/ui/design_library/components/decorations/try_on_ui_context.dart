import 'package:flutter/material.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/providers/try_it_on_provider.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

extension TryOnUIContext on BuildContext {
  void showTryOnResult(TryItOnProvider provider, String? error) {
    if (!mounted) return;
    if (error == 'IMAGE_PICK_CANCELLED') return;

    ScaffoldMessenger.of(this).hideCurrentSnackBar();

    if (error == null) {
      if (!provider.wasLastGenerationCached) {
        ScaffoldMessenger.of(this).showSnackBar(
          const SnackBar(content: Text('Look generated successfully!')),
        );
      }
    } else {
      ScaffoldMessenger.of(this).showSnackBar(
        SnackBar(content: Text(error), duration: AppDurations.slow),
      );
    }
  }
}
