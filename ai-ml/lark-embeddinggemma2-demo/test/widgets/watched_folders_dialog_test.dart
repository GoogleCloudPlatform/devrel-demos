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
import 'package:lark_memory/controllers/memory_search_controller.dart';
import 'package:lark_memory/models/watched_folder.dart';
import 'package:lark_memory/repositories/memory_repository.dart';
import 'package:lark_memory/theme/app_theme.dart';
import 'package:lark_memory/widgets/watched_folders_dialog.dart';

class MockMemoryRepository extends MemoryRepository {
  MockMemoryRepository() : super(jsonLoader: (p) async => '{"memories": [], "sampleQueries": {}}');

  final List<WatchedFolder> mockFolders = [
    const WatchedFolder(
      path: '~/Documents',
      resolvedPath: '/Users/mock/Documents',
      itemCount: 3,
      autoWatch: true,
      lastSynced: '2026-10-14 21:00',
    ),
  ];

  @override
  Future<List<WatchedFolder>> fetchWatchedFolders() async => mockFolders;

  @override
  Future<List<WatchedFolder>> addWatchedFolder(String path) async {
    mockFolders.add(WatchedFolder(
      path: path,
      resolvedPath: '/Users/mock/${path.replaceAll("~/", "")}',
      itemCount: 1,
      autoWatch: true,
    ));
    return mockFolders;
  }

  @override
  Future<List<WatchedFolder>> removeWatchedFolder(String path) async {
    mockFolders.removeWhere((f) => f.path == path);
    return mockFolders;
  }

  @override
  Future<Map<String, dynamic>> syncWatchedFolders() async {
    return {
      'status': 'success',
      'indexed_count': 3,
      'folders': mockFolders.map((e) => e.toJson()).toList(),
    };
  }
}

void main() {
  group('WatchedFoldersDialog Widget', () {
    testWidgets('displays watched folders and allows adding a new folder', (tester) async {
      tester.view.physicalSize = const Size(1200, 1000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final repo = MockMemoryRepository();
      await repo.initialize();
      final controller = MemorySearchController(repository: repo);
      await controller.loadWatchedFolders();

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () => WatchedFoldersDialog.show(context, controller),
                child: const Text('Open Folders Dialog'),
              ),
            ),
          ),
        ),
      );

      // Open dialog
      await tester.tap(find.text('Open Folders Dialog'));
      await tester.pumpAndSettle();

      expect(find.text('Watched Folders'), findsOneWidget);
      expect(find.text('~/Documents'), findsOneWidget);
      expect(find.textContaining('3 items indexed'), findsOneWidget);

      // Enter new folder
      await tester.enterText(find.byType(TextField).last, '~/Desktop/Notes');
      await tester.tap(find.text('Watch'));
      await tester.pumpAndSettle();

      expect(find.text('~/Desktop/Notes'), findsOneWidget);
    });
  });
}
