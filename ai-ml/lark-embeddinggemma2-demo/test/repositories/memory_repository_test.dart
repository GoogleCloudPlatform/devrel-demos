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
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lark_memory/models/memory_item.dart';
import 'package:lark_memory/repositories/memory_repository.dart';
import 'package:lark_memory/services/vertex_ai_client.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // Read mock fixture JSON for unit testing
  final realBundleJson = File('test/fixtures/mock_memories.json').readAsStringSync();
  final parsedFixture = json.decode(realBundleJson) as Map<String, dynamic>;
  final fixtureQueries = parsedFixture['sampleQueries'] as Map<String, dynamic>;

  VertexAiClient createMockVertexClient() {
    return VertexAiClient(
      httpClient: MockClient((request) async {
        final body = json.decode(request.body) as Map<String, dynamic>;
        final inputList = body['input'] as List<dynamic>;
        final rawInput = inputList.first as String;
        final queryText = rawInput.split('query:').last.trim().toLowerCase();
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

  group('MemoryRepository', () {
    late MemoryRepository repository;

    setUp(() async {
      repository = MemoryRepository(
        vertexAiClient: createMockVertexClient(),
        jsonLoader: (path) async => realBundleJson,
      );
      await repository.initialize();
    });

    test('initialize loads all 15 bundled memories', () {
      expect(repository.allItems.length, 15);
      expect(repository.allItems.any((m) => m.id == 'mem_01'), isTrue);
      expect(repository.allItems.any((m) => m.type == MediaType.textNote), isTrue);
      expect(repository.allItems.any((m) => m.type == MediaType.voiceMemo), isTrue);
    });

    test('searches target query via EmbeddingGemma 2 client', () async {
      const query = 'that rainy night when we got ramen after the concert';
      final results = await repository.search(query, minScore: 0.66);

      expect(results, isNotEmpty);
      expect(results.length, 6);

      final topIds = results.take(3).map((r) => r.item.id).toList();
      expect(topIds, anyOf(contains('mem_01'), contains('mem_02'), contains('mem_06')));
      expect(results.first.score, greaterThan(0.75));
    });

    test('throws VertexAiScaleUpException without fallback when endpoint returns 429', () async {
      final coldRepo = MemoryRepository(
        vertexAiClient: VertexAiClient(
          httpClient: MockClient((_) async => http.Response('Model scaling up from zero', 429)),
        ),
        jsonLoader: (path) async => realBundleJson,
      );
      await coldRepo.initialize();

      expect(
        () => coldRepo.search('hamsters eating ramen'),
        throwsA(isA<VertexAiScaleUpException>()),
      );
    });

    test('retrieves all memories when minScore is 0.0', () async {
      const query = 'that rainy night when we got ramen after the concert';
      final results = await repository.search(query, minScore: 0.0);
      expect(results.length, 15);
    });

    test('filters results by MediaType', () async {
      const query = 'that rainy night when we got ramen after the concert';
      final photoResults = await repository.search(query, filterType: MediaType.photo);

      expect(photoResults, isNotEmpty);
      expect(photoResults.every((r) => r.item.type == MediaType.photo), isTrue);
      expect(photoResults.first.item.id, 'mem_01'); // Ramen bowl photo
    });

    test('handles empty or whitespace query by returning empty list', () async {
      final results = await repository.search('   ');
      expect(results, isEmpty);
    });

    test('adds custom memory and includes it in subsequent search', () async {
      final customItem = MemoryItem(
        id: 'custom_01',
        title: 'Custom Ramen Memory',
        description: 'Eating ramen late night',
        type: MediaType.photo,
        assetPath: 'assets/custom.jpg',
        timestamp: DateTime.now(),
        embedding: List<double>.from(repository.allItems.first.embedding),
      );

      await repository.addCustomMemory(customItem);
      expect(repository.allItems.length, 16);

      final results = await repository.search('that rainy night when we got ramen after the concert');
      expect(results.any((r) => r.item.id == 'custom_01'), isTrue);
    });
  });
}
