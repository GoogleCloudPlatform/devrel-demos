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
import 'controllers/memory_search_controller.dart';
import 'repositories/memory_repository.dart';
import 'screens/home_screen.dart';
import 'theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final repository = MemoryRepository();
  await repository.initialize();

  final searchController = MemorySearchController(repository: repository);

  runApp(LarkMemoryApp(searchController: searchController));
}

class LarkMemoryApp extends StatelessWidget {
  final MemorySearchController searchController;

  const LarkMemoryApp({super.key, required this.searchController});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lark Memory',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: HomeScreen(controller: searchController),
    );
  }
}
