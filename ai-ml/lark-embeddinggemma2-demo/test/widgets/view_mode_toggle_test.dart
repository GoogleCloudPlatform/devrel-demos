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

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lark_memory/controllers/memory_search_controller.dart';
import 'package:lark_memory/repositories/memory_repository.dart';
import 'package:lark_memory/screens/home_screen.dart';
import 'package:lark_memory/theme/app_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final bundledJson = File('test/fixtures/mock_memories.json').readAsStringSync();

  group('View Mode Grid/List Toggle', () {
    late MemoryRepository repository;
    late MemorySearchController searchController;

    setUp(() async {
      repository = MemoryRepository(
        jsonLoader: (path) async => bundledJson,
      );
      await repository.initialize();
      searchController = MemorySearchController(repository: repository);
    });

    Widget buildApp() {
      return MaterialApp(
        theme: AppTheme.lightTheme,
        home: HomeScreen(controller: searchController),
      );
    }

    testWidgets('defaults to grid view and toggles between grid and list', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(buildApp());
      await tester.pumpAndSettle();

      // 1. Initial view: grid view is displayed by default
      expect(find.byKey(const Key('memory_grid_view')), findsOneWidget);
      expect(find.byKey(const Key('memory_list_view')), findsNothing);

      // 2. Tap the toggle button to switch to list view
      final toggleButton = find.byKey(const Key('view_mode_toggle_button'));
      expect(toggleButton, findsOneWidget);
      await tester.tap(toggleButton);
      await tester.pumpAndSettle();

      // 3. Now list view is displayed
      expect(find.byKey(const Key('memory_list_view')), findsOneWidget);
      expect(find.byKey(const Key('memory_grid_view')), findsNothing);

      // 4. Tap the toggle button again to switch back to grid view
      await tester.tap(toggleButton);
      await tester.pumpAndSettle();

      // 5. Grid view is displayed again
      expect(find.byKey(const Key('memory_grid_view')), findsOneWidget);
      expect(find.byKey(const Key('memory_list_view')), findsNothing);
    });
  });
}
