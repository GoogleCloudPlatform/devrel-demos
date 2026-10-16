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
import 'package:flutter/services.dart' show rootBundle;
import 'package:http/http.dart' as http;
import '../engine/local_vector_engine.dart';
import '../models/memory_item.dart';
import '../models/watched_folder.dart';
import '../services/vertex_ai_client.dart';
import '../services/api_config.dart';

typedef JsonFileLoader = Future<String> Function(String path);

class MemoryRepository {
  VertexAiClient _vertexAiClient;
  final JsonFileLoader _jsonLoader;

  final List<MemoryItem> _items = [];
  final Map<String, List<double>> _queryCache = {};
  bool _isInitialized = false;
  String? _customToken;
  String? _lastMemoriesEtag;
  String? _lastMemoriesRawBody;

  MemoryRepository({
    VertexAiClient? vertexAiClient,
    JsonFileLoader? jsonLoader,
  })  : _vertexAiClient = vertexAiClient ?? VertexAiClient(),
        _jsonLoader = jsonLoader ?? rootBundle.loadString;

  List<MemoryItem> get allItems => List.unmodifiable(_items);
  List<MemoryItem> get items => _items;
  bool get isInitialized => _isInitialized;
  String? get vertexToken => _customToken ?? _vertexAiClient.defaultToken;
  VertexAiClient get vertexAiClient => _vertexAiClient;

  void addMemoryItem(MemoryItem item) {
    _items.insert(0, item);
    _lastMemoriesEtag = null;
    _lastMemoriesRawBody = null;
  }

  void updateVertexAiToken(String token) {
    _customToken = token;
    _vertexAiClient = VertexAiClient(defaultToken: token);
  }

  List<WatchedFolder> _parseWatchedFolders(String responseBody) {
    final data = json.decode(responseBody) as Map<String, dynamic>;
    final list = data['folders'] as List<dynamic>? ?? [];
    return list.map((e) => WatchedFolder.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<WatchedFolder>> fetchWatchedFolders() async {
    try {
      final res = await http.get(ApiConfig.uri('/api/watched-folders'));
      if (res.statusCode == 200) {
        return _parseWatchedFolders(res.body);
      }
    } catch (_) {}
    return [];
  }

  Future<List<WatchedFolder>> addWatchedFolder(String path) async {
    final res = await http.post(
      ApiConfig.uri('/api/watched-folders'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'path': path}),
    );
    if (res.statusCode == 200) {
      await reloadMemories();
      return _parseWatchedFolders(res.body);
    } else {
      final err = json.decode(res.body)['error'] ?? 'Failed to add folder';
      throw Exception(err);
    }
  }

  Future<List<WatchedFolder>> removeWatchedFolder(String path) async {
    final res = await http.delete(
      ApiConfig.uri('/api/watched-folders'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'path': path}),
    );
    if (res.statusCode == 200) {
      await reloadMemories();
      return _parseWatchedFolders(res.body);
    }
    return [];
  }

  Future<Map<String, dynamic>> syncWatchedFolders() async {
    final res = await http.post(ApiConfig.uri('/api/sync-folders'));
    if (res.statusCode == 200) {
      final data = json.decode(res.body) as Map<String, dynamic>;
      await reloadMemories();
      return data;
    } else {
      final err = json.decode(res.body)['error'] ?? 'Failed to sync folders';
      throw Exception(err);
    }
  }

  bool _parseAndApplyMemoriesWithDiff(Map<String, dynamic> data) {
    final oldIds = _items.map((i) => i.id).toSet();
    final oldById = {for (final m in _items) m.id: m};
    final memoriesJson = data['memories'] as List<dynamic>? ?? [];
    final newItems = [
      for (final itemJson in memoriesJson)
        MemoryItem.fromJson(itemJson as Map<String, dynamic>),
    ];
    final newIds = newItems.map((i) => i.id).toSet();
    bool changed = oldIds.length != newIds.length || !oldIds.containsAll(newIds);
    if (!changed) {
      for (final newItem in newItems) {
        final oldItem = oldById[newItem.id];
        final embeddingChanged = oldItem == null ||
            oldItem.embedding.length != newItem.embedding.length ||
            (oldItem.embedding.isNotEmpty &&
                oldItem.embedding.first != newItem.embedding.first);
        if (oldItem == null ||
            embeddingChanged ||
            oldItem.title != newItem.title ||
            oldItem.textContent != newItem.textContent ||
            oldItem.description != newItem.description ||
            oldItem.timestamp != newItem.timestamp ||
            oldItem.metadata?['revision'] != newItem.metadata?['revision'] ||
            oldItem.metadata?['embeddingVersion'] !=
                newItem.metadata?['embeddingVersion']) {
          changed = true;
          break;
        }
      }
    }
    if (changed || _items.isEmpty) {
      _items
        ..clear()
        ..addAll(newItems);
    }
    return changed;
  }

