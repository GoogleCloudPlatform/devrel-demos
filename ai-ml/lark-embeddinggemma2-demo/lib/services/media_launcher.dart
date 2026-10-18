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
import 'api_config.dart';
import 'media_launcher_io.dart'
    if (dart.library.html) 'media_launcher_web.dart' as platform_launcher;

class MediaLauncher {
  static String resolveMimeType(MemoryItem item) {
    final lower = item.assetPath.toLowerCase();
    if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg';
    if (lower.endsWith('.png')) return 'image/png';
    if (lower.endsWith('.webp')) return 'image/webp';
    if (lower.endsWith('.gif')) return 'image/gif';
    if (lower.endsWith('.mp4') || lower.endsWith('.m4v')) return 'video/mp4';
    if (lower.endsWith('.mov')) return 'video/quicktime';
    if (lower.endsWith('.webm')) return 'video/webm';
    if (lower.endsWith('.mp3')) return 'audio/mpeg';
    if (lower.endsWith('.m4a') || lower.endsWith('.aac')) return 'audio/mp4';
    if (lower.endsWith('.wav')) return 'audio/wav';
    if (lower.endsWith('.ogg')) return 'audio/ogg';
    if (lower.endsWith('.txt') || lower.endsWith('.md')) return 'text/plain';

    switch (item.type) {
      case MediaType.photo:
        return 'image/jpeg';
      case MediaType.video:
        return 'video/mp4';
      case MediaType.voiceMemo:
        return 'audio/mpeg';
      case MediaType.textNote:
        return 'text/plain';
    }
  }

  static String resolveFilename(MemoryItem item) {
    final raw = item.assetPath.split('/').last.split('\\').last.trim();
    if (raw.isNotEmpty && raw.contains('.')) {
      final ext = raw.substring(raw.lastIndexOf('.'));
      return '${item.id}$ext';
    }
    switch (item.type) {
      case MediaType.photo:
        return '${item.id}.jpg';
      case MediaType.video:
        return '${item.id}.mp4';
      case MediaType.voiceMemo:
        return '${item.id}.mp3';
      case MediaType.textNote:
        return '${item.id}.txt';
    }
  }

  static Future<bool> open(BuildContext context, MemoryItem item) async {
    final url = ApiConfig.url(
      '/api/file?path=${Uri.encodeComponent(item.assetPath)}',
    );
    final filename = resolveFilename(item);
    final mimeType = resolveMimeType(item);

    try {
      final launched = await platform_launcher.launchPlatformMedia(
        item: item,
        url: url,
        filename: filename,
        mimeType: mimeType,
      );
      if (!launched && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not open ${item.title}'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
      return launched;
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to open ${item.title}: $e'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
      return false;
    }
  }
}
