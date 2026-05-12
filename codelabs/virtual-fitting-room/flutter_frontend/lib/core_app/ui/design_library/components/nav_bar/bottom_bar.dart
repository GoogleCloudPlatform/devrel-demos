import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class BottomBar extends StatelessWidget {
  final Widget child;
  final double? height;
  final EdgeInsetsGeometry padding;
  final bool handleSafeArea;
  final double? maxWidth;

  const BottomBar({
    super.key,
    required this.child,
    this.height,
    this.padding = AppPadding.all16,
    this.handleSafeArea = true,
    this.maxWidth,
  });

  @override
  Widget build(BuildContext context) {
    final bottomInset = handleSafeArea
        ? MediaQuery.paddingOf(context).bottom
        : 0.0;

    EdgeInsets resolvedPadding = padding.resolve(Directionality.of(context));
    if (handleSafeArea) {
      resolvedPadding = resolvedPadding.copyWith(
        bottom: resolvedPadding.bottom + bottomInset,
      );
    }

    final resolvedHeight = height != null ? height! + bottomInset : null;

    Widget content = child;
    if (maxWidth != null) {
      content = Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth!),
          child: content,
        ),
      );
    }

    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          height: resolvedHeight,
          padding: resolvedPadding,
          decoration: BoxDecoration(
            color: Theme.of(
              context,
            ).scaffoldBackgroundColor.withValues(alpha: 0.8),
            border: Border(
              top: BorderSide(
                color: Theme.of(
                  context,
                ).colorScheme.onSurface.withValues(alpha: 0.1),
              ),
            ),
          ),
          child: content,
        ),
      ),
    );
  }
}
