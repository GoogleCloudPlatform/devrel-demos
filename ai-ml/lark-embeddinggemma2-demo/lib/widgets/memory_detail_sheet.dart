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
import '../models/memory_item.dart';
import '../services/media_launcher.dart';
import '../theme/app_theme.dart';

class MemoryDetailSheet extends StatelessWidget {
  final ScoredMemory scoredMemory;
  final bool isQuerying;
  final ScrollController scrollController;

  const MemoryDetailSheet({
    super.key,
    required this.scoredMemory,
    required this.isQuerying,
    required this.scrollController,
  });

  static Future<void> show(
    BuildContext context, {
    required ScoredMemory scoredMemory,
    required bool isQuerying,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surfaceWhite,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.55,
          maxChildSize: 0.85,
          minChildSize: 0.35,
          builder: (context, scrollController) {
            return MemoryDetailSheet(
              scoredMemory: scoredMemory,
              isQuerying: isQuerying,
              scrollController: scrollController,
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final item = scoredMemory.item;
    final aiDescription = item.metadata?['aiDescription'] as String?;
    final tags = item.tags;

    return SingleChildScrollView(
      controller: scrollController,
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.amberPrimary.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  item.type.name.toUpperCase(),
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.amberPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            item.title,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppTheme.textMain,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              const Icon(Icons.access_time_rounded, size: 13, color: AppTheme.textMuted),
              const SizedBox(width: 4),
              Text(
                item.formattedTimestamp,
                style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
              ),
            ],
          ),
          if (item.type != MediaType.textNote && item.description.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              item.description,
              style: const TextStyle(
                fontSize: 14,
                color: AppTheme.textMuted,
                height: 1.4,
              ),
            ),
          ],
          if (aiDescription != null && aiDescription.isNotEmpty) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                Icon(
                  item.type == MediaType.photo
                      ? Icons.visibility_rounded
                      : (item.type == MediaType.voiceMemo
                          ? Icons.hearing_rounded
                          : Icons.smart_display_rounded),
                  size: 15,
                  color: AppTheme.amberPrimary,
                ),
                const SizedBox(width: 6),
                Text(
                  item.type == MediaType.photo
                      ? 'Visual Understanding (Vision AI)'
                      : (item.type == MediaType.voiceMemo
                          ? 'Audio Transcription & Vibe'
                          : 'Video Scene Breakdown'),
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textMain,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.creamCanvas,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Text(
                aiDescription,
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.4,
                  color: AppTheme.textMain,
                ),
              ),
            ),
          ],
          if (item.textContent != null) ...[
            const SizedBox(height: 16),
            const Text(
              'Content',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: AppTheme.textMain,
              ),
            ),
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.creamCanvas,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Text(
                item.textContent!,
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.4,
                  color: AppTheme.textMain,
                ),
              ),
            ),
          ],
          if (tags.isNotEmpty) ...[
            const SizedBox(height: 16),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: tags.map((tag) {
                return Chip(
                  label: Text('#$tag', style: const TextStyle(fontSize: 11)),
                  backgroundColor: AppTheme.creamCanvas,
                  side: const BorderSide(color: AppTheme.borderSubtle),
                  padding: EdgeInsets.zero,
                  visualDensity: VisualDensity.compact,
                );
              }).toList(),
            ),
          ],
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () => MediaLauncher.open(context, item),
              icon: Icon(
                item.type == MediaType.video || item.type == MediaType.voiceMemo
                    ? Icons.play_circle_fill_rounded
                    : Icons.open_in_new_rounded,
                size: 18,
              ),
              label: Text(
                item.type == MediaType.video
                    ? 'Play Video'
                    : (item.type == MediaType.voiceMemo
                        ? 'Play Audio'
                        : (item.type == MediaType.photo ? 'Open Image' : 'Open Note')),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.amberPrimary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
