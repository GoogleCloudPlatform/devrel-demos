import 'package:flutter/material.dart';

class ProductDetailAppBar extends StatelessWidget {
  final Widget background;

  const ProductDetailAppBar({super.key, required this.background});

  @override
  Widget build(BuildContext context) {
    return SliverAppBar(
      expandedHeight: 480,
      pinned: true,
      backgroundColor: Theme.of(
        context,
      ).scaffoldBackgroundColor.withValues(alpha: 0.9),
      leading: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.only(left: 16, top: 8),
          child: CircleAvatar(
            backgroundColor: Theme.of(
              context,
            ).scaffoldBackgroundColor.withValues(alpha: 0.8),
            child: IconButton(
              icon: Icon(
                Icons.arrow_back,
                color: Theme.of(context).colorScheme.onSurface,
              ),
              onPressed: () => Navigator.pop(context),
            ),
          ),
        ),
      ),
      flexibleSpace: FlexibleSpaceBar(background: background),
    );
  }
}
