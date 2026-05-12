import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/components/inputs/app_text_field.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class ThreadCountAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String? title;
  final VoidCallback? onSearchPressed;
  final VoidCallback? onActionPressed;
  final VoidCallback? onBackButtonPressed;
  final bool showBackButton;
  final bool showSearchBar;
  final IconData? actionIcon;

  const ThreadCountAppBar({
    super.key,
    this.title,
    this.onSearchPressed,
    this.onActionPressed,
    this.onBackButtonPressed,
    this.showBackButton = false,
    this.showSearchBar = false,
    this.actionIcon,
  });

  @override
  Widget build(BuildContext context) {
    return AppBar(
      toolbarHeight: showSearchBar ? 72.0 : kToolbarHeight,
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      elevation: 0,
      centerTitle: true,
      leading: showBackButton
          ? AppBarBackButton(onPressed: onBackButtonPressed)
          : (showSearchBar
                ? null
                : AppBarSearchButton(onPressed: onSearchPressed)),
      title: showSearchBar
          ? AppBarSearchBar(onSearchPressed: onSearchPressed)
          : Text(
              title ?? '',
              style: AppTextStyles.appBarTitle.copyWith(
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
      actions: showSearchBar || actionIcon == null
          ? null
          : [
              AppBarActionButton(icon: actionIcon!, onPressed: onActionPressed),
              const SizedBox(width: AppSizes.s8),
            ],
    );
  }

  @override
  Size get preferredSize =>
      Size.fromHeight(showSearchBar ? 72.0 : kToolbarHeight);
}

class AppBarSearchBar extends StatelessWidget {
  final VoidCallback? onSearchPressed;

  const AppBarSearchBar({super.key, this.onSearchPressed});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSizes.s4,
        vertical: AppSizes.s8,
      ),
      child: AppTextField(
        onSubmitted: (_) {
          onSearchPressed?.call();
        },
        isDense: true,
        hintText: 'Search...',
        borderRadius: AppRadius.circular20,
        prefixIcon: Icon(
          Icons.search,
          color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.5),
          size: AppSizes.iconNormal,
        ),
      ),
    );
  }
}

class AppBarBackButton extends StatelessWidget {
  final VoidCallback? onPressed;

  const AppBarBackButton({super.key, this.onPressed});

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(
        Icons.arrow_back_ios_new,
        color: Theme.of(context).colorScheme.onSurface,
      ),
      onPressed: onPressed ?? () => Navigator.pop(context),
    );
  }
}

class AppBarSearchButton extends StatelessWidget {
  final VoidCallback? onPressed;

  const AppBarSearchButton({super.key, this.onPressed});

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(Icons.search, color: Theme.of(context).colorScheme.onSurface),
      onPressed: onPressed ?? () {},
    );
  }
}

class AppBarActionButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onPressed;

  const AppBarActionButton({super.key, required this.icon, this.onPressed});

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(icon, color: Theme.of(context).colorScheme.onSurface),
      onPressed: onPressed ?? () {},
    );
  }
}
