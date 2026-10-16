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
import '../controllers/memory_search_controller.dart';
import '../models/memory_item.dart';
import '../theme/app_theme.dart';
import '../widgets/cards/memory_card.dart';
import '../widgets/filter_chips.dart';
import '../widgets/search_header.dart';
import '../widgets/settings_drawer.dart';
import '../widgets/watched_folders_dialog.dart';
import '../widgets/memory_detail_sheet.dart';
import '../services/media_launcher.dart';

class HomeScreen extends StatefulWidget {
  final MemorySearchController controller;

  const HomeScreen({super.key, required this.controller});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  late final TextEditingController _searchController;
  bool _isGridView = true;

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(text: widget.controller.query);
    widget.controller.startAutoSync();
    widget.controller.warmUpModel();
  }

  @override
  void dispose() {
    widget.controller.stopAutoSync();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final results = widget.controller.results;
        final totalCount = widget.controller.allItems.length;
        final isQuerying = widget.controller.query.isNotEmpty;

        return Scaffold(
          key: _scaffoldKey,
          backgroundColor: AppTheme.creamCanvas,
          appBar: AppBar(
            elevation: 0,
            scrolledUnderElevation: 1,
            backgroundColor: AppTheme.creamCanvas,
            titleSpacing: 12,
            title: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: AppTheme.amberPrimary.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.bubble_chart_rounded,
                    color: AppTheme.amberPrimary,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Lark Memory',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.textMain,
                        ),
                      ),
                      Text(
                        isQuerying
                            ? '${results.length} matches • ${widget.controller.dimension}-d'
                            : '$totalCount memories',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppTheme.textMuted,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            actions: [
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 2),
                child: Tooltip(
                  message: widget.controller.isWarmingUp
                      ? 'Vertex AI endpoints are scaling up from zero...'
                      : widget.controller.isModelReady
                          ? 'Vertex AI endpoints are warm & ready (tap to re-verify)'
                          : 'Wake up scale-to-zero Vertex AI endpoints (EmbeddingGemma 2 & Gemma 3n)',
                  child: InkWell(
                    key: const Key('warmup_model_button'),
                    borderRadius: BorderRadius.circular(20),
                    onTap: widget.controller.isWarmingUp
                        ? null
                        : () async {
                            final messenger = ScaffoldMessenger.of(context);
                            await widget.controller.warmUpModel(manual: true);
                            if (!mounted) return;
                            if (widget.controller.isModelReady) {
                              messenger.showSnackBar(
                                const SnackBar(
                                  content: Text('Vertex AI models are warm and ready!'),
                                  duration: Duration(seconds: 2),
                                ),
                              );
                            }
                          },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                      decoration: BoxDecoration(
                        color: widget.controller.isWarmingUp
                            ? AppTheme.amberPrimary.withOpacity(0.18)
                            : widget.controller.isModelReady
                                ? const Color(0xFF2E7D32).withOpacity(0.16)
                                : AppTheme.amberPrimary.withOpacity(0.14),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: widget.controller.isWarmingUp
                              ? AppTheme.amberPrimary.withOpacity(0.5)
                              : widget.controller.isModelReady
                                  ? const Color(0xFF4CAF50).withOpacity(0.5)
                                  : AppTheme.amberPrimary.withOpacity(0.4),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (widget.controller.isWarmingUp)
                            const SizedBox(
                              width: 12,
                              height: 12,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: AppTheme.amberPrimary,
                              ),
                            )
                          else
                            Icon(
                              Icons.bolt_rounded,
                              size: 14,
                              color: widget.controller.isModelReady
                                  ? const Color(0xFF4CAF50)
                                  : AppTheme.amberPrimary,
                            ),
                          const SizedBox(width: 4),
                          Text(
                            widget.controller.isWarmingUp
                                ? 'Warming${widget.controller.warmupAttempt > 0 ? " #${widget.controller.warmupAttempt}" : "..."}'
                                : widget.controller.isModelReady
                                    ? 'AI Ready'
                                    : 'Warm Up',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: widget.controller.isWarmingUp
                                  ? AppTheme.amberPrimary
                                  : widget.controller.isModelReady
                                      ? const Color(0xFF4CAF50)
                                      : AppTheme.amberPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              IconButton(
                key: const Key('view_mode_toggle_button'),
                visualDensity: VisualDensity.compact,
                icon: Icon(
                  _isGridView ? Icons.view_list_rounded : Icons.grid_view_rounded,
                  color: AppTheme.textMain,
                ),
                tooltip: _isGridView ? 'Switch to list view' : 'Switch to grid view',
                onPressed: () {
                  setState(() {
                    _isGridView = !_isGridView;
                  });
                },
              ),
              IconButton(
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.folder_special_rounded, color: AppTheme.amberPrimary),
                tooltip: 'Watched Folders (~/Documents)',
                onPressed: () {
                  WatchedFoldersDialog.show(context, widget.controller);
                },
              ),
              IconButton(
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.tune_rounded, color: AppTheme.textMain),
                tooltip: 'Settings & Cloud Sync',
                onPressed: () {
                  _scaffoldKey.currentState?.openEndDrawer();
                },
              ),
              const SizedBox(width: 4),
            ],
          ),
          endDrawer: SettingsDrawer(
            currentToken: widget.controller.repository.vertexToken ?? '',
            currentDimension: widget.controller.dimension,
            onTokenSaved: (token) {
              widget.controller.updateToken(token);
            },
          ),
          body: Column(
            children: [
              SearchHeader(
                controller: _searchController,
                onQuerySubmitted: (q) => widget.controller.search(q),
                onClear: () {
                  _searchController.clear();
                  widget.controller.search('');
                },
              ),
              FilterChipsBar(
                selectedType: widget.controller.selectedType,
                onFilterChanged: (type) => widget.controller.filterByType(type),
              ),
              if (widget.controller.isWarmingUp && !widget.controller.isSearching)
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.fromLTRB(16, 4, 16, 4),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppTheme.amberPrimary.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.amberPrimary.withOpacity(0.3)),
                  ),
                  child: Row(
                    children: [
                      const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppTheme.amberPrimary,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Warming up EmbeddingGemma 2 & Gemma 3n on Vertex AI${widget.controller.warmupAttempt > 0 ? " (check #${widget.controller.warmupAttempt})" : ""}...',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppTheme.textMain,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              Expanded(
                child: _buildResultsView(results),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildResultsView(List<ScoredMemory> results) {
    if (widget.controller.isSearching) {
      if (widget.controller.isWarmingUp) {
        return Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const CircularProgressIndicator(color: AppTheme.amberPrimary),
                const SizedBox(height: 20),
                const Text(
                  'Warming up EmbeddingGemma 2...',
                  style: TextStyle(
                    fontSize: 16,
                    color: AppTheme.textMain,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'The Vertex AI endpoint is scaling up from zero. Your search results will appear automatically as soon as the model is ready.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 13,
                    color: AppTheme.textMuted,
                    height: 1.4,
                  ),
                ),
                if (widget.controller.warmupAttempt > 0) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Waiting for model readiness (check #${widget.controller.warmupAttempt})...',
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppTheme.amberPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      }
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: AppTheme.amberPrimary),
            SizedBox(height: 16),
            Text(
              'Finding memories with EmbeddingGemma 2...',
              style: TextStyle(
                fontSize: 14,
                color: AppTheme.textMuted,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    if (widget.controller.errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.cloud_off_rounded, size: 48, color: Colors.red.shade300),
              const SizedBox(height: 12),
              const Text(
                'Could not reach Vertex AI',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textMain),
              ),
              const SizedBox(height: 8),
              Text(
                widget.controller.errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () => _scaffoldKey.currentState?.openEndDrawer(),
                icon: const Icon(Icons.settings_rounded, size: 16),
                label: const Text('Update Access Token'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.amberPrimary,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (results.isEmpty) {
      final total = widget.controller.repository.items.length;
      if (total == 0) {
        return Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.folder_open_rounded, size: 64, color: AppTheme.amberPrimary.withOpacity(0.6)),
                const SizedBox(height: 16),
                const Text(
                  'No memories indexed yet',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textMain),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Add personal notes, memories, or index a folder from your Mac to search your real files.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 14, color: AppTheme.textMuted),
                ),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  onPressed: () => WatchedFoldersDialog.show(context, widget.controller),
                  icon: const Icon(Icons.folder_special_rounded),
                  label: const Text('Watch Documents Folder'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.amberPrimary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  ),
                ),
              ],
            ),
          ),
        );
      }

      final isSearching = widget.controller.query.isNotEmpty;
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.search_off_rounded, size: 56, color: AppTheme.amberPrimary.withOpacity(0.5)),
              const SizedBox(height: 12),
              Text(
                isSearching
                    ? 'No confident matches for "${widget.controller.query}"'
                    : 'No matching memories found',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textMain),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 6),
              Text(
                isSearching
                    ? 'The model only shows results it is confident in. Try different descriptive keywords or clear the media filter.'
                    : 'Try asking with different descriptive words or clear the media filter.',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
              ),
            ],
          ),
        ),
      );
    }

    final isSearching = widget.controller.query.isNotEmpty;

    if (_isGridView) {
      return LayoutBuilder(
        builder: (context, constraints) {
          final crossAxisCount = constraints.maxWidth < 600
              ? 2
              : (constraints.maxWidth / 220).floor().clamp(2, 6);
          final totalSpacing = 32.0 + (crossAxisCount - 1) * 12.0;
          final colWidth = (constraints.maxWidth - totalSpacing) / crossAxisCount;
          // The square media preview has height equal to colWidth.
          // The title (1 line) + description (1 line) + padding occupies ~52px.
          const textHeight = 52.0;
          final cardHeight = colWidth + textHeight;
          final childAspectRatio = (colWidth / cardHeight).clamp(0.65, 0.92);
          return GridView.builder(
            key: const Key('memory_grid_view'),
            cacheExtent: 800,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: crossAxisCount,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: childAspectRatio,
            ),
            itemCount: results.length,
            itemBuilder: (context, index) {
              final item = results[index];
              return GestureDetector(
                onLongPress: () => _showMemoryDetail(item),
                child: MemoryCard(
                  key: ValueKey(item.item.id),
                  scoredMemory: item,
                  isSearchActive: isSearching,
                  isTile: true,
                  onTap: () => _openMemoryItem(item),
                ),
              );
            },
          );
        },
      );
    }

    return ListView.separated(
      key: const Key('memory_list_view'),
      cacheExtent: 800,
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      itemCount: results.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final item = results[index];
        return GestureDetector(
          onLongPress: () => _showMemoryDetail(item),
          child: MemoryCard(
            key: ValueKey(item.item.id),
            scoredMemory: item,
            isSearchActive: isSearching,
            isTile: false,
            onTap: () => _openMemoryItem(item),
          ),
        );
      },
    );
  }

  Future<void> _openMemoryItem(ScoredMemory scored) async {
    await MediaLauncher.open(context, scored.item);
  }

  void _showMemoryDetail(ScoredMemory scored) {
    MemoryDetailSheet.show(
      context,
      scoredMemory: scored,
      isQuerying: widget.controller.query.isNotEmpty,
    );
  }
}
