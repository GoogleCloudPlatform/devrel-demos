import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/nav_bar/bottom_bar.dart';
import 'package:provider/provider.dart';
import 'package:fashion_app/core_app/providers/cart_provider.dart';
import 'package:fashion_app/core_app/ui/design_library/components/nav_bar/branded_nav_item.dart';

class _NavItemData {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final bool isCart;

  const _NavItemData({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    this.isCart = false,
  });
}

class BottomNav extends StatelessWidget {
  static const double _baseHeight = 60.0;
  static const double _indicatorWidth = 64.0;
  static const double _indicatorHeight = 3.0;

  static const double _maxTabletWidth = 600.0;
  static const List<_NavItemData> _navItems = [
    _NavItemData(
      icon: Icons.home_outlined,
      selectedIcon: Icons.home_filled,
      label: 'Home',
    ),
    _NavItemData(
      icon: Icons.grid_view_outlined,
      selectedIcon: Icons.grid_view,
      label: 'Categories',
    ),
    _NavItemData(
      icon: Icons.shopping_bag_outlined,
      selectedIcon: Icons.shopping_bag,
      label: 'Bag',
      isCart: true,
    ),
    _NavItemData(
      icon: Icons.person_outline,
      selectedIcon: Icons.person,
      label: 'Profile',
    ),
  ];

  final int selectedIndex;
  final Function(int) onItemSelected;

  const BottomNav({
    super.key,
    required this.selectedIndex,
    required this.onItemSelected,
  });

  @override
  Widget build(BuildContext context) {
    return BottomBar(
      height: _baseHeight,
      padding: EdgeInsets.zero,
      maxWidth: _maxTabletWidth,
      child: LayoutBuilder(
        builder: (context, constraints) {
          return Stack(
            children: [
              AnimatedPositioned(
                duration: AppDurations.fast,
                curve: Curves.easeInOut,
                top: 0,
                left:
                    (constraints.maxWidth / _navItems.length * selectedIndex) +
                    ((constraints.maxWidth / _navItems.length -
                            _indicatorWidth) /
                        2),
                child: Container(
                  width: _indicatorWidth,
                  height: _indicatorHeight,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  for (int i = 0; i < _navItems.length; i++)
                    if (_navItems[i].isCart)
                      Consumer<CartProvider>(
                        builder: (context, cart, _) => BottomNavItem(
                          icon: _navItems[i].icon,
                          selectedIcon: _navItems[i].selectedIcon,
                          label: _navItems[i].label,
                          isSelected: selectedIndex == i,
                          onTap: () => onItemSelected(i),
                          badgeCount: cart.totalItemCount,
                        ),
                      )
                    else
                      BottomNavItem(
                        icon: _navItems[i].icon,
                        selectedIcon: _navItems[i].selectedIcon,
                        label: _navItems[i].label,
                        isSelected: selectedIndex == i,
                        onTap: () => onItemSelected(i),
                      ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}
