import 'dart:ui'; // Import for PointerDeviceKind
import 'package:flutter/material.dart';
import 'package:fashion_app/core_app/ui/screens/welcome/welcome_screen.dart';

import 'package:firebase_core/firebase_core.dart';
import 'package:fashion_app/firebase_options.dart';

import 'package:provider/provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/providers/try_it_on_provider.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/services/adk_fitting_room_service.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/providers/styling_provider.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/services/adk_styling_service.dart';
import 'package:fashion_app/core_app/providers/cart_provider.dart';
import 'package:fashion_app/core_app/ui/design_library/theme.dart';

// Removed app_routes

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => TryItOnProvider(aiService: AdkFittingRoomService()),
        ),
        ChangeNotifierProvider(
          create: (_) => StylingProvider(stylingService: AdkStylingService()),
        ),
        ChangeNotifierProvider(create: (_) => CartProvider()),
      ],
      child: MaterialApp(
        scrollBehavior: const AppScrollBehavior(),
        debugShowCheckedModeBanner: false,
        title: 'Thread Count',
        darkTheme: darkTheme,
        themeMode: ThemeMode.dark,
        home: const WelcomeScreen(),
      ),
    );
  }
}

class AppScrollBehavior extends MaterialScrollBehavior {
  const AppScrollBehavior();

  @override
  Set<PointerDeviceKind> get dragDevices => {
    PointerDeviceKind.touch,
    PointerDeviceKind.mouse,
    PointerDeviceKind.trackpad,
  };
}
