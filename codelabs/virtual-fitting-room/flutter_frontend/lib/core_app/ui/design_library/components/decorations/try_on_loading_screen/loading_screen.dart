import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/decorations/try_on_loading_screen/try_on_loading_overlay.dart';

class LoadingScreen extends StatefulWidget {
  const LoadingScreen({required this.userImage, super.key});

  final Uint8List? userImage;

  @override
  State<LoadingScreen> createState() => _LoadingScreenState();
}

class _LoadingScreenState extends State<LoadingScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final userImage = widget.userImage;

    return Stack(
      children: [
        Center(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              // More noticeable breathing scale (1.0 to 1.08)
              final scale = 1.0 + (_controller.value * 0.08);
              // Gentle floating up and down (-5 to +5 pixels)
              final translateY = (_controller.value - 0.5) * 10.0;

              return Transform(
                alignment: Alignment.center,
                transform: Matrix4.translationValues(0.0, translateY, 0.0)
                  ..scaleByDouble(scale, scale, 1.0, 1.0),
                child: child,
              );
            },
            child: userImage != null
                ? Image.memory(userImage, width: 300, fit: BoxFit.contain)
                : const SizedBox(width: 300),
          ),
        ),
        const TryOnLoadingOverlay(),
      ],
    );
  }
}
