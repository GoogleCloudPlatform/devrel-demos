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
import 'package:flutter_test/flutter_test.dart';
import 'package:lark_memory/controllers/memory_search_controller.dart';
import 'package:lark_memory/main.dart';
import 'package:lark_memory/repositories/memory_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final bundledJson = File('test/fixtures/mock_memories.json').readAsStringSync();

  testWidgets('LarkMemoryApp smoke test', (WidgetTester tester) async {
    final repository = MemoryRepository(jsonLoader: (path) async => bundledJson);
    await repository.initialize();
    final searchController = MemorySearchController(repository: repository);

    await tester.pumpWidget(LarkMemoryApp(searchController: searchController));
    await tester.pumpAndSettle();

    expect(find.text('Lark Memory'), findsOneWidget);
    expect(find.text('15 memories'), findsOneWidget);
  });
}
