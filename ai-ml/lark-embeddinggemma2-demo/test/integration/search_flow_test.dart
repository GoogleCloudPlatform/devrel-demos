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

import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lark_memory/controllers/memory_search_controller.dart';
import 'package:lark_memory/repositories/memory_repository.dart';
import 'package:lark_memory/screens/home_screen.dart';
import 'package:lark_memory/services/vertex_ai_client.dart';
import 'package:lark_memory/theme/app_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final bundledJson = File('test/fixtures/mock_memories.json').readAsStringSync();
  final parsedFixture = json.decode(bundledJson) as Map<String, dynamic>;
  final fixtureQueries = parsedFixture['sampleQueries'] as Map<String, dynamic>;

  VertexAiClient createMockVertexClient({
    int fail429Count = 0,
    int failWarmup429Count = 0,
  }) {
    int calls = 0;
    int warmupCalls = 0;
    return VertexAiClient(
      httpClient: MockClient((request) async {
        final body = json.decode(request.body) as Map<String, dynamic>;
        final inputList = body['input'] as List<dynamic>;
        final rawInput = inputList.first as String;
        final queryText = rawInput.split('query:').last.trim().toLowerCase();
        if (queryText == 'warmup') {
          warmupCalls++;
          if (warmupCalls <= failWarmup429Count) {
            return http.Response('Model is scaling up from zero', 429);
          }
        } else {
          calls++;
          if (calls <= fail429Count) {
            return http.Response('Model is scaling up from zero', 429);
          }
        }
        final vec = fixtureQueries[queryText] ?? fixtureQueries.values.first;
        return http.Response(
          json.encode({
            'model': 'google/embeddinggemma-2',
            'data': [
              {'embedding': vec}
            ],
          }),
          200,
        );
      }),
    );
  }

  group('Lark Memory End-to-End Search Flow', () {
    late MemoryRepository repository;
    late MemorySearchController searchController;

    setUp(() async {
      repository = MemoryRepository(
        vertexAiClient: createMockVertexClient(),
        jsonLoader: (path) async => bundledJson,
      );
      await repository.initialize();
      searchController = MemorySearchController(
        repository: repository,
        warmupRetryDelay: const Duration(milliseconds: 50),
      );
    });

    Widget buildApp() {
      return MaterialApp(
        theme: AppTheme.lightTheme,
        home: HomeScreen(controller: searchController),
      );
    }

    testWidgets('loads all 15 memories and performs natural language search', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(buildApp());
      await tester.pumpAndSettle();

      // Initial state: shows all memories, NO 100% Match badges in browse mode
      expect(find.text('Lark Memory'), findsOneWidget);
      expect(find.text('15 memories'), findsOneWidget);
      expect(find.text('100% Match'), findsNothing);

      // Perform search query
      await tester.enterText(
        find.byType(TextField),
        'that rainy night when we got ramen after the concert',
      );
      await tester.testTextInput.receiveAction(TextInputAction.search);
      await tester.pumpAndSettle();

      // Top results should be ranked by relevance without displaying match percentage badges
      expect(find.text('Rainy Concert Night Journal'), findsOneWidget);
      expect(find.text('Rain Walk After the Show'), findsOneWidget);
      expect(find.text('Late Night Ramen Bowl'), findsOneWidget);
      expect(find.textContaining('% Match'), findsNothing);

      // Filter by Voice Memo
      await tester.tap(find.text('Voice'));
      await tester.pumpAndSettle();

      // Voice Memo should still be displayed
      expect(find.text('Rain Walk After the Show'), findsOneWidget);
      // Photo and text note should no longer be visible
      expect(find.text('Late Night Ramen Bowl'), findsNothing);
      expect(find.text('Rainy Concert Night Journal'), findsNothing);

      // Return to All
      await tester.tap(find.text('All'));
      await tester.pumpAndSettle();
      expect(find.text('Rainy Concert Night Journal'), findsOneWidget);
      expect(find.text('Late Night Ramen Bowl'), findsOneWidget);
    });

    testWidgets('warms up model, informs user, and shows results once EmbeddingGemma 2 is ready', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final coldRepo = MemoryRepository(
        vertexAiClient: createMockVertexClient(fail429Count: 2),
        jsonLoader: (path) async => bundledJson,
      );
      await coldRepo.initialize();
      searchController = MemorySearchController(
        repository: coldRepo,
        warmupRetryDelay: const Duration(milliseconds: 100),
      );

      await tester.pumpWidget(buildApp());
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byType(TextField),
        'that rainy night when we got ramen after the concert',
      );
      await tester.testTextInput.receiveAction(TextInputAction.search);
      await tester.pump(const Duration(milliseconds: 20));

      // Should display the warm-up state to the user while model scales up from zero
      expect(find.text('Warming up EmbeddingGemma 2...'), findsOneWidget);

      // Pump until retries finish and model returns 200 OK
      await tester.pumpAndSettle();

      expect(find.text('Warming up EmbeddingGemma 2...'), findsNothing);
      expect(find.text('Rainy Concert Night Journal'), findsOneWidget);
    });

    testWidgets('shows confident match empty state when query has no confident results', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(buildApp());
      await tester.pumpAndSettle();

      // Search for morning coffee on the balcony
      await tester.enterText(find.byType(TextField), 'morning coffee on the balcony');
      await tester.testTextInput.receiveAction(TextInputAction.search);
      await tester.pumpAndSettle();

      // Filter by Videos where all videos are below confidence threshold
      await tester.tap(find.text('Videos'));
      await tester.pumpAndSettle();

      expect(find.text('No confident matches for "morning coffee on the balcony"'), findsOneWidget);
      expect(
        find.text('The model only shows results it is confident in. Try different descriptive keywords or clear the media filter.'),
        findsOneWidget,
      );
    });

    testWidgets('warmup button wakes scale-to-zero models, shows polling progress, and transitions to AI Ready', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      // Fail first warmup call so initial auto-warmup enters warming loop, or test manual trigger:
      int warmupCalls = 0;
      bool blockAutoWarmup = true;
      final warmupClient = VertexAiClient(
        httpClient: MockClient((request) async {
          if (blockAutoWarmup) {
            return http.Response('Network offline initially', 500);
          }
          warmupCalls++;
          if (warmupCalls <= 2) {
            return http.Response('Model is scaling up from zero', 429);
          }
          final vec = fixtureQueries.values.first;
          return http.Response(
            json.encode({
              'model': 'google/embeddinggemma-2',
              'data': [
                {'embedding': vec}
              ],
            }),
            200,
          );
        }),
      );

      final coldRepo = MemoryRepository(
        vertexAiClient: warmupClient,
        jsonLoader: (path) async => bundledJson,
      );
      await coldRepo.initialize();
      searchController = MemorySearchController(
        repository: coldRepo,
        warmupRetryDelay: const Duration(milliseconds: 80),
      );

      await tester.pumpWidget(buildApp());
      await tester.pumpAndSettle();

      // Initially cold ("Warm Up" button visible)
      expect(find.byKey(const Key('warmup_model_button')), findsOneWidget);
      expect(find.text('Warm Up'), findsOneWidget);

      // Now enable scale-up simulation and tap Warm Up button
      blockAutoWarmup = false;
      await tester.tap(find.byKey(const Key('warmup_model_button')));
      await tester.pump(const Duration(milliseconds: 20));

      // Should show Warming #1 and the warming banner
      expect(find.text('Warming #1'), findsOneWidget);
      expect(find.textContaining('Warming up EmbeddingGemma 2 & Gemma 3n on Vertex AI'), findsOneWidget);

      // Pump until retries complete and 200 OK is returned
      await tester.pumpAndSettle();

      // Should now show AI Ready and the SnackBar confirmation
      expect(find.text('AI Ready'), findsOneWidget);
      expect(find.text('Vertex AI models are warm and ready!'), findsOneWidget);
    });
  });
}
