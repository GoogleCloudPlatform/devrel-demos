import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/outfit.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/style_request.dart';
import 'package:fashion_app/app_config.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/services/styling_service.dart';

class AdkStylingService implements StylingService {
  static const _appName = 'stylist';
  static const _userId = 'flutter_user';

  /// Outfit hero images cycled per outfit index.
  static const _outfitHeroImages = [
    'assets/images/outfit_casual.png',
    'assets/images/outfit_floral.png',
    'assets/images/outfit_streetwear.png',
    'assets/images/outfit_evening.png',
  ];

  /// Maps catalog product IDs to local Flutter asset paths.
  /// This avoids relying on whatever image string the LLM returns.
  static const _productImageMap = {
    'id_bomber_jacket': 'assets/images/bomber_jacket.png',
    'id_flutter_hat': 'assets/images/flutter_hat.png',
    'id_flutter_letterman': 'assets/images/flutter_letterman.png',
    'id_hightop': 'assets/images/hightop.png',
    'id_plaid_shirt': 'assets/images/plaid_shirt.png',
    'id_product_1': 'assets/images/product_1.png',
    'id_product_2': 'assets/images/product_2.png',
    'id_product_3': 'assets/images/product_3.png',
    'id_product_4': 'assets/images/product_4.png',
    'id_quarter-zip': 'assets/images/quarter-zip.png',
    'id_style_1': 'assets/images/prod1_var1.png',
    'id_style_2': 'assets/images/prod2_var1.png',
    'id_style_3': 'assets/images/prod3_var1.png',
    'id_style_4': 'assets/images/prod4_var1.png',
    'id_style_5': 'assets/images/prod5_var1.png',
    'id_style_6': 'assets/images/prod6_var1.png',
    'id_style_7': 'assets/images/prod7_var1.png',
    'id_style_8': 'assets/images/prod8_var1.png',
    'id_style_9': 'assets/images/prod9_var1.png',
    'id_style_10': 'assets/images/prod10_var1.png',
    'id_style_11': 'assets/images/prod11_var1.png',
    'id_style_12': 'assets/images/prod12_var1.png',
  };

  final String _baseUrl;
  final http.Client _client;
  String? _sessionId;

  AdkStylingService({String? baseUrl, http.Client? client})
    : _baseUrl = baseUrl ?? AppConfig.adkBackendUrl,
      _client = client ?? http.Client();

  @override
  Future<List<Outfit>> getStyleSuggestions(StyleRequest request) async {
    try {
      _sessionId ??= await _createSession();
      return await _runAgent(request: request);
    } on SocketException {
      throw Exception('Check your internet connection and try again.');
    } on TimeoutException {
      throw Exception('The server took too long to respond. Please try again.');
    } on Exception {
      rethrow;
    } catch (e) {
      throw Exception('Failed to get style suggestions. Please try again.');
    }
  }

  /// Sends follow-up feedback in the same session to refine suggestions.
  @override
  Future<List<Outfit>> refineWithFeedback(String feedback) async {
    try {
      _sessionId ??= await _createSession();
      return await _runAgent(prompt: feedback);
    } on SocketException {
      throw Exception('Check your internet connection and try again.');
    } on TimeoutException {
      throw Exception('The server took too long to respond. Please try again.');
    } on Exception {
      rethrow;
    } catch (e) {
      throw Exception('Failed to refine suggestions. Please try again.');
    }
  }

