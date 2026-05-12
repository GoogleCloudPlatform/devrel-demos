import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/noise_background.dart';

class ScaffoldWithBackgroundNoise extends StatelessWidget {
  final Widget body;
  final Widget? bottomNavigationBar;
  final PreferredSizeWidget? appBar;
  final bool? resizeToAvoidBottomInset;

  const ScaffoldWithBackgroundNoise({
    super.key,
    required this.body,
    this.bottomNavigationBar,
    this.appBar,
    this.resizeToAvoidBottomInset,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      resizeToAvoidBottomInset: resizeToAvoidBottomInset,
      appBar: appBar,
      body: Stack(
        children: [
          const NoiseBackground(),
          body,
        ],
      ),
      bottomNavigationBar: bottomNavigationBar,
    );
  }
}
