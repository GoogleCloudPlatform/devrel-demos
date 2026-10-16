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

class WatchedFolder {
  final String path;
  final String resolvedPath;
  final int itemCount;
  final String? lastSynced;
  final bool autoWatch;

  const WatchedFolder({
    required this.path,
    required this.resolvedPath,
    required this.itemCount,
    this.lastSynced,
    this.autoWatch = true,
  });

  factory WatchedFolder.fromJson(Map<String, dynamic> json) {
    return WatchedFolder(
      path: json['path'] as String? ?? '',
      resolvedPath: json['resolvedPath'] as String? ?? '',
      itemCount: json['itemCount'] as int? ?? 0,
      lastSynced: json['lastSynced'] as String?,
      autoWatch: json['autoWatch'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() => {
    'path': path,
    'resolvedPath': resolvedPath,
    'itemCount': itemCount,
    'lastSynced': lastSynced,
    'autoWatch': autoWatch,
  };
}
