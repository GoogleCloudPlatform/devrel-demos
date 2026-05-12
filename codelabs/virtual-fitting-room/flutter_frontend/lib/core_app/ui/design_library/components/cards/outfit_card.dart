import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/outfit.dart';
import 'package:fashion_app/core_app/ui/design_library/components/cards/app_card.dart';
import 'package:fashion_app/core_app/ui/design_library/components/layout/outfit_product_list.dart';

class OutfitCard extends StatefulWidget {
  final Outfit outfit;

  const OutfitCard({super.key, required this.outfit});

  @override
  State<OutfitCard> createState() => _OutfitCardState();
}

class _OutfitCardState extends State<OutfitCard> {
  bool _isExpanded = false;

  void _toggleExpanded() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
  }

  @override
  Widget build(BuildContext context) {
    final outfit = widget.outfit;
    return LayoutBuilder(
      builder: (context, constraints) {
        return AppCard(
          borderRadius: AppRadius.circular24,
          clipBehavior: Clip.antiAlias,
          shadows: [
            BoxShadow(
              color: Theme.of(
                context,
              ).colorScheme.onSurface.withValues(alpha: 0.08),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
          child: SingleChildScrollView(
            child: SizedBox(
              height: constraints.maxHeight * 2,
              child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                flex: 3,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    GestureDetector(
                      behavior: HitTestBehavior.translucent,
                      onTap: () {
                        if (_isExpanded) {
                          _toggleExpanded();
                        }
                      },
                      child: SizedBox.expand(
                        child: outfit.imageData != null
                            ? Image.memory(
                                outfit.imageData!,
                                fit: BoxFit.cover,
                                cacheWidth: 800,
                                gaplessPlayback: true,
                              )
                            : Image.asset(
                                outfit.imagePath,
                                fit: BoxFit.cover,
                                cacheWidth: 800,
                                gaplessPlayback: true,
                              ),
                      ),
                    ),
                    if (constraints.maxWidth > 150)
                      Positioned(
                        bottom: 16,
                        right: 16,
                        child: ConstrainedBox(
                          constraints: BoxConstraints(
                            maxWidth: constraints.maxWidth > 32
                                ? constraints.maxWidth - 32
                                : 0,
                          ),
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: _toggleExpanded,
                              borderRadius: _isExpanded
                                  ? AppRadius.circular32
                                  : AppRadius.circular20,
                              child: AnimatedContainer(
                                duration: AppDurations.fast,
                                curve: Curves.easeInOut,
                                padding: EdgeInsets.symmetric(
                                  horizontal: _isExpanded
                                      ? AppSizes.s8
                                      : AppSizes.s12,
                                  vertical: _isExpanded
                                      ? AppSizes.s8
                                      : AppSizes.s6,
                                ),
                                decoration: BoxDecoration(
                                  color: Colors.black.withValues(alpha: 0.7),
                                  borderRadius: AppRadius.circular20,
                                  border: Border.all(
                                    color: Colors.white.withValues(alpha: 0.2),
                                  ),
                                ),
                                child: AnimatedCrossFade(
                                  duration: AppDurations.fast,
                                  alignment: Alignment.bottomRight,
                                  sizeCurve: Curves.easeInOut,
                                  firstCurve: Curves.easeOutCubic,
                                  secondCurve: Curves.easeInCubic,
                                  crossFadeState: _isExpanded
                                      ? CrossFadeState.showSecond
                                      : CrossFadeState.showFirst,
                                  firstChild: RepaintBoundary(
                                    key: const ValueKey('collapsed_badge'),
                                    child: OutfitCollapsedBadge(outfit: outfit),
                                  ),
                                  secondChild: SizedBox(
                                    width: constraints.maxWidth > 48 ? constraints.maxWidth - 48 : null,
                                    child: RepaintBoundary(
                                      key: const ValueKey('expanded_list'),
                                      child: OutfitProductList(outfit: outfit),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              Expanded(
                flex: 1,
                child: Container(
                  padding: AppPadding.all16,
                  color: Colors.white,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.auto_awesome,
                            size: 16,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                          const SizedBox(width: AppSizes.s8),
                          Expanded(
                            child: Text(
                              'Styling Notes',
                              style: Theme.of(context).textTheme.titleSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.bold,
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.primary,
                                  ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSizes.s8),
                      Expanded(
                        child: Text(
                          outfit.commentary,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(
                                color: Colors.black.withValues(alpha: 0.8),
                                height: 1.5,
                              ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
            ),
          ),
        );
      },
    );
  }
}

class OutfitCollapsedBadge extends StatelessWidget {
  final Outfit outfit;

  const OutfitCollapsedBadge({super.key, required this.outfit});

  @override
  Widget build(BuildContext context) {
    return Text(
      '${outfit.products.length} products',
      style: Theme.of(context).textTheme.bodySmall?.copyWith(
        color: Colors.white,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}
