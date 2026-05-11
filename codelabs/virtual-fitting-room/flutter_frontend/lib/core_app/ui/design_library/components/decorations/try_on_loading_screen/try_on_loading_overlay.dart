import 'package:flutter/material.dart';
import 'dart:math' as math;
import 'package:google_fonts/google_fonts.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class TryOnLoadingOverlay extends StatefulWidget {
  const TryOnLoadingOverlay({super.key});

  @override
  State<TryOnLoadingOverlay> createState() => _TryOnLoadingOverlayState();
}

class _TryOnLoadingOverlayState extends State<TryOnLoadingOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  final List<String> _emojiAssets = [
    'assets/images/emoji_tshirt.png',
    'assets/images/emoji_dress.png',
    'assets/images/emoji_jacket.png',
    'assets/images/emoji_jeans.png',
    'assets/images/emoji_sneaker.png',
    'assets/images/emoji_cap.png',
  ];

  final List<String> _loadingMessages = [
    'Give us a sec.',
    'We think this will look great on you!',
    'Scanning your photo for the perfect fit...',
    'Analyzing fit and proportions...',
    'Digitally tailoring the garment to your picture...',
    'Rendering your virtual fitting room...',
    'Stitching the pixels together...',
    'Almost there...',
  ];

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      // Very long duration for slow, perfectly looping fluid movement
      duration: AppDurations.loadingOverlayLoop,
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: Container(
        color: Colors.black.withValues(
          alpha: 0.6,
        ), // Slightly darker for better contrast with badges
        child: Center(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              return Stack(
                clipBehavior: Clip.none,
                alignment: Alignment.center,
                children: [
                  // Floating image icons
                  for (int i = 0; i < _emojiAssets.length; i++)
                    Builder(
                      builder: (context) {
                        final double t = _controller.value * 2 * math.pi;

                        // Fluid, water-like complex paths using Lissajous curves
                        // Integer frequencies ensure a perfect, seamless loop
                        final int fX1 = (i % 3) + 1; // 1, 2, or 3
                        final int fX2 = ((i + 1) % 4) + 1; // 1 to 4
                        final int fY1 = ((i + 2) % 3) + 1; // 1, 2, or 3
                        final int fY2 = ((i + 3) % 4) + 1; // 1 to 4

                        // Unique phase offsets to spread them out
                        final double pX1 = i * (math.pi / 3);
                        final double pX2 = i * (math.pi / 5);
                        final double pY1 = i * (math.pi / 4);
                        final double pY2 = i * (math.pi / 7);

                        // Move across 80% of the screen width/height
                        final double rangeX =
                            MediaQuery.of(context).size.width * 0.4;
                        final double rangeY =
                            MediaQuery.of(context).size.height * 0.4;

                        // X and Y positions
                        final double x =
                            math.sin(t * fX1 + pX1) * (rangeX * 0.6) +
                            math.cos(t * fX2 + pX2) * (rangeX * 0.4);

                        final double y =
                            math.cos(t * fY1 + pY1) * (rangeY * 0.6) +
                            math.sin(t * fY2 + pY2) * (rangeY * 0.4);

                        // Add subtle scale and rotation
                        final double scale = 1.0 + 0.15 * math.sin(t * 5 + i);
                        final double rotation = 0.2 * math.sin(t * 3 + i * 2);

                        final Matrix4 transform =
                            Matrix4.translationValues(x, y, 0.0)
                              ..scaleByDouble(scale, scale, 1.0, 1.0)
                              ..rotateZ(rotation);

                        return Transform(
                          alignment: Alignment.center,
                          transform: transform,
                          child: Container(
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.5),
                                width: 2,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.3),
                                  blurRadius: 10,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                            ),
                            child: ClipOval(
                              child: Image.asset(
                                _emojiAssets[i],
                                width: 80,
                                height: 80,
                                fit: BoxFit.cover,
                              ),
                            ),
                          ),
                        );
                      },
                    ),

                  // Center Content
                  Column(
                    mainAxisAlignment: MainAxisAlignment.start,
                    children: [
                      LinearProgressIndicator(
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      const SizedBox(height: AppSizes.s24),
                      Builder(
                        builder: (context) {
                          final int totalSeconds =
                              AppDurations.loadingOverlayLoop.inSeconds;
                          final int cycleSeconds =
                              AppDurations.loadingOverlayMessageCycle.inSeconds;

                          // Change message on a timer cycle based on the loop duration
                          final int messageIndex =
                              ((_controller.value * totalSeconds) ~/
                                  cycleSeconds) %
                              _loadingMessages.length;
                          final String currentMessage =
                              _loadingMessages[messageIndex];

                          return AnimatedSwitcher(
                            duration: AppDurations.medium,
                            switchInCurve: Curves.easeIn,
                            switchOutCurve: Curves.easeOut,
                            transitionBuilder:
                                (Widget child, Animation<double> animation) {
                                  return FadeTransition(
                                    opacity: animation,
                                    child: SlideTransition(
                                      position: Tween<Offset>(
                                        begin: const Offset(0.0, 0.2),
                                        end: Offset.zero,
                                      ).animate(animation),
                                      child: child,
                                    ),
                                  );
                                },
                            child: Text(
                              currentMessage,
                              key: ValueKey<String>(currentMessage),
                              style: GoogleFonts.plusJakartaSans(
                                color: Theme.of(context).colorScheme.primary,
                                fontWeight: FontWeight.w600,
                                fontSize: 18,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
