import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

/// A reusable bottom sheet form layout that automatically handles keyboard insets,
/// safe area padding, and scrolling.
class AppBottomSheetForm extends StatelessWidget {
  final GlobalKey<FormState> formKey;
  final List<Widget> children;

  const AppBottomSheetForm({
    super.key,
    required this.formKey,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.viewInsetsOf(context).bottom;

    return Padding(
      padding: EdgeInsets.fromLTRB(
        AppSizes.s24,
        0,
        AppSizes.s24,
        AppSizes.s24 + bottomInset,
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          child: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: children,
            ),
          ),
        ),
      ),
    );
  }
}
