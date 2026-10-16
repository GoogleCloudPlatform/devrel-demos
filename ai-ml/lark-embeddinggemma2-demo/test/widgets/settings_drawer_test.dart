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
import 'package:lark_memory/theme/app_theme.dart';
import 'package:lark_memory/widgets/settings_drawer.dart';

void main() {
  Widget buildTestableWidget(Widget child) {
    return MaterialApp(
      theme: AppTheme.lightTheme,
      home: Scaffold(
        endDrawer: child,
        body: Builder(
          builder: (context) => ElevatedButton(
            onPressed: () => Scaffold.of(context).openEndDrawer(),
            child: const Text('Open Settings'),
          ),
        ),
      ),
    );
  }

  group('SettingsDrawer Widget', () {
    testWidgets('allows entering token and calls onTokenSaved', (tester) async {
      tester.view.physicalSize = const Size(1200, 1000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      String? savedToken;

      await tester.pumpWidget(
        buildTestableWidget(
          SettingsDrawer(
            currentToken: 'initial-token',
            currentDimension: 768,
            onTokenSaved: (t) => savedToken = t,
            onDimensionChanged: (_) {},
          ),
        ),
      );

      // Open drawer
      await tester.tap(find.text('Open Settings'));
      await tester.pumpAndSettle();

      expect(find.text('Settings & Cloud Sync'), findsOneWidget);
      expect(find.text('initial-token'), findsOneWidget);

      // Enter new token
      await tester.enterText(find.byType(TextField).first, 'ya29.new-token-abc');
      await tester.ensureVisible(find.text('Save Token'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Save Token'));
      await tester.pumpAndSettle();

      expect(savedToken, 'ya29.new-token-abc');
    });

    testWidgets('confirms cleaned settings drawer omits verbose/deprecated controls', (tester) async {
      tester.view.physicalSize = const Size(1200, 1000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        buildTestableWidget(
          SettingsDrawer(
            currentToken: '',
            currentDimension: 768,
            onTokenSaved: (_) {},
          ),
        ),
      );

      // Open drawer
      await tester.tap(find.text('Open Settings'));
      await tester.pumpAndSettle();

      // Verify removed sections are absent
      expect(find.text('256-d Fast MRL'), findsNothing);
      expect(find.text('768-d Full Quality'), findsNothing);
      expect(find.text('Embedding Dimension (MRL)'), findsNothing);
      expect(find.text('gcloud auth print-access-token'), findsNothing);
      expect(find.text('Watched Folders'), findsNothing);

      // Verify core settings remain
      expect(find.text('Settings & Cloud Sync'), findsOneWidget);
      expect(find.text('Cloud + Local Hybrid Mode'), findsOneWidget);
      expect(find.text('Google Cloud Access Token'), findsOneWidget);
    });

    testWidgets('runs connection test and shows success feedback', (tester) async {
      tester.view.physicalSize = const Size(1200, 1000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        buildTestableWidget(
          SettingsDrawer(
            currentToken: 'valid-token',
            currentDimension: 768,
            onTokenSaved: (_) {},
            onDimensionChanged: (_) {},
            onTestConnection: () async => true,
          ),
        ),
      );

      // Open drawer
      await tester.tap(find.text('Open Settings'));
      await tester.pumpAndSettle();

      // Tap test connection
      await tester.ensureVisible(find.text('Test Endpoint Connection'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Test Endpoint Connection'));
      await tester.pumpAndSettle();

      expect(find.textContaining('Connected'), findsOneWidget);
    });
  });
}
