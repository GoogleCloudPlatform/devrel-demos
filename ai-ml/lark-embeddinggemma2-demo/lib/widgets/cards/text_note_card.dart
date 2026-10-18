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
import '../../models/memory_item.dart';
import '../../theme/app_theme.dart';
import 'memory_card.dart';

class TextNoteCard extends StatelessWidget {
  final ScoredMemory scoredMemory;
  final VoidCallback? onTap;
  final bool isSearchActive;
  final bool isTile;

  const TextNoteCard({
    super.key,
    required this.scoredMemory,
    this.onTap,
    this.isSearchActive = false,
    this.isTile = false,
  });

  @override
  Widget build(BuildContext context) {
    final item = scoredMemory.item;
    final excerpt = item.textContent ?? item.description;
    final showBadge = scoredMemory.shouldShowMatchBadge(isSearchActive);

    if (isTile) {
      return MediaPreviewCardShell(
        scoredMemory: scoredMemory,
        isSearchActive: isSearchActive,
        isTile: true,
        onTap: onTap,
        subtitleOverride: excerpt,
        italicSubtitle: true,
        preview: Container(
          color: AppTheme.lavenderPurple.withOpacity(0.12),
          child: Center(
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: const Icon(
                Icons.article_rounded,
                color: AppTheme.lavenderPurple,
                size: 26,
              ),
            ),
          ),
        ),
      );
    }

    return Card(
      clipBehavior: Clip.hardEdge,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const CardMediaTypeBadge.inline(type: MediaType.textNote),
                  if (showBadge)
                    CardMatchBadge(
                      matchPercent: scoredMemory.matchPercent,
                      color: AppTheme.lavenderPurple,
                      hasShadow: false,
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                item.title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textMain,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.lavenderPurple.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: AppTheme.lavenderPurple.withOpacity(0.15),
                  ),
                ),
                child: Text(
                  excerpt,
                  maxLines: 5,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontStyle: FontStyle.italic,
                    color: AppTheme.textMain,
                    height: 1.4,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  const Icon(
                    Icons.access_time_rounded,
                    size: 13,
                    color: AppTheme.textMuted,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    item.formattedTimestamp,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppTheme.textMuted,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
