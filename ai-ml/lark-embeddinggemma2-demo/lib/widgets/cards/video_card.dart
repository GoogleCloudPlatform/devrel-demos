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
import '../../services/api_config.dart';
import 'memory_card.dart';

class VideoCard extends StatelessWidget {
  final ScoredMemory scoredMemory;
  final VoidCallback? onTap;
  final bool isSearchActive;
  final bool isTile;

  const VideoCard({
    super.key,
    required this.scoredMemory,
    this.onTap,
    this.isSearchActive = false,
    this.isTile = false,
  });

  @override
  Widget build(BuildContext context) {
    final item = scoredMemory.item;

    return MediaPreviewCardShell(
      scoredMemory: scoredMemory,
      isSearchActive: isSearchActive,
      isTile: isTile,
      onTap: onTap,
      showDurationOverlay: true,
      preview: _buildVideoThumbnail(item, isTile),
      centerOverlay: Container(
        padding: EdgeInsets.all(isTile ? 8 : 12),
        decoration: BoxDecoration(
          color: AppTheme.coralPink.withOpacity(0.9),
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.25),
              blurRadius: 8,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Icon(
          Icons.play_arrow_rounded,
          color: Colors.white,
          size: isTile ? 22 : 32,
        ),
      ),
    );
  }

  Widget _buildVideoThumbnail(MemoryItem item, bool isTile) {
    final metadataThumb = item.metadata?['thumbnailPath'] as String?;
    final filename = item.assetPath.split('/').last.split('\\').last;
    final baseName = filename.contains('.')
        ? filename.substring(0, filename.lastIndexOf('.'))
        : filename;
    final defaultAssetThumb = 'assets/media/thumbnails/$baseName.png';

    final fallback = Container(
      color: const Color(0xFF1E293B),
      child: Center(
        child: Icon(
          Icons.movie_creation_outlined,
          size: isTile ? 36 : 56,
          color: AppTheme.coralPink.withOpacity(0.4),
        ),
      ),
    );

    final thumbPath = metadataThumb ?? defaultAssetThumb;

    Widget imageWidget;
    if (item.assetPath.startsWith('assets/') && thumbPath.startsWith('assets/')) {
      imageWidget = Image.asset(
        thumbPath,
        cacheWidth: 400,
        gaplessPlayback: true,
        filterQuality: FilterQuality.low,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) => Image.network(
          ApiConfig.url('/api/thumbnail?path=${Uri.encodeComponent(item.assetPath)}'),
          cacheWidth: 400,
          gaplessPlayback: true,
          filterQuality: FilterQuality.low,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) => fallback,
        ),
      );
    } else if (metadataThumb != null && !metadataThumb.startsWith('assets/')) {
      imageWidget = Image.network(
        ApiConfig.url('/api/file?path=${Uri.encodeComponent(metadataThumb)}&w=400'),
        cacheWidth: 400,
        gaplessPlayback: true,
        filterQuality: FilterQuality.low,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) => Image.network(
          ApiConfig.url('/api/thumbnail?path=${Uri.encodeComponent(item.assetPath)}'),
          cacheWidth: 400,
          gaplessPlayback: true,
          filterQuality: FilterQuality.low,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) => fallback,
        ),
      );
    } else {
      imageWidget = Image.network(
        ApiConfig.url('/api/thumbnail?path=${Uri.encodeComponent(item.assetPath)}'),
        cacheWidth: 400,
        gaplessPlayback: true,
        filterQuality: FilterQuality.low,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) => fallback,
      );
    }

    return Stack(
      children: [
        Positioned.fill(child: imageWidget),
        // Dark translucent overlay so the play button and metadata chips stand out clearly
        Positioned.fill(
          child: Container(
            color: Colors.black.withOpacity(0.18),
          ),
        ),
      ],
    );
  }
}
