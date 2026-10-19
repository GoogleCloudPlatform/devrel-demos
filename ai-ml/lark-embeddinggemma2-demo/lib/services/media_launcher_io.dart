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

import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import '../models/memory_item.dart';

const MethodChannel _channel =
    MethodChannel('com.antigravity.lark_memory/media_launcher');

Future<bool> launchPlatformMedia({
  required MemoryItem item,
  required String url,
  required String filename,
  required String mimeType,
}) async {
  if (Platform.isAndroid) {
    Uint8List? inlineBytes;
    if (item.type == MediaType.textNote &&
        item.textContent != null &&
        (item.assetPath.isEmpty || item.assetPath.startsWith('local://'))) {
      inlineBytes = Uint8List.fromList(utf8.encode(item.textContent!));
    } else if (item.assetPath.startsWith('assets/')) {
      try {
        final data = await rootBundle.load(item.assetPath);
        if (data.lengthInBytes <= 512 * 1024) {
          inlineBytes = data.buffer.asUint8List();
        }
      } catch (_) {}
    }

    final result = await _channel.invokeMethod<bool>('openMedia', {
      'url': url,
      'filename': filename,
      'mimeType': mimeType,
      if (inlineBytes != null) 'bytes': inlineBytes,
    });
    return result ?? false;
  }

  if (Platform.isMacOS) {
    var targetPath = item.assetPath;
    if (targetPath.startsWith('~/')) {
      final home = Platform.environment['HOME'];
      if (home != null && home.isNotEmpty) {
        targetPath = '$home${targetPath.substring(1)}';
      }
    }
    final res = await Process.run('open', [targetPath]);
    return res.exitCode == 0;
  }

  return false;
}
