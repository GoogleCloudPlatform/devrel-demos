// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class SearchHeader extends StatefulWidget {
  final TextEditingController controller;
  final ValueChanged<String> onQuerySubmitted;
  final VoidCallback? onClear;

  final List<Map<String, String>>? sparkSuggestions;

  const SearchHeader({
    super.key,
    required this.controller,
    required this.onQuerySubmitted,
    this.onClear,
    this.sparkSuggestions,
  });

  @override
  State<SearchHeader> createState() => _SearchHeaderState();
}

class _SearchHeaderState extends State<SearchHeader> {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: ValueListenableBuilder<TextEditingValue>(
            valueListenable: widget.controller,
            builder: (context, value, _) {
              return TextField(
                controller: widget.controller,
                textInputAction: TextInputAction.search,
                onSubmitted: (text) {
                  if (text.trim().isNotEmpty) {
                    widget.onQuerySubmitted(text.trim());
                  }
                },
                decoration: InputDecoration(
                  hintText: 'Search memories by feeling, scene, or words...',
                  prefixIcon: const Icon(Icons.search_rounded, color: AppTheme.amberPrimary),
                  suffixIcon: value.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear_rounded, color: AppTheme.textMuted),
                          onPressed: () {
                            widget.controller.clear();
                            widget.onClear?.call();
                          },
                        )
                      : null,
                ),
              );
            },
          ),
        ),
        if (widget.sparkSuggestions != null && widget.sparkSuggestions!.isNotEmpty)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(
              children: widget.sparkSuggestions!.map((spark) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ActionChip(
                    backgroundColor: AppTheme.inputFill,
                    surfaceTintColor: Colors.transparent,
                    side: const BorderSide(color: AppTheme.borderSubtle),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                    label: Text(
                      spark['label']!,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.textMain,
                      ),
                    ),
                    onPressed: () {
                      widget.controller.text = spark['query']!;
                      widget.onQuerySubmitted(spark['query']!);
                    },
                  ),
                );
              }).toList(),
            ),
          ),
      ],
    );
  }
}
