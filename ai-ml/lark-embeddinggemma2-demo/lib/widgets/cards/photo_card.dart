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

class PhotoCard extends StatelessWidget {
  final ScoredMemory scoredMemory;
  final VoidCallback? onTap;
  final bool isSearchActive;
  final bool isTile;

  const PhotoCard({
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
      preview: Container(
        width: double.infinity,
        color: AppTheme.inputFill,
        child: _buildPhotoContent(item, isTile),
      ),
    );
  }

  Widget _buildPhotoContent(MemoryItem item, bool isTile) {
    if (item.assetPath.startsWith('assets/')) {
      return Image.asset(
        item.assetPath,
        cacheWidth: 400,
        gaplessPlayback: true,
        filterQuality: FilterQuality.low,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) => Center(
          child: Icon(
            Icons.photo_rounded,
            size: isTile ? 36 : 48,
            color: AppTheme.amberPrimary.withOpacity(0.5),
          ),
        ),
      );
    }
    return Image.network(
      ApiConfig.url('/api/file?path=${Uri.encodeComponent(item.assetPath)}&w=400'),
      cacheWidth: 400,
      gaplessPlayback: true,
      filterQuality: FilterQuality.low,
      fit: BoxFit.cover,
      errorBuilder: (context, error, stackTrace) => Center(
        child: Icon(
          Icons.photo_rounded,
          size: isTile ? 36 : 48,
          color: AppTheme.amberPrimary.withOpacity(0.5),
        ),
      ),
    );
  }
}
