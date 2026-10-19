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

import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/memory_item.dart';
import '../models/watched_folder.dart';
import '../repositories/memory_repository.dart';
import '../engine/local_vector_engine.dart';
import '../services/vertex_ai_client.dart';

class MemorySearchController extends ChangeNotifier {
  final MemoryRepository repository;
  final Duration warmupRetryDelay;
  final int maxWarmupRetries;

  String _query = '';
  MediaType? _selectedType;
  int _dimension = 768;
  double _confidenceThreshold = LocalVectorEngine.defaultConfidenceThreshold;
  bool _isSearching = false;
  bool _isWarmingUp = false;
  bool _isModelReady = false;
  bool _isWarmupLoopRunning = false;
  int _warmupAttempt = 0;
  int _searchSeq = 0;
  String? _errorMessage;
  Duration? _searchLatency;
  List<ScoredMemory> _results = [];
  List<WatchedFolder> _watchedFolders = [];
  bool _isSyncingFolders = false;
  Timer? _autoSyncTimer;

  MemorySearchController({
    required this.repository,
    this.warmupRetryDelay = const Duration(seconds: 4),
    this.maxWarmupRetries = 120,
  }) {
    _resetToAll();
    loadWatchedFolders();
  }

  List<WatchedFolder> get watchedFolders => _watchedFolders;
  bool get isSyncingFolders => _isSyncingFolders;

  String get query => _query;
  MediaType? get selectedType => _selectedType;
  int get dimension => _dimension;
  double get confidenceThreshold => _confidenceThreshold;
  bool get isSearching => _isSearching;
  bool get isWarmingUp => _isWarmingUp;
  bool get isModelReady => _isModelReady;
  int get warmupAttempt => _warmupAttempt;
  String? get errorMessage => _errorMessage;
  Duration? get searchLatency => _searchLatency;
  List<ScoredMemory> get results => _results;
  List<MemoryItem> get allItems => repository.items;

  set confidenceThreshold(double val) {
    if (_confidenceThreshold == val) return;
    _confidenceThreshold = val;
    if (_query.isNotEmpty) {
      search(_query);
    } else {
      notifyListeners();
    }
  }

  void _resetToAll() {
    final filtered = _selectedType == null
        ? repository.items
        : repository.items.where((i) => i.type == _selectedType).toList();

    _results = filtered.map((item) => ScoredMemory(item: item, score: 1.0)).toList();
  }

  /// Proactively pings the Vertex AI endpoints to trigger scale-up from zero
  /// and polls until the models are warm and ready for inference.
  Future<bool> warmUpModel({bool manual = false}) async {
    if (_isWarmupLoopRunning) return _isModelReady;
    _isWarmupLoopRunning = true;
    if (manual) {
      _isWarmingUp = true;
      _warmupAttempt = 0;
      _errorMessage = null;
      notifyListeners();
    }

    try {
      for (int attempt = 1; attempt <= maxWarmupRetries; attempt++) {
        try {
          await repository.vertexAiClient.embedText(
            'warmup',
            token: repository.vertexToken,
          );
          _isWarmingUp = false;
          _isModelReady = true;
          _warmupAttempt = 0;
          notifyListeners();
          return true;
        } on VertexAiScaleUpException {
          _warmupAttempt = attempt;
          _isWarmingUp = true;
          _isModelReady = false;
          notifyListeners();
          if (attempt < maxWarmupRetries) {
            await Future.delayed(warmupRetryDelay);
          }
        } catch (_) {
          _isWarmingUp = false;
          _isModelReady = false;
          notifyListeners();
          return false;
        }
      }
      _isWarmingUp = false;
      notifyListeners();
      return false;
    } finally {
      _isWarmupLoopRunning = false;
    }
  }