  Future<String> _createSession() async {
    final url = Uri.parse(
      '$_baseUrl/apps/${Uri.encodeComponent(_appName)}/users/$_userId/sessions',
    );
    final response = await _client
        .post(
          url,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({}),
        )
        .timeout(const Duration(seconds: 15));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Failed to create styling session.');
    }
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return body['id'] as String;
  }

  Future<List<Outfit>> _runAgent({
    StyleRequest? request,
    String? prompt,
  }) async {
    final url = Uri.parse('$_baseUrl/run');

    final List<Map<String, dynamic>> parts = [];

    if (request != null) {
      parts.add({'text': _buildPrompt(request)});
      if (request.gcsUserImageUrl != null) {
        // Pass the GCS URI as text — fitting_tool resolves gs:// URIs directly,
        // preserving the user's exact appearance from the prior try-on.
        parts.add({
          'text':
              'User try-on base image (use this gs:// URI as user_image for fitting_tool): ${request.gcsUserImageUrl}',
        });
      } else if (request.userImageData != null) {
        parts.add({
          'inlineData': {
            'mimeType': 'image/jpeg',
            'data': base64Encode(request.userImageData!),
          },
        });
      }
      if (request.selectedProductId != null) {
        parts.add({
          'text':
              'Base product already tried on (MUST include in the outfit): ID=${request.selectedProductId}, Title=${request.selectedProductTitle}',
        });
      }
    } else if (prompt != null) {
      parts.add({'text': prompt});
    }

    final requestBody = jsonEncode({
      'appName': _appName,
      'userId': _userId,
      'sessionId': _sessionId,
      'newMessage': {'role': 'user', 'parts': parts},
    });

    final response = await _client
        .post(
          url,
          headers: {'Content-Type': 'application/json'},
          body: requestBody,
        )
        .timeout(const Duration(seconds: 300));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Failed to get style suggestions.');
    }

    return await _parseResponse(response.body);
  }

  String _buildPrompt(StyleRequest request) {
    final parts = <String>[];
    if (request.location.isNotEmpty) parts.add('Location: ${request.location}');
    if (request.occasion.isNotEmpty) parts.add('Occasion: ${request.occasion}');
    if (request.notes.isNotEmpty) {
      parts.add('Additional notes: ${request.notes}');
    }
    return parts.join('\n');
  }

  Future<List<Outfit>> _parseResponse(String responseBody) async {
    final events = jsonDecode(responseBody) as List<dynamic>;

    // Walk events in reverse to find the last agent text response
    String? lastText;
    for (final event in events.reversed) {
      final content = event['content'] as Map<String, dynamic>?;
      if (content == null) continue;
      final parts = content['parts'] as List<dynamic>?;
      if (parts == null) continue;
      for (final part in parts) {
        final text = part['text'] as String?;
        if (text != null && text.trim().isNotEmpty) {
          lastText = text.trim();
          break;
        }
      }
      if (lastText != null) break;
    }

    if (lastText == null) {
      throw Exception('No response received from styling.');
    }

    debugPrint('Styling raw response: $lastText');
    return await _parseOutfitsFromText(lastText);
  }

  Future<List<Outfit>> _parseOutfitsFromText(String text) async {
    // Strip markdown code fences if present
    String jsonText = text;
    final fenceMatch = RegExp(
      r'```(?:json)?\s*([\s\S]*?)\s*```',
    ).firstMatch(text);
    if (fenceMatch != null) {
      jsonText = fenceMatch.group(1)!;
    }

    // Extract the outermost JSON object
    final start = jsonText.indexOf('{');
    final end = jsonText.lastIndexOf('}');
    if (start == -1 || end == -1 || end <= start) {
      throw Exception('Styling returned an unexpected response format.');
    }
    jsonText = jsonText.substring(start, end + 1);

    final json = jsonDecode(jsonText) as Map<String, dynamic>;
    final outfitsData = json['outfits'] as List<dynamic>;

    List<Outfit> parsedOutfits = [];
    for (int index = 0; index < outfitsData.length; index++) {
      final outfitData = outfitsData[index] as Map<String, dynamic>;
      final commentary = outfitData['commentary'] as String? ?? '';
      final productsData = outfitData['products'] as List<dynamic>? ?? [];

      final products = productsData.map((p) {
        final productMap = p as Map<String, dynamic>;
        final id = productMap['id'] as String? ?? '';
        // Always resolve image from the local ID→asset map, never trust the LLM's image string
        final imagePath =
            _productImageMap[id] ??
            _outfitHeroImages[index % _outfitHeroImages.length];
        final priceRaw = productMap['price'];
        final double price = priceRaw != null
            ? (priceRaw as num).toDouble()
            : 0.0;

        return Product(
          id: id,
          title: productMap['title'] as String? ?? '',
          subtitle: productMap['subtitle'] as String? ?? '',
          price: price,
          images: [imagePath],
        );
      }).toList();

      // Use the predefined outfit hero images (not product images) so the
      // card always shows a styled "look" photo rather than a single item.
      final heroImage = _outfitHeroImages[index % _outfitHeroImages.length];

      Uint8List? imageData;
      final imageArtName = outfitData['image'] as String?;
      if (imageArtName != null &&
          imageArtName.isNotEmpty &&
          _sessionId != null) {
        try {
          imageData = await _loadArtifact(
            sessionId: _sessionId!,
            artifactName: imageArtName,
          );
        } catch (e) {
          debugPrint('Failed to load image artifact: $e');
        }
      }

      parsedOutfits.add(
        Outfit(
          imagePath: heroImage,
          imageData: imageData,
          products: products,
          commentary: commentary,
        ),
      );
    }

    return parsedOutfits;
  }

  Future<Uint8List?> _loadArtifact({
    required String sessionId,
    required String artifactName,
  }) async {
    final url = Uri.parse(
      '$_baseUrl/apps/${Uri.encodeComponent(_appName)}/users/$_userId/sessions/$sessionId/artifacts/$artifactName',
    );
    final response = await _client
        .get(url)
        .timeout(const Duration(seconds: 30));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      return null;
    }

    final part = jsonDecode(response.body) as Map<String, dynamic>;
    final inlineData = part['inlineData'] as Map<String, dynamic>?;
    if (inlineData == null) return null;

    final data = inlineData['data'] as String?;
    if (data == null) return null;

    return base64Decode(data);
  }
}
