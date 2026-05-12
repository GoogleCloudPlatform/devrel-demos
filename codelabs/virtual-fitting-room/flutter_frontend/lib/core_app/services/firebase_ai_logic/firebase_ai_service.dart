import 'dart:async';
import 'dart:io';
import 'package:firebase_ai/firebase_ai.dart';
import 'package:flutter/foundation.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/services/try_it_on_service.dart';

const String geminiModel = 'gemini-3.1-flash-image-preview';
const String tryOnPrompt =
    'Identify the product in the product image. Modify the image of the the person so that they are wearing with the item in the product image. Only modify the product on the person. You should strongly avoid changing anything else in the image. The person must be wearing the product from the second image. High quality, photorealistic 2k resolution.';

class FirebaseAIService implements TryItOnService {
  final GenerativeModel? _model;

  FirebaseAIService()
    : _model = FirebaseAI.googleAI().generativeModel(model: geminiModel);

  @visibleForTesting
  FirebaseAIService.forTesting() : _model = null;

  @override
  Future<(Uint8List?, String?)> generateTryOnImage(
    Uint8List userImageBytes,
    Uint8List productImageBytes,
  ) async {
    final prompt = TextPart(tryOnPrompt);

    final userImagePart = InlineDataPart('image/jpeg', userImageBytes);
    final productImagePart = InlineDataPart('image/png', productImageBytes);

    final content = Content.multi([prompt, userImagePart, productImagePart]);

    try {
      final response = await _model!
          .generateContent([content])
          .timeout(const Duration(seconds: 120));

      if (response.candidates.isNotEmpty) {
        final candidate = response.candidates.first;

        for (final part in candidate.content.parts) {
          if (part is InlineDataPart) {
            if (part.mimeType.startsWith('image/')) {
              return (part.bytes, null);
            }
          }
        }
        throw Exception('We could not generate an image from this photo.');
      } else {
        throw Exception('No style suggestions were returned for this image.');
      }
    } on TimeoutException {
      throw Exception(
        'The AI service took too long to respond. Please try again.',
      );
    } on SocketException {
      throw Exception('Check your internet connection and try again.');
    } catch (e) {
      // General catch for parsing/API errors from backend
      throw Exception('Failed to generate image. Please try another photo.');
    }
  }
}