  Future<void> search(String newQuery) async {
    final seq = ++_searchSeq;
    _query = newQuery.trim();
    _errorMessage = null;

    if (_query.isEmpty) {
      _isSearching = false;
      _isWarmingUp = false;
      _warmupAttempt = 0;
      _searchLatency = null;
      _resetToAll();
      notifyListeners();
      return;
    }

    _isSearching = true;
    _warmupAttempt = 0;
    notifyListeners();

    final stopwatch = Stopwatch()..start();

    while (seq == _searchSeq && _query.isNotEmpty) {
      try {
        final searchResults = await repository.search(
          _query,
          dimension: _dimension,
          filterType: _selectedType,
          minScore: _confidenceThreshold,
        );
        if (seq != _searchSeq) return;
        stopwatch.stop();
        _results = searchResults;
        _searchLatency = stopwatch.elapsed;
        _isWarmingUp = false;
        _isModelReady = true;
        _warmupAttempt = 0;
        _isSearching = false;
        notifyListeners();
        return;
      } on VertexAiScaleUpException catch (e) {
        if (seq != _searchSeq) return;
        _warmupAttempt++;
        if (_warmupAttempt > maxWarmupRetries) {
          stopwatch.stop();
          _isWarmingUp = false;
          _isSearching = false;
          _errorMessage = e.message;
          notifyListeners();
          return;
        }
        _isWarmingUp = true;
        _isModelReady = false;
        _errorMessage = null;
        notifyListeners();
        await Future.delayed(warmupRetryDelay);
      } catch (e) {
        if (seq != _searchSeq) return;
        stopwatch.stop();
        _isWarmingUp = false;
        _isSearching = false;
        _errorMessage = e.toString();
        notifyListeners();
        return;
      }
    }
  }

  void filterByType(MediaType? type) {
    if (_selectedType == type) return;
    _selectedType = type;

    if (_query.isNotEmpty) {
      search(_query);
    } else {
      _resetToAll();
      notifyListeners();
    }
  }

  void setDimension(int newDim) {
    if (_dimension == newDim) return;
    _dimension = newDim;
    if (_query.isNotEmpty) {
      search(_query);
    } else {
      notifyListeners();
    }
  }

  Future<void> _refreshCurrentResults() async {
    if (_query.isNotEmpty) {
      await search(_query);
    } else {
      _resetToAll();
      notifyListeners();
    }
  }

  Future<void> _runFolderSyncAction(Future<void> Function() action) async {
    _isSyncingFolders = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await action();
      await _refreshCurrentResults();
    } catch (e) {
      _errorMessage = e.toString().replaceFirst('Exception: ', '');
    } finally {
      _isSyncingFolders = false;
      notifyListeners();
    }
  }

  Future<void> addCustomMemory({
    required MediaType type,
    required String title,
    required String contentOrDescription,
  }) async {
    _isSearching = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final client = repository.vertexAiClient;
      final embedding = await client.embedText(
        contentOrDescription,
        token: repository.vertexToken,
      );

      final newItem = MemoryItem(
        id: 'local_${DateTime.now().millisecondsSinceEpoch}',
        type: type,
        title: title,
        timestamp: DateTime.now(),
        embedding: embedding,
        description: contentOrDescription,
        assetPath: '',
        textContent: type == MediaType.textNote ? contentOrDescription : null,
        metadata: {
          'isLocalFile': true,
          'tags': [type.name, 'custom'],
        },
      );

      repository.addMemoryItem(newItem);
      _isSearching = false;
      await _refreshCurrentResults();
    } catch (e) {
      _errorMessage = 'Failed to index custom memory: $e';
      _isSearching = false;
      notifyListeners();
    }
  }

  void updateToken(String token) {
    repository.updateVertexAiToken(token);
    notifyListeners();
  }

  Future<void> loadWatchedFolders() async {
    try {
      _watchedFolders = await repository.fetchWatchedFolders();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> addWatchedFolder(String path) async {
    await _runFolderSyncAction(() async {
      _watchedFolders = await repository.addWatchedFolder(path);
    });
  }

  Future<void> removeWatchedFolder(String path) async {
    await _runFolderSyncAction(() async {
      _watchedFolders = await repository.removeWatchedFolder(path);
    });
  }

  Future<void> syncWatchedFolders() async {
    await _runFolderSyncAction(() async {
      final res = await repository.syncWatchedFolders();
      final list = res['folders'] as List<dynamic>? ?? [];
      _watchedFolders = list
          .map((e) => WatchedFolder.fromJson(e as Map<String, dynamic>))
          .toList();
    });
  }

  void startAutoSync({Duration interval = const Duration(seconds: 4)}) {
    _autoSyncTimer?.cancel();
    _autoSyncTimer = Timer.periodic(interval, (_) => pollForUpdates());
  }

  void stopAutoSync() {
    _autoSyncTimer?.cancel();
    _autoSyncTimer = null;
  }

  Future<void> pollForUpdates() async {
    final changed = await repository.reloadMemories();
    if (changed) {
      await loadWatchedFolders();
      await _refreshCurrentResults();
    }
  }

  @override
  void dispose() {
    stopAutoSync();
    super.dispose();
  }
}

