import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

var darkTheme = ThemeData(
  scaffoldBackgroundColor: const Color(0xFF181113),
  appBarTheme: const AppBarTheme(
    backgroundColor: Color(0xFF181113),
    foregroundColor: Colors.white,
  ),
  colorScheme: ColorScheme.fromSeed(
    seedColor: const Color(0xFFEE2B5B),
    primary: const Color(0xFFEE2B5B),
    surface: const Color(0xFF221015),
    secondary: const Color(0xFF374151),
    tertiary: const Color(0xFFD1D5DB),
    brightness: Brightness.dark,
    error: Colors.redAccent,
  ),
  useMaterial3: true,
  textTheme: GoogleFonts.plusJakartaSansTextTheme(ThemeData.dark().textTheme),
);
