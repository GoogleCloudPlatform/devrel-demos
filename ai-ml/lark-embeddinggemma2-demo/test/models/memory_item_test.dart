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

import 'package:flutter_test/flutter_test.dart';
import 'package:lark_memory/models/memory_item.dart';

void main() {
  group('MediaType enum', () {
    test('contains all four supported media types', () {
      expect(MediaType.values, containsAll([
        MediaType.photo,
        MediaType.video,
        MediaType.voiceMemo,
        MediaType.textNote,
      ]));
    });

    test('fromString parses strings correctly', () {
      expect(MediaTypeExtension.fromString('photo'), MediaType.photo);
      expect(MediaTypeExtension.fromString('video'), MediaType.video);
      expect(MediaTypeExtension.fromString('voiceMemo'), MediaType.voiceMemo);
      expect(MediaTypeExtension.fromString('textNote'), MediaType.textNote);
      expect(MediaTypeExtension.fromString('unknown'), MediaType.photo); // fallback
    });
  });

  group('MemoryItem model', () {
    final sampleJson = {
      'id': 'mem_01',
      'title': 'Late Night Ramen Bowl',
      'description': 'Steaming hot tonkotsu ramen with soft-boiled egg',
      'type': 'photo',
      'assetPath': 'assets/media/photos/ramen_bowl.jpg',
      'timestamp': '2026-10-12T23:30:00Z',
      'duration': null,
      'textContent': null,
      'embedding': [0.1, 0.2, 0.3],
      'metadata': {'location': 'Shibuya', 'weather': 'Rainy'},
    };

    test('parses complete JSON correctly', () {
      final item = MemoryItem.fromJson(sampleJson);
      expect(item.id, 'mem_01');
      expect(item.title, 'Late Night Ramen Bowl');
      expect(item.type, MediaType.photo);
      expect(item.assetPath, 'assets/media/photos/ramen_bowl.jpg');
      expect(item.timestamp, DateTime.parse('2026-10-12T23:30:00Z'));
      expect(item.duration, isNull);
      expect(item.textContent, isNull);
      expect(item.embedding, [0.1, 0.2, 0.3]);
      expect(item.metadata?['location'], 'Shibuya');
    });

    test('parses voiceMemo and textNote specific fields', () {
      final voiceJson = {
        'id': 'mem_02',
        'title': 'Rain Walk Memo',
        'description': 'Voice memo about rainy walk',
        'type': 'voiceMemo',
        'assetPath': 'assets/media/audio/rain_walk.m4a',
        'timestamp': '2026-10-12T23:15:00Z',
        'duration': '0:34',
        'textContent': 'Transcript of voice memo',
        'embedding': [0.5, 0.5],
      };

      final item = MemoryItem.fromJson(voiceJson);
      expect(item.type, MediaType.voiceMemo);
      expect(item.duration, '0:34');
      expect(item.textContent, 'Transcript of voice memo');
      expect(item.metadata, isNull);
    });

    test('serializes to JSON correctly (round-trip)', () {
      final item = MemoryItem.fromJson(sampleJson);
      final jsonOutput = item.toJson();
      final roundTripped = MemoryItem.fromJson(jsonOutput);

      expect(roundTripped.id, item.id);
      expect(roundTripped.title, item.title);
      expect(roundTripped.type, item.type);
      expect(roundTripped.assetPath, item.assetPath);
      expect(roundTripped.embedding, item.embedding);
      expect(roundTripped.metadata?['location'], item.metadata?['location']);
    });
  });

  group('ScoredMemory model', () {
    test('holds item and score properly', () {
      final item = MemoryItem(
        id: 'mem_test',
        title: 'Test',
        description: 'Desc',
        type: MediaType.photo,
        assetPath: 'assets/test.jpg',
        timestamp: DateTime.now(),
        embedding: [1.0, 0.0],
      );

      final scored = ScoredMemory(item: item, score: 0.85);
      expect(scored.item.id, 'mem_test');
      expect(scored.score, 0.85);
    });
  });
}
