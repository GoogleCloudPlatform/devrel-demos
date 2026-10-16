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
import 'package:lark_memory/widgets/filter_chips.dart';
import 'package:lark_memory/widgets/search_header.dart';

void main() {
  Widget buildTestableWidget(Widget child) {
    return MaterialApp(
      theme: AppTheme.lightTheme,
      home: Scaffold(
        body: child,
      ),
    );
  }

  group('SearchHeader Widget', () {
    testWidgets('renders search field without suggestions by default', (tester) async {
      final controller = TextEditingController();

      await tester.pumpWidget(
        buildTestableWidget(
          SearchHeader(
            controller: controller,
            onQuerySubmitted: (_) {},
          ),
        ),
      );

      expect(find.byType(TextField), findsOneWidget);
      expect(find.byType(ActionChip), findsNothing);
    });

    testWidgets('renders spark suggestions when explicitly provided', (tester) async {
      String? submittedQuery;
      final controller = TextEditingController();

      await tester.pumpWidget(
        buildTestableWidget(
          SearchHeader(
            controller: controller,
            onQuerySubmitted: (q) => submittedQuery = q,
            sparkSuggestions: const [
              {
                'label': '🍜 Ramen after concert',
                'query': 'that rainy night when we got ramen after the concert',
              },
            ],
          ),
        ),
      );

      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('🍜 Ramen after concert'), findsOneWidget);

      // Tap spark suggestion
      await tester.tap(find.text('🍜 Ramen after concert'));
      await tester.pumpAndSettle();

      expect(controller.text, 'that rainy night when we got ramen after the concert');
      expect(submittedQuery, 'that rainy night when we got ramen after the concert');
    });

    testWidgets('submitting text triggers onQuerySubmitted callback', (tester) async {
      String? submittedQuery;
      final controller = TextEditingController();

      await tester.pumpWidget(
        buildTestableWidget(
          SearchHeader(
            controller: controller,
            onQuerySubmitted: (q) => submittedQuery = q,
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), 'mountain sunset');
      await tester.testTextInput.receiveAction(TextInputAction.search);
      await tester.pumpAndSettle();

      expect(submittedQuery, 'mountain sunset');
    });
  });

  group('FilterChipsBar Widget', () {
    testWidgets('displays all media filters and invokes onFilterChanged', (tester) async {
      MediaType? selectedType;

      await tester.pumpWidget(
        buildTestableWidget(
          FilterChipsBar(
            selectedType: null,
            onFilterChanged: (type) => selectedType = type,
          ),
        ),
      );

      expect(find.text('All'), findsOneWidget);
      expect(find.text('Photos'), findsOneWidget);
      expect(find.text('Videos'), findsOneWidget);
      expect(find.text('Voice'), findsOneWidget);
      expect(find.text('Notes'), findsOneWidget);

      // Tap 'Voice' chip
      await tester.tap(find.text('Voice'));
      await tester.pumpAndSettle();

      expect(selectedType, MediaType.voiceMemo);

      // Tap 'Notes' chip
      await tester.tap(find.text('Notes'));
      await tester.pumpAndSettle();

      expect(selectedType, MediaType.textNote);
    });
  });
}
