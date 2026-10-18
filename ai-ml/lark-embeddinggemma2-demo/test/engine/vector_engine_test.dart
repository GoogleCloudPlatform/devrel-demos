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

import 'dart:math' as math;
import 'package:flutter_test/flutter_test.dart';
import 'package:lark_memory/models/memory_item.dart';
import 'package:lark_memory/engine/local_vector_engine.dart';

void main() {
  group('LocalVectorEngine.dotProduct', () {
    test('returns 0.0 for orthogonal unit vectors', () {
      final a = [1.0, 0.0];
      final b = [0.0, 1.0];
      expect(LocalVectorEngine.dotProduct(a, b), closeTo(0.0, 1e-6));
    });

    test('returns 1.0 for identical unit vectors', () {
      final a = [0.6, 0.8];
      final b = [0.6, 0.8];
      expect(LocalVectorEngine.dotProduct(a, b), closeTo(1.0, 1e-6));
    });

    test('handles empty or dimension mismatch cleanly', () {
      expect(LocalVectorEngine.dotProduct([], []), 0.0);
      expect(LocalVectorEngine.dotProduct([1.0], [1.0, 2.0]), 1.0);
    });
  });

  group('LocalVectorEngine.truncateMrl', () {
    test('truncates vector to target dimension and re-normalizes to unit length', () {
      final original = List.generate(768, (i) => (i + 1) * 0.01);
      final truncated = LocalVectorEngine.truncateMrl(original, 256);

      expect(truncated.length, 256);

      // Check L2 norm equals 1.0
      final norm = math.sqrt(truncated.fold<double>(0.0, (sum, val) => sum + val * val));
      expect(norm, closeTo(1.0, 1e-5));
    });

    test('returns original if targetDim >= original.length', () {
      final vec = [0.6, 0.8];
      final res = LocalVectorEngine.truncateMrl(vec, 10);
      expect(res.length, 2);
    });
  });

  group('LocalVectorEngine.rank', () {
    final itemPhoto = MemoryItem(
      id: 'mem_1',
      title: 'Ramen Bowl',
      description: 'Hot soup',
      type: MediaType.photo,
      assetPath: 'assets/ramen.jpg',
      timestamp: DateTime.now(),
      embedding: [0.9, 0.1, 0.0],
    );

    final itemVoice = MemoryItem(
      id: 'mem_2',
      title: 'Rain Walk Audio',
      description: 'Walking in rain',
      type: MediaType.voiceMemo,
      assetPath: 'assets/rain.m4a',
      timestamp: DateTime.now(),
      duration: '0:30',
      embedding: [0.1, 0.9, 0.0],
    );

    final itemVideo = MemoryItem(
      id: 'mem_3',
      title: 'Concert Clip',
      description: 'Guitar solo',
      type: MediaType.video,
      assetPath: 'assets/concert.mp4',
      timestamp: DateTime.now(),
      duration: '0:45',
      embedding: [0.0, 0.1, 0.9],
    );

    test('ranks items by descending similarity', () {
      final queryVec = [1.0, 0.0, 0.0];
      final results = LocalVectorEngine.rank(queryVec, [itemPhoto, itemVoice, itemVideo]);

      expect(results.length, 3);
      expect(results[0].item.id, 'mem_1'); // 0.9 similarity
      expect(results[1].item.id, 'mem_2'); // 0.1 similarity
      expect(results[2].item.id, 'mem_3'); // 0.0 similarity
      expect(results[0].score, closeTo(0.9, 1e-5));
    });

    test('applies filterType correctly', () {
      final queryVec = [1.0, 0.0, 0.0];
      final results = LocalVectorEngine.rank(
        queryVec,
        [itemPhoto, itemVoice, itemVideo],
        filterType: MediaType.voiceMemo,
      );

      expect(results.length, 1);
      expect(results.first.item.id, 'mem_2');
      expect(results.first.item.type, MediaType.voiceMemo);
    });

    test('filters by minScore threshold', () {
      final queryVec = [1.0, 0.0, 0.0];
      final results = LocalVectorEngine.rank(
        queryVec,
        [itemPhoto, itemVoice, itemVideo],
        minScore: 0.5,
      );

      expect(results.length, 1);
      expect(results.first.item.id, 'mem_1');
    });

    test('uses genuine EmbeddingGemma2 similarity score for matchPercent without artificial 100% stretching', () {
      final queryVec = [1.0, 0.0, 0.0];
      final results = LocalVectorEngine.rank(
        queryVec,
        [itemPhoto, itemVoice, itemVideo],
        minScore: -1.0,
      );

      expect(results.length, 3);
      // 0.9 cosine similarity should display as 90% Match, not stretched to 100%
      expect(results.first.calibratedScore, isNull);
      expect(results.first.matchPercent, 90);
      expect(results.first.score, closeTo(0.9, 0.001));
    });

    test('ScoredMemory matchPercent falls back to raw score truncation when uncalibrated', () {
      final uncalibrated = ScoredMemory(
        item: itemPhoto,
        score: 0.765,
      );
      expect(uncalibrated.matchPercent, 76);

      final calibrated = ScoredMemory(
        item: itemPhoto,
        score: 0.765,
        calibratedScore: 0.95,
      );
      expect(calibrated.matchPercent, 95);
    });

    test('adaptiveCutoff keeps temporal videos and songs on single-concept queries while cutting off static partial matches on multi-concept queries', () {
      final queryVec = [1.0, 0.0];
      final ramenPhoto = MemoryItem(
        id: 'photo_ramen',
        title: 'Photo',
        description: 'Captured photo',
        type: MediaType.photo,
        assetPath: 'image-d.jpeg',
        timestamp: DateTime.now(),
        embedding: [0.7939, 0.0],
      );
      final ramenSong = MemoryItem(
        id: 'song_ramen',
        title: 'Voice Memo',
        description: 'Lyrics',
        type: MediaType.voiceMemo,
        assetPath: 'whiskers-and-warm-broth.mp3',
        timestamp: DateTime.now(),
        embedding: [0.7318, 0.0],
      );
      final ramenVideo = MemoryItem(
        id: 'video_ramen',
        title: 'Video',
        description: 'Captured video',
        type: MediaType.video,
        assetPath: 'video-a.mp4',
        timestamp: DateTime.now(),
        embedding: [0.7190, 0.0],
      );

      final singleConceptResults = LocalVectorEngine.rank(
        queryVec,
        [ramenPhoto, ramenSong, ramenVideo],
        minScore: LocalVectorEngine.defaultConfidenceThreshold,
      );
      expect(
        singleConceptResults.map((r) => r.item.id).toList(),
        ['photo_ramen', 'song_ramen', 'video_ramen'],
      );

      final multiConceptVideo = MemoryItem(
        id: 'video_hamster_ramen',
        title: 'Video',
        description: 'Captured video',
        type: MediaType.video,
        assetPath: 'video-a.mp4',
        timestamp: DateTime.now(),
        embedding: [0.7973, 0.0],
      );
      final multiConceptSong = MemoryItem(
        id: 'song_hamster_ramen',
        title: 'Voice Memo',
        description: 'Lyrics',
        type: MediaType.voiceMemo,
        assetPath: 'whiskers-and-warm-broth.mp3',
        timestamp: DateTime.now(),
        embedding: [0.7661, 0.0],
      );
      final partialNote = MemoryItem(
        id: 'note_ramen_only',
        title: 'Note',
        description: 'Ramen only',
        type: MediaType.textNote,
        assetPath: 'journal-d.txt',
        timestamp: DateTime.now(),
        embedding: [0.7347, 0.0],
      );

      final multiConceptResults = LocalVectorEngine.rank(
        queryVec,
        [multiConceptVideo, multiConceptSong, partialNote],
        minScore: LocalVectorEngine.defaultConfidenceThreshold,
      );
      expect(
        multiConceptResults.map((r) => r.item.id).toList(),
        ['video_hamster_ramen', 'song_hamster_ramen'],
      );
    });
  });
}
