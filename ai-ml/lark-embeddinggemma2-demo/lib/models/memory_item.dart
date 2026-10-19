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

enum MediaType {
  photo,
  video,
  voiceMemo,
  textNote,
}

extension MediaTypeExtension on MediaType {
  static MediaType fromString(String str) {
    switch (str) {
      case 'photo':
        return MediaType.photo;
      case 'video':
        return MediaType.video;
      case 'voiceMemo':
        return MediaType.voiceMemo;
      case 'textNote':
        return MediaType.textNote;
      default:
        return MediaType.photo;
    }
  }

  String get value {
    switch (this) {
      case MediaType.photo:
        return 'photo';
      case MediaType.video:
        return 'video';
      case MediaType.voiceMemo:
        return 'voiceMemo';
      case MediaType.textNote:
        return 'textNote';
    }
  }

  String get label {
    switch (this) {
      case MediaType.photo:
        return 'Photo';
      case MediaType.video:
        return 'Video';
      case MediaType.voiceMemo:
        return 'Voice';
      case MediaType.textNote:
        return 'Note';
    }
  }
}

class MemoryItem {
  final String id;
  final String title;
  final String description;
  final MediaType type;
  final String assetPath;
  final DateTime timestamp;
  final String? duration;
  final String? textContent;
  final List<double> embedding;
  final Map<String, dynamic>? metadata;

  const MemoryItem({
    required this.id,
    required this.title,
    required this.description,
    required this.type,
    required this.assetPath,
    required this.timestamp,
    this.duration,
    this.textContent,
    required this.embedding,
    this.metadata,
  });

  factory MemoryItem.fromJson(Map<String, dynamic> json) {
    return MemoryItem(
      id: json['id'] as String,
      title: json['title'] as String,
      description: (json['description'] ?? json['caption'] ?? '') as String,
      type: MediaTypeExtension.fromString(json['type'] as String),
      assetPath: (json['assetPath'] ?? json['mediaAssetPath'] ?? '') as String,
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ?? DateTime.now(),
      duration: json['duration'] as String?,
      textContent: json['textContent'] as String?,
      embedding: (json['embedding'] as List<dynamic>)
          .map((e) => (e as num).toDouble())
          .toList(),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'type': type.value,
      'assetPath': assetPath,
      'timestamp': timestamp.toIso8601String(),
      if (duration != null) 'duration': duration,
      if (textContent != null) 'textContent': textContent,
      'embedding': embedding,
      if (metadata != null) 'metadata': metadata,
    };
  }

  /// Formatted timestamp string (`YYYY-MM-DD HH:mm`).
  String get formattedTimestamp =>
      '${timestamp.year}-${timestamp.month.toString().padLeft(2, '0')}-${timestamp.day.toString().padLeft(2, '0')} '
      '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';

  /// Extracted list of string tags from `metadata['tags']`.
  List<String> get tags =>
      (metadata?['tags'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList() ??
      const [];
}

class ScoredMemory {
  final MemoryItem item;
  final double score;
  final double? calibratedScore;

  const ScoredMemory({
    required this.item,
    required this.score,
    this.calibratedScore,
  });

  /// User-facing match percentage (0 to 100), calibrated to the effective relevance range.
  int get matchPercent => calibratedScore != null
      ? (calibratedScore! * 100).clamp(0, 100).round()
      : (score * 100).clamp(0, 100).toInt();

  /// Whether the match percentage badge should be displayed on cards.
  bool shouldShowMatchBadge(bool isSearchActive) => false;
}
