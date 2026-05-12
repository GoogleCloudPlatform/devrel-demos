import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';

class AppAccordion extends StatefulWidget {
  final String title;
  final Widget child;

  const AppAccordion({super.key, required this.title, required this.child});

  @override
  State<AppAccordion> createState() => _AppAccordionState();
}

class _AppAccordionState extends State<AppAccordion> {
  final GlobalKey _key = GlobalKey();

  void _scrollToSelectedContent() {
    Future.delayed(AppDurations.fast).then((value) {
      if (!mounted) return;
      final keyContext = _key.currentContext;
      if (keyContext != null && keyContext.mounted) {
        Scrollable.ensureVisible(
          keyContext,
          duration: AppDurations.medium,
          curve: Curves.fastOutSlowIn,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Theme.of(context).colorScheme.secondary),
        ),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          key: _key,
          onExpansionChanged: (expanded) {
            if (expanded) {
              _scrollToSelectedContent();
            }
          },
          tilePadding: EdgeInsets.zero,
          title: Text(
            widget.title,
            style: AppTextStyles.accordionTitle.copyWith(
              color: Theme.of(context).colorScheme.onSurface,
            ),
          ),
          iconColor: Theme.of(context).colorScheme.tertiary,
          collapsedIconColor: Theme.of(context).colorScheme.tertiary,
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: AppSizes.s16),
              child: widget.child,
            ),
          ],
        ),
      ),
    );
  }
}
