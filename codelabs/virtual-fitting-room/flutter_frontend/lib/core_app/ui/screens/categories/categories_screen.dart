import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class CategoriesScreen extends StatelessWidget {
  const CategoriesScreen({super.key});

  final List<Map<String, dynamic>> _categories = const [
    {'title': 'Dresses', 'icon': Icons.dry_cleaning_outlined},
    {'title': 'Tops', 'icon': Icons.checkroom_outlined},
    {'title': 'Bottoms', 'icon': Icons.pan_tool_alt_outlined},
    {'title': 'Outerwear', 'icon': Icons.ac_unit_outlined},
    {'title': 'Shoes', 'icon': Icons.directions_walk_outlined},
    {'title': 'Accessories', 'icon': Icons.watch_outlined},
    {'title': 'Bags', 'icon': Icons.shopping_bag_outlined},
    {'title': 'Sleepwear', 'icon': Icons.bed_outlined},
    {'title': 'Swimwear', 'icon': Icons.pool_outlined},
    {'title': 'Activewear', 'icon': Icons.fitness_center_outlined},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      body: Stack(
        children: [
          // Background Noise Texture
          Positioned.fill(
            child: Opacity(
              opacity: 0.1,
              child: Image.asset(
                'assets/images/noise.png',
                repeat: ImageRepeat.repeat,
              ),
            ),
          ),
          ListView.separated(
            padding: const EdgeInsets.only(
              top: 16,
              bottom: 150, // Padding for bottom nav bar
            ),
            itemCount: _categories.length,
            separatorBuilder: (context, index) => Divider(
              color: Theme.of(
                context,
              ).colorScheme.onSurface.withValues(alpha: 0.1),
              height: 1,
              indent: 24,
              endIndent: 24,
            ),
            itemBuilder: (context, index) {
              final category = _categories[index];
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 8,
                ),
                leading: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(
                      context,
                    ).colorScheme.onSurface.withValues(alpha: 0.05),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    category['icon'] as IconData,
                    color: Theme.of(context).colorScheme.onSurface,
                  ),
                ),
                title: Text(
                  category['title'] as String,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Theme.of(context).colorScheme.onSurface,
                  ),
                ),
                trailing: Icon(
                  Icons.chevron_right,
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withValues(alpha: 0.5),
                ),
                onTap: () {
                  // TODO: Navigate to specific category listing
                },
              );
            },
          ),
        ],
      ),
    );
  }
}
