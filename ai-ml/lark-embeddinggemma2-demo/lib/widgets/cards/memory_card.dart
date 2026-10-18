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
import 'audio_card.dart';
import 'photo_card.dart';
import 'text_note_card.dart';
import 'video_card.dart';

class MemoryCard extends StatelessWidget {
  final ScoredMemory scoredMemory;
  final VoidCallback? onTap;
  final bool isSearchActive;
  final bool isTile;

  const MemoryCard({
    super.key,
    required this.scoredMemory,
    this.onTap,
    this.isSearchActive = false,
    this.isTile = false,
  });

  @override
  Widget build(BuildContext context) {
    switch (scoredMemory.item.type) {
      case MediaType.photo:
        return PhotoCard(scoredMemory: scoredMemory, onTap: onTap, isSearchActive: isSearchActive, isTile: isTile);
      case MediaType.video:
        return VideoCard(scoredMemory: scoredMemory, onTap: onTap, isSearchActive: isSearchActive, isTile: isTile);
      case MediaType.voiceMemo:
        return AudioCard(scoredMemory: scoredMemory, onTap: onTap, isSearchActive: isSearchActive, isTile: isTile);
      case MediaType.textNote:
        return TextNoteCard(scoredMemory: scoredMemory, onTap: onTap, isSearchActive: isSearchActive, isTile: isTile);
    }
  }
}

/// Shared match percentage pill badge (`94% Match`).
class CardMatchBadge extends StatelessWidget {
  final int matchPercent;
  final Color color;
  final bool isTile;
  final bool hasShadow;

  const CardMatchBadge({
    super.key,
    required this.matchPercent,
    required this.color,
    this.isTile = false,
    this.hasShadow = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isTile ? 7 : 10,
        vertical: isTile ? 3 : 4,
      ),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(16),
        boxShadow: hasShadow
            ? [
                BoxShadow(
                  color: Colors.black.withOpacity(0.15),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      ),
      child: Text(
        '$matchPercent% Match',
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
          fontSize: isTile ? 10 : 12,
        ),
      ),
    );
  }
}

/// Shared media type pill badge (either dark translucent overlay or tinted inline pill).
class CardMediaTypeBadge extends StatelessWidget {
  final MediaType type;
  final bool isTile;
  final bool isOverlay;
  final IconData? iconOverride;

  const CardMediaTypeBadge.overlay({
    super.key,
    required this.type,
    this.isTile = false,
    this.iconOverride,
  }) : isOverlay = true;

  const CardMediaTypeBadge.inline({
    super.key,
    required this.type,
    this.iconOverride,
  })  : isTile = false,
        isOverlay = false;

  @override
  Widget build(BuildContext context) {
    final color = type.accentColor;
    final icon = iconOverride ?? (isOverlay ? type.badgeIcon : type.filterIcon);

    if (isOverlay) {
      return Container(
        padding: EdgeInsets.symmetric(
          horizontal: isTile ? 6 : 8,
          vertical: isTile ? 2 : 3,
        ),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.6),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              color: Colors.white,
              size: isTile ? 10 : 12,
            ),
            const SizedBox(width: 4),
            Text(
              type.badgeLabel,
              style: TextStyle(
                color: Colors.white,
                fontSize: isTile ? 9 : 11,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 13),
          const SizedBox(width: 4),
          Text(
            type.badgeLabel,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

/// Shared duration pill overlay for video and voice memo cards.
class CardDurationBadge extends StatelessWidget {
  final String duration;
  final bool isTile;

  const CardDurationBadge({
    super.key,
    required this.duration,
    this.isTile = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isTile ? 6 : 8,
        vertical: isTile ? 2 : 3,
      ),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.7),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        duration,
        style: TextStyle(
          color: Colors.white,
          fontSize: isTile ? 9 : 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

/// Shared card footer displaying 1-line title and 1–2 line subtitle/excerpt.
class CardMetadataFooter extends StatelessWidget {
  final String title;
  final String subtitle;
  final bool isTile;
  final bool italicSubtitle;

  const CardMetadataFooter({
    super.key,
    required this.title,
    required this.subtitle,
    this.isTile = false,
    this.italicSubtitle = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        isTile ? 10 : 14,
        isTile ? 8 : 14,
        isTile ? 10 : 14,
        isTile ? 8 : 14,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: isTile ? 13 : 16,
              fontWeight: FontWeight.bold,
              color: AppTheme.textMain,
            ),
          ),
          SizedBox(height: isTile ? 2 : 4),
          Text(
            subtitle,
            maxLines: isTile ? 1 : 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: isTile ? 11 : 13,
              fontStyle: italicSubtitle ? FontStyle.italic : FontStyle.normal,
              color: AppTheme.textMuted,
              height: 1.3,
            ),
          ),
        ],
      ),
    );
  }
}

/// Shared shell for cards with a top media preview Stack and bottom metadata footer.
class MediaPreviewCardShell extends StatelessWidget {
  final ScoredMemory scoredMemory;
  final bool isSearchActive;
  final bool isTile;
  final VoidCallback? onTap;
  final Widget preview;
  final Widget? centerOverlay;
  final String? subtitleOverride;
  final bool italicSubtitle;
  final bool showDurationOverlay;

  const MediaPreviewCardShell({
    super.key,
    required this.scoredMemory,
    required this.isSearchActive,
    required this.isTile,
    required this.preview,
    this.onTap,
    this.centerOverlay,
    this.subtitleOverride,
    this.italicSubtitle = false,
    this.showDurationOverlay = false,
  });

  @override
  Widget build(BuildContext context) {
    final item = scoredMemory.item;
    final showBadge = scoredMemory.shouldShowMatchBadge(isSearchActive);
    final edgeInset = isTile ? 8.0 : 12.0;

    return Card(
      clipBehavior: Clip.hardEdge,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Stack(
              alignment: Alignment.center,
              children: [
                isTile
                    ? AspectRatio(
                        aspectRatio: 1.0,
                        child: SizedBox(width: double.infinity, child: preview),
                      )
                    : SizedBox(
                        height: 180,
                        width: double.infinity,
                        child: preview,
                      ),
                if (centerOverlay != null) centerOverlay!,
                if (showBadge)
                  Positioned(
                    top: edgeInset,
                    right: edgeInset,
                    child: CardMatchBadge(
                      matchPercent: scoredMemory.matchPercent,
                      color: item.type.accentColor,
                      isTile: isTile,
                    ),
                  ),
                Positioned(
                  bottom: edgeInset,
                  left: edgeInset,
                  child: CardMediaTypeBadge.overlay(
                    type: item.type,
                    isTile: isTile,
                  ),
                ),
                if (showDurationOverlay && item.duration != null)
                  Positioned(
                    bottom: edgeInset,
                    right: edgeInset,
                    child: CardDurationBadge(
                      duration: item.duration!,
                      isTile: isTile,
                    ),
                  ),
              ],
            ),
            CardMetadataFooter(
              title: item.title,
              subtitle: subtitleOverride ?? item.description,
              isTile: isTile,
              italicSubtitle: italicSubtitle,
            ),
          ],
        ),
      ),
    );
  }
}
