import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/screens/home/home_screen.dart';
import 'package:fashion_app/core_app/ui/screens/cart/shopping_cart_screen.dart';
import 'package:fashion_app/core_app/ui/screens/profile/profile_screen.dart';

import 'package:fashion_app/core_app/ui/design_library/components/app_bar/app_bar.dart';
import 'package:fashion_app/core_app/ui/design_library/components/nav_bar/branded_nav_bar.dart';
import 'package:fashion_app/core_app/ui/screens/categories/categories_screen.dart';

class _NestedNavObserver extends NavigatorObserver {
  final VoidCallback onRouteChanged;
  _NestedNavObserver({required this.onRouteChanged});

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) =>
      onRouteChanged();
  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) =>
      onRouteChanged();
  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) =>
      onRouteChanged();
  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) =>
      onRouteChanged();
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;
  int _previousIndex = 0;
  bool _isVisible = true;

  late final GlobalKey<NavigatorState> _homeNavigatorKey =
      GlobalKey<NavigatorState>();

  late final _NestedNavObserver _navObserver = _NestedNavObserver(
    onRouteChanged: () {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() {});
      });
    },
  );

  late final List<Widget> _screens = [
    Navigator(
      key: _homeNavigatorKey,
      observers: [HeroController(), _navObserver],
      onGenerateRoute: (settings) {
        return MaterialPageRoute(
          builder: (context) => const HomeScreen(key: ValueKey('HomeScreen')),
        );
      },
    ),
    const CategoriesScreen(key: ValueKey('CategoriesScreen')),
    const ShoppingCartScreen(key: ValueKey('ShoppingCartScreen')),
    const ProfileScreen(key: ValueKey('ProfileScreen')),
  ];

  @override
  Widget build(BuildContext context) {
    bool canPop =
        _selectedIndex == 0 && _homeNavigatorKey.currentState?.canPop() == true;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        if (_selectedIndex == 0 &&
            _homeNavigatorKey.currentState?.canPop() == true) {
          _homeNavigatorKey.currentState?.pop();
        } else {
          // Additional logic for app exit could go here
        }
      },
      child: Scaffold(
        appBar: ThreadCountAppBar(
          showSearchBar: true,
          showBackButton: canPop,
          onBackButtonPressed: () {
            if (_selectedIndex == 0) {
              _homeNavigatorKey.currentState?.pop();
            }
          },
        ),
        body: NotificationListener<ScrollNotification>(
          onNotification: (ScrollNotification notification) {
            if (notification is ScrollUpdateNotification) {
              if (notification.metrics.pixels <= 0) {
                if (!_isVisible) {
                  setState(() {
                    _isVisible = true;
                  });
                }
              } else if (notification.scrollDelta! > 0 && _isVisible) {
                setState(() {
                  _isVisible = false;
                });
              } else if (notification.scrollDelta! < 0 && !_isVisible) {
                setState(() {
                  _isVisible = true;
                });
              }
            }
            return true;
          },
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 300),
            transitionBuilder: (Widget child, Animation<double> animation) {
              final isIncoming = child.key == _screens[_selectedIndex].key;
              final isMovingRight = _selectedIndex > _previousIndex;
              final isMovingLeft = _selectedIndex < _previousIndex;

              Offset beginOffset;
              if (isMovingRight) {
                // Moving right: incoming slides from right, outgoing slides to left
                beginOffset = isIncoming
                    ? const Offset(1.0, 0.0)
                    : const Offset(-1.0, 0.0);
              } else if (isMovingLeft) {
                // Moving left: incoming slides from left, outgoing slides to right
                beginOffset = isIncoming
                    ? const Offset(-1.0, 0.0)
                    : const Offset(1.0, 0.0);
              } else {
                // Initial load or unexpected case
                beginOffset = const Offset(0.0, 0.0);
              }

              return SlideTransition(
                position: Tween<Offset>(begin: beginOffset, end: Offset.zero)
                    .animate(
                      CurvedAnimation(
                        parent: animation,
                        curve: Curves.easeInOutCubic,
                      ),
                    ),
                child: child,
              );
            },
            child: _screens[_selectedIndex],
          ),
        ),
        extendBody: true,
        bottomNavigationBar: AnimatedSlide(
          duration: const Duration(milliseconds: 300),
          offset: _isVisible ? Offset.zero : const Offset(0, 1),
          child: BottomNav(
            selectedIndex: _selectedIndex,
            onItemSelected: (index) {
              if (_selectedIndex != index) {
                setState(() {
                  _previousIndex = _selectedIndex;
                  _selectedIndex = index;
                });
              }
            },
          ),
        ),
      ),
    );
  }
}
