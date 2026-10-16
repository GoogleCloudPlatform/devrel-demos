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
import '../models/memory_item.dart';

extension MediaTypeTheme on MediaType {
  Color get accentColor {
    switch (this) {
      case MediaType.photo:
        return AppTheme.amberPrimary;
      case MediaType.video:
        return AppTheme.coralPink;
      case MediaType.voiceMemo:
        return AppTheme.sageGreen;
      case MediaType.textNote:
        return AppTheme.lavenderPurple;
    }
  }

  String get filterLabel {
    switch (this) {
      case MediaType.photo:
        return 'Photos';
      case MediaType.video:
        return 'Videos';
      case MediaType.voiceMemo:
        return 'Voice';
      case MediaType.textNote:
        return 'Notes';
    }
  }

  IconData get filterIcon {
    switch (this) {
      case MediaType.photo:
        return Icons.photo_library_rounded;
      case MediaType.video:
        return Icons.videocam_rounded;
      case MediaType.voiceMemo:
        return Icons.mic_rounded;
      case MediaType.textNote:
        return Icons.article_rounded;
    }
  }

  String get badgeLabel {
    switch (this) {
      case MediaType.photo:
        return 'Photo';
      case MediaType.video:
        return 'Video';
      case MediaType.voiceMemo:
        return 'Voice Memo';
      case MediaType.textNote:
        return 'Note';
    }
  }

  IconData get badgeIcon {
    switch (this) {
      case MediaType.photo:
        return Icons.photo_camera_rounded;
      case MediaType.video:
        return Icons.videocam_rounded;
      case MediaType.voiceMemo:
        return Icons.mic_rounded;
      case MediaType.textNote:
        return Icons.description_rounded;
    }
  }
}

class AppTheme {
  // Cheerful palette colors
  static const Color creamCanvas = Color(0xFFFFFDF9);
  static const Color amberPrimary = Color(0xFFF59E0B);
  static const Color amberDark = Color(0xFFD97706);
  static const Color ceruleanBlue = Color(0xFF0284C7);
  static const Color coralPink = Color(0xFFFF7043);
  static const Color sageGreen = Color(0xFF10B981);
  static const Color lavenderPurple = Color(0xFF8B5CF6);
  static const Color surfaceWhite = Color(0xFFFFFFFF);
  static const Color inputFill = Color(0xFFF8FAFC);
  static const Color textMain = Color(0xFF1E293B);
  static const Color textMuted = Color(0xFF64748B);
  static const Color borderSubtle = Color(0xFFE2E8F0);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: creamCanvas,
      colorScheme: const ColorScheme.light(
        primary: amberPrimary,
        secondary: ceruleanBlue,
        surface: surfaceWhite,
        error: Color(0xFFEF4444),
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: textMain,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: creamCanvas,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textMain,
          fontSize: 22,
          fontWeight: FontWeight.bold,
          letterSpacing: -0.5,
        ),
        iconTheme: IconThemeData(color: textMain),
      ),
      cardTheme: CardTheme(
        color: surfaceWhite,
        elevation: 1,
        shadowColor: Colors.black.withOpacity(0.04),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: borderSubtle, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: inputFill,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(28),
          borderSide: const BorderSide(color: borderSubtle),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(28),
          borderSide: const BorderSide(color: borderSubtle),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(28),
          borderSide: const BorderSide(color: amberPrimary, width: 2),
        ),
        hintStyle: const TextStyle(color: textMuted, fontSize: 14),
      ),
    );
  }
}
