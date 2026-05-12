import 'package:flutter/material.dart';

/// A reusable layout component that wraps the main [body] in a [SafeArea] and
/// [Padding], while rendering absolute-positioned [overlays] over it inside a [Stack].
class ScreenWithOverlays extends StatelessWidget {
  /// The main content of the screen.
  final Widget body;

  /// Absolute-positioned widgets that float over the main content 
  /// (e.g., error messages, fixed-bottom chat bars).
  final List<Widget> overlays;

  /// Padding to apply to the main [body]. Defaults to `EdgeInsets.fromLTRB(24, 24, 24, 100)`.
  final EdgeInsetsGeometry bodyPadding;

  const ScreenWithOverlays({
    super.key,
    required this.body,
    this.overlays = const <Widget>[],
    this.bodyPadding = const EdgeInsets.fromLTRB(24, 24, 24, 100),
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        SafeArea(
          bottom: true,
          child: Padding(
            padding: bodyPadding,
            child: body,
          ),
        ),
        ...overlays,
      ],
    );
  }
}
