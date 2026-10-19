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
import 'package:flutter_test/flutter_test.dart';
import 'package:lark_memory/models/memory_item.dart';
import 'package:lark_memory/theme/app_theme.dart';
import 'package:lark_memory/widgets/cards/audio_card.dart';
import 'package:lark_memory/widgets/cards/memory_card.dart';
import 'package:lark_memory/widgets/cards/photo_card.dart';
import 'package:lark_memory/widgets/cards/text_note_card.dart';
import 'package:lark_memory/widgets/cards/video_card.dart';

void main() {
  Widget buildTestableWidget(Widget child) {
    return MaterialApp(
      theme: AppTheme.lightTheme,
      home: Scaffold(
        body: SingleChildScrollView(child: child),
      ),
    );
  }

  final testPhoto = ScoredMemory(
    item: MemoryItem(
      id: 'photo_1',
      title: 'Late Night Ramen Bowl',
      description: 'Hot steaming tonkotsu ramen with soft boiled egg',
      type: MediaType.photo,
      assetPath: 'assets/media/photos/ramen_bowl.jpg',
      timestamp: DateTime(2026, 10, 10, 22, 30),
      embedding: const [1.0, 0.0],
    ),
    score: 0.942,
  );

  final testAudio = ScoredMemory(
    item: MemoryItem(
      id: 'audio_1',
      title: 'Rain Walk Audio',
      description: 'Patter of rain on umbrella walking through Shibuya',
      type: MediaType.voiceMemo,
      assetPath: 'assets/media/audio/rain_walk.m4a',
      timestamp: DateTime(2026, 10, 10, 23, 15),
      duration: '0:32',
      embedding: const [0.8, 0.2],
    ),
    score: 0.884,
  );

  final testVideo = ScoredMemory(
    item: MemoryItem(
      id: 'video_1',
      title: 'Concert Finale',
      description: 'Encore lights and screaming crowd',
      type: MediaType.video,
      assetPath: 'assets/media/videos/concert_finale.mp4',
      timestamp: DateTime(2026, 10, 10, 21, 45),
      duration: '0:45',
      embedding: const [0.7, 0.3],
    ),
    score: 0.765,
  );

  final testNote = ScoredMemory(
    item: MemoryItem(
      id: 'note_1',
      title: 'Rainy Concert Night Journal',
      description: 'Quick thoughts jotted down after the show',
      type: MediaType.textNote,
      assetPath: 'assets/media/notes/concert_night.txt',
      timestamp: DateTime(2026, 10, 11, 0, 15),
      textContent: 'The humidity was high, rain was falling in sheets outside the venue...',
      embedding: const [0.85, 0.15],
    ),
    score: 0.851,
  );

  group('MemoryCard Factory & Multimodal Cards', () {
    testWidgets('renders PhotoCard for MediaType.photo without match percentage badge', (tester) async {
      await tester.pumpWidget(
        buildTestableWidget(
          MemoryCard(scoredMemory: testPhoto),
        ),
      );

      expect(find.byType(PhotoCard), findsOneWidget);
      expect(find.text('Late Night Ramen Bowl'), findsOneWidget);
      expect(find.textContaining('% Match'), findsNothing);
    });

    testWidgets('renders AudioCard for MediaType.voiceMemo with play button and duration', (tester) async {
      await tester.pumpWidget(
        buildTestableWidget(
          MemoryCard(scoredMemory: testAudio),
        ),
      );

      expect(find.byType(AudioCard), findsOneWidget);
      expect(find.text('Rain Walk Audio'), findsOneWidget);
      expect(find.text('0:32'), findsOneWidget);
      expect(find.byIcon(Icons.play_arrow_rounded), findsOneWidget);
      expect(find.textContaining('% Match'), findsNothing);
    });

    testWidgets('renders VideoCard for MediaType.video with duration pill and play icon', (tester) async {
      await tester.pumpWidget(
        buildTestableWidget(
          MemoryCard(scoredMemory: testVideo),
        ),
      );

      expect(find.byType(VideoCard), findsOneWidget);
      expect(find.text('Concert Finale'), findsOneWidget);
      expect(find.text('0:45'), findsOneWidget);
      expect(find.textContaining('% Match'), findsNothing);
    });

    testWidgets('renders TextNoteCard for MediaType.textNote with content excerpt', (tester) async {
      await tester.pumpWidget(
        buildTestableWidget(
          MemoryCard(scoredMemory: testNote),
        ),
      );

      expect(find.byType(TextNoteCard), findsOneWidget);
      expect(find.text('Rainy Concert Night Journal'), findsOneWidget);
      expect(find.textContaining('The humidity was high'), findsOneWidget);
      expect(find.textContaining('% Match'), findsNothing);
    });

    testWidgets('renders all cards properly in tile mode (isTile: true)', (tester) async {
      await tester.pumpWidget(
        buildTestableWidget(
          Column(
            children: [
              MemoryCard(scoredMemory: testPhoto, isTile: true),
              MemoryCard(scoredMemory: testAudio, isTile: true),
              MemoryCard(scoredMemory: testVideo, isTile: true),
              MemoryCard(scoredMemory: testNote, isTile: true),
            ],
          ),
        ),
      );

      expect(find.byType(PhotoCard), findsOneWidget);
      expect(find.byType(AudioCard), findsOneWidget);
      expect(find.byType(VideoCard), findsOneWidget);
      expect(find.byType(TextNoteCard), findsOneWidget);
      expect(find.text('Late Night Ramen Bowl'), findsOneWidget);
      expect(find.text('Rain Walk Audio'), findsOneWidget);
      expect(find.text('Concert Finale'), findsOneWidget);
      expect(find.text('Rainy Concert Night Journal'), findsOneWidget);
    });

    testWidgets('invokes onTap callback when tapped', (tester) async {
      bool tapped = false;
      await tester.pumpWidget(
        buildTestableWidget(
          MemoryCard(
            scoredMemory: testPhoto,
            onTap: () => tapped = true,
          ),
        ),
      );

      await tester.tap(find.byType(PhotoCard));
      await tester.pumpAndSettle();

      expect(tapped, isTrue);
    });
  });
}
