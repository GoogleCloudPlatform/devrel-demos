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
import '../theme/app_theme.dart';

class WatchedFoldersDialog extends StatefulWidget {
  final MemorySearchController controller;

  const WatchedFoldersDialog({
    super.key,
    required this.controller,
  });

  static Future<void> show(BuildContext context, MemorySearchController controller) {
    return showDialog(
      context: context,
      builder: (ctx) => WatchedFoldersDialog(controller: controller),
    );
  }

  @override
  State<WatchedFoldersDialog> createState() => _WatchedFoldersDialogState();
}

class _WatchedFoldersDialogState extends State<WatchedFoldersDialog> {
  final TextEditingController _pathController = TextEditingController();
  bool _isAdding = false;

  @override
  void dispose() {
    _pathController.dispose();
    super.dispose();
  }

  Future<void> _addFolder() async {
    final path = _pathController.text.trim();
    if (path.isEmpty) return;

    setState(() => _isAdding = true);
    await widget.controller.addWatchedFolder(path);
    if (mounted) {
      setState(() {
        _isAdding = false;
        _pathController.text = '';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final folders = widget.controller.watchedFolders;
        final isSyncing = widget.controller.isSyncingFolders;

        return AlertDialog(
          backgroundColor: AppTheme.creamCanvas,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.amberPrimary.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.folder_special_rounded, color: AppTheme.amberPrimary, size: 24),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Text(
                  'Watched Folders',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textMain),
                ),
              ),
              if (isSyncing)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.amberPrimary),
                )
              else
                IconButton(
                  tooltip: 'Sync All Folders Now',
                  icon: const Icon(Icons.refresh_rounded, color: AppTheme.ceruleanBlue),
                  onPressed: () => widget.controller.syncWatchedFolders(),
                ),
            ],
          ),
          content: SizedBox(
            width: 520,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Lark Memory monitors these folders on your Mac. When new notes, documents, or photos are saved, they are automatically indexed with Vertex AI EmbeddingGemma 2.',
                  style: TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.4),
                ),
                const SizedBox(height: 16),
                if (folders.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.inputFill,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.borderSubtle),
                    ),
                    child: const Center(
                      child: Text(
                        'No folders currently watched. Add ~/Documents below to begin.',
                        style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                      ),
                    ),
                  )
                else
                  Flexible(
                    child: ListView.separated(
                      shrinkWrap: true,
                      itemCount: folders.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final f = folders[index];
                        return Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AppTheme.borderSubtle),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.folder_rounded, color: AppTheme.amberPrimary, size: 22),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      f.path,
                                      style: const TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        color: AppTheme.textMain,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      '${f.itemCount} items indexed • ${f.autoWatch ? "Auto-watching" : "Manual sync"}${f.lastSynced != null ? " • Last sync: ${f.lastSynced}" : ""}',
                                      style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                                    ),
                                  ],
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.delete_outline_rounded, size: 20, color: Colors.grey),
                                tooltip: 'Unwatch Folder',
                                onPressed: isSyncing
                                    ? null
                                    : () => widget.controller.removeWatchedFolder(f.path),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                const SizedBox(height: 16),
                const Divider(color: AppTheme.borderSubtle),
                const SizedBox(height: 12),
                const Text(
                  'Add Folder to Watch',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textMain),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _pathController,
                        decoration: InputDecoration(
                          hintText: 'e.g. ~/Documents, ~/Desktop/Notes',
                          hintStyle: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
                          isDense: true,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                          filled: true,
                          fillColor: AppTheme.inputFill,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: const BorderSide(color: AppTheme.borderSubtle),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: const BorderSide(color: AppTheme.borderSubtle),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton.icon(
                      onPressed: (_isAdding || isSyncing) ? null : _addFolder,
                      icon: _isAdding
                          ? const SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.add_rounded, size: 18),
                      label: const Text('Watch'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.amberPrimary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ],
                ),
                if (widget.controller.errorMessage != null) ...[
                  const SizedBox(height: 10),
                  Text(
                    widget.controller.errorMessage!,
                    style: const TextStyle(fontSize: 12, color: Colors.red),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }
}
