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

// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import '../models/memory_item.dart';

Future<bool> launchPlatformMedia({
  required MemoryItem item,
  required String url,
  required String filename,
  required String mimeType,
}) async {
  if (item.type == MediaType.textNote &&
      item.textContent != null &&
      (item.assetPath.isEmpty || item.assetPath.startsWith('local://'))) {
    final blob = html.Blob([item.textContent!], 'text/plain;charset=utf-8');
    final blobUrl = html.Url.createObjectUrlFromBlob(blob);
    html.window.open(blobUrl, '_blank');
    return true;
  }

  html.window.open(url, '_blank');
  return true;
}
