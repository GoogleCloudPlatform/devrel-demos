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

class AudioCard extends StatelessWidget {
  final ScoredMemory scoredMemory;
  final VoidCallback? onTap;
  final bool isSearchActive;
  final bool isTile;

  static const List<double> _waveformHeights = [
    14.0, 24.0, 36.0, 18.0, 28.0, 42.0, 22.0, 32.0, 46.0, 26.0, 16.0, 30.0, 40.0, 20.0
  ];

  const AudioCard({
    super.key,
    required this.scoredMemory,
    this.onTap,
    this.isSearchActive = false,
    this.isTile = false,
  });

  @override
  Widget build(BuildContext context) {
    final item = scoredMemory.item;
    final showBadge = scoredMemory.shouldShowMatchBadge(isSearchActive);

    if (isTile) {
      return MediaPreviewCardShell(
        scoredMemory: scoredMemory,
        isSearchActive: isSearchActive,
        isTile: true,
        onTap: onTap,
        showDurationOverlay: true,
        preview: Container(
          color: AppTheme.sageGreen.withOpacity(0.12),
          child: Center(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.sageGreen,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.15),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.play_arrow_rounded,
                    color: Colors.white,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 8),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: _waveformHeights.sublist(0, 8).map((h) {
                    return Container(
                      margin: const EdgeInsets.symmetric(horizontal: 1.5),
                      width: 3,
                      height: h * 0.6,
                      decoration: BoxDecoration(
                        color: AppTheme.sageGreen.withOpacity(0.7),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    );
                  }).toList(),
                ),
              ],
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
                  const CardMediaTypeBadge.inline(type: MediaType.voiceMemo),
                  if (showBadge)
                    CardMatchBadge(
                      matchPercent: scoredMemory.matchPercent,
                      color: AppTheme.sageGreen,
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
              const SizedBox(height: 4),
              Text(
                item.description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 13,
                  color: AppTheme.textMuted,
                  height: 1.3,
                ),
              ),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.sageGreen.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: const BoxDecoration(
                        color: AppTheme.sageGreen,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.play_arrow_rounded,
                        color: Colors.white,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: _waveformHeights.map((h) {
                          return Container(
                            width: 3,
                            height: h,
                            decoration: BoxDecoration(
                              color: AppTheme.sageGreen.withOpacity(0.7),
                              borderRadius: BorderRadius.circular(2),
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      item.duration ?? '0:30',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.sageGreen,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
