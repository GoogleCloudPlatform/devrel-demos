import 'package:flutter/material.dart';

class NoiseBackground extends StatelessWidget {
  const NoiseBackground({super.key});

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: Opacity(
        opacity: 0.1,
        child: Image.asset(
          'assets/images/noise.png',
          repeat: ImageRepeat.repeat,
        ),
      ),
    );
  }
}