  Future<bool> reloadMemories() async {
    try {
      final res = await http.get(
        ApiConfig.uri('/api/memories'),
        headers: _lastMemoriesEtag != null
            ? {'If-None-Match': _lastMemoriesEtag!}
            : null,
      );
      if (res.statusCode == 304) {
        return false;
      }
      if (res.statusCode == 200) {
        _lastMemoriesEtag = res.headers['etag'];
        if (_lastMemoriesRawBody == res.body) {
          return false;
        }
        _lastMemoriesRawBody = res.body;
        final data = json.decode(res.body) as Map<String, dynamic>;
        return _parseAndApplyMemoriesWithDiff(data);
      }
    } catch (_) {}

    final jsonString = await _jsonLoader('assets/data/bundled_memories.json');
    if (_lastMemoriesRawBody == jsonString) {
      return false;
    }
    _lastMemoriesRawBody = jsonString;
    final data = json.decode(jsonString) as Map<String, dynamic>;
    return _parseAndApplyMemoriesWithDiff(data);
  }

  /// Loads indexed memories from the local backend or bundled assets.
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      bool loadedLive = false;
      try {
        final res = await http.get(ApiConfig.uri('/api/memories'));
        if (res.statusCode == 200) {
          _lastMemoriesEtag = res.headers['etag'];
          _lastMemoriesRawBody = res.body;
          final data = json.decode(res.body) as Map<String, dynamic>;
          _parseAndApplyMemoriesWithDiff(data);
          loadedLive = true;
        }
      } catch (_) {}

      if (!loadedLive) {
        final jsonString = await _jsonLoader('assets/data/bundled_memories.json');
        _lastMemoriesRawBody = jsonString;
        final data = json.decode(jsonString) as Map<String, dynamic>;
        _parseAndApplyMemoriesWithDiff(data);
      }

      _isInitialized = true;
    } catch (e) {
      throw StateError('Failed to initialize MemoryRepository from assets: $e');
    }
  }

  /// Searches the local memories using live EmbeddingGemma 2 vector embeddings
  /// with zero fallbacks. If the Vertex AI endpoint is scaling up from zero,
  /// throws [VertexAiScaleUpException] so the caller can display warm-up status
  /// and automatically retry until the model is ready.
  Future<List<ScoredMemory>> search(
    String query, {
    MediaType? filterType,
    int dimension = 768,
    String? token,
    String? endpointUrl,
    double minScore = LocalVectorEngine.defaultConfidenceThreshold,
  }) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) {
      return const [];
    }

    if (!_isInitialized) {
      await initialize();
    }

    final normalizedKey = _normalizeQuery(trimmed);
    List<double>? queryVector = _queryCache[normalizedKey];

    // Always compute query vector via live EmbeddingGemma 2 endpoint if not already
    // computed in this session (no sampleQueries or lexical fallbacks).
    if (queryVector == null) {
      queryVector = await _vertexAiClient.embedText(
        trimmed,
        token: token,
        endpointUrl: endpointUrl,
      );
      _queryCache[normalizedKey] = queryVector;
    }

    // Rank locally using pure EmbeddingGemma 2 cosine similarity (never inspects filenames)
    return LocalVectorEngine.rank(
      queryVector,
      _items,
      filterType: filterType,
      dimension: dimension,
      minScore: minScore,
    );
  }

  /// Adds a custom local memory item to the repository.
  Future<void> addCustomMemory(MemoryItem item) async {
    _items.add(item);
    _lastMemoriesEtag = null;
    _lastMemoriesRawBody = null;
  }

  static String _normalizeQuery(String q) {
    return q.trim().toLowerCase();
  }
}
