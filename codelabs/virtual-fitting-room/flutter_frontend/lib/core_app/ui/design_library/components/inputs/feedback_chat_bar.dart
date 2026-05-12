import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/design_library/app_styles.dart';
import 'package:fashion_app/core_app/ui/design_library/components/layout/keyboard_aware_positioned.dart';

class FeedbackChatBar extends StatefulWidget {
  final ValueChanged<String>? onSubmitted;
  final bool isLoading;

  const FeedbackChatBar({super.key, this.onSubmitted, this.isLoading = false});

  @override
  State<FeedbackChatBar> createState() => _FeedbackChatBarState();
}

class _FeedbackChatBarState extends State<FeedbackChatBar> {
  final TextEditingController _controller = TextEditingController();
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    final hasText = _controller.text.trim().isNotEmpty;
    if (_hasText != hasText) {
      setState(() {
        _hasText = hasText;
      });
    }
  }

  @override
  void dispose() {
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    if (_hasText && !widget.isLoading) {
      widget.onSubmitted?.call(_controller.text);
      _controller.clear();
      FocusScope.of(context).unfocus();
    }
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardAwarePositioned(
      child: Container(
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: AppRadius.circular30,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, -2),
            ),
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: _controller,
                enabled: !widget.isLoading,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _submit(),
                minLines: 1,
                maxLines: 1,
                decoration: const InputDecoration(
                  hintText: 'Feedback for the styling',
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: AppSizes.s24,
                    vertical: AppSizes.s16,
                  ),
                ),
              ),
            ),
            AnimatedSize(
              duration: AppDurations.fast,
              curve: Curves.easeOutCubic,
              alignment: Alignment.centerRight,
              child: AnimatedSwitcher(
                duration: AppDurations.fast,
                switchInCurve: Curves.easeOut,
                switchOutCurve: Curves.easeIn,
                child: _hasText
                    ? Padding(
                        key: const ValueKey('send_button'),
                        padding: const EdgeInsets.only(
                          right: AppSizes.s8,
                          bottom: AppSizes.s4,
                        ),
                        child: IconButton(
                          icon: const Icon(Icons.send_rounded),
                          color: Theme.of(context).colorScheme.primary,
                          tooltip: 'Send feedback',
                          onPressed: widget.isLoading ? null : _submit,
                        ),
                      )
                    : const SizedBox.shrink(key: ValueKey('empty_space')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
