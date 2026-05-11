import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:fashion_app/app_config.dart';

import 'package:fashion_app/workshop_tasks/step_1_try_it_on/services/try_it_on_service.dart';

class AdkFittingRoomService implements TryItOnService {
  static const _appName = 'fitting room';
  static const _userId = 'flutter_user';

  final String _baseUrl;
  final http.Client _client;

  AdkFittingRoomService({String? baseUrl, http.Client? client})
    : _baseUrl = baseUrl ?? AppConfig.adkBackendUrl,
      _client = client ?? http.Client();

  @override
  Future<(Uint8List?, String?)> generateTryOnImage(
    Uint8List userImageBytes,
    Uint8List productImageBytes,
  ) async {
    try {
      // 1. Create a new session
      final sessionId = await _createSession();

      // 2. Run the fitting room agent — returns (artifactName, gcsUrl)
      final (artifactName, gcsUrl) = await _runAgent(
        sessionId: sessionId,
        userImageBytes: userImageBytes,
        productImageBytes: productImageBytes,
      );

      if (artifactName == null) {
        throw Exception('We could not generate an image from this photo.');
      }

      // 3. Fetch the generated artifact
      final imageBytes = await _loadArtifact(
        sessionId: sessionId,
        artifactName: artifactName,
      );
      return (imageBytes, gcsUrl);
    } on SocketException {
      throw Exception('Check your internet connection and try again.');
    } on TimeoutException {
      throw Exception('The server took too long to respond. Please try again.');
    } on Exception {
      rethrow;
    } catch (e) {
      throw Exception('Failed to generate image. Please try another photo.');
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
      throw Exception('Failed to generate image. Please try another photo.');
    }
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return body['id'] as String;
  }

  Future<(String?, String?)> _runAgent({
    required String sessionId,
    required Uint8List userImageBytes,
    required Uint8List productImageBytes,
  }) async {
    final url = Uri.parse('$_baseUrl/run');
    final requestBody = jsonEncode({
      'appName': _appName,
      'userId': _userId,
      'sessionId': sessionId,
      'newMessage': {
        'role': 'user',
        'parts': [
          {
            'text':
                'Generate a virtual try-on. The first image is my photo, the second is the clothing item I want to try on.',
          },
          {
            'inlineData': {
              'mimeType': 'image/jpeg',
              'data': base64Encode(userImageBytes),
            },
          },
          {
            'inlineData': {
              'mimeType': 'image/png',
              'data': base64Encode(productImageBytes),
            },
          },
        ],
      },
    });

    final response = await _client
        .post(
          url,
          headers: {'Content-Type': 'application/json'},
          body: requestBody,
        )
        .timeout(const Duration(seconds: 300));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Failed to generate image. Please try another photo.');
    }

    final events = jsonDecode(response.body) as List<dynamic>;
    String? artifactName;
    String? gcsUrl;

    for (final event in events) {
      // Extract artifact name from artifactDelta
      final artifactDelta =
          (event['actions']?['artifactDelta'] as Map<String, dynamic>?);
      if (artifactDelta != null) {
        for (final name in artifactDelta.keys) {
          if (name.startsWith('generated_fitting_')) {
            artifactName = name;
          }
        }
      }

      // Extract GCS URL from the fitting_tool function response
      final parts =
          (event['content']?['parts'] as List<dynamic>?);
      if (parts != null) {
        for (final part in parts) {
          final funcResp =
              (part as Map<String, dynamic>)['functionResponse']
                  as Map<String, dynamic>?;
          if (funcResp?['name'] == 'fitting_tool') {
            final result =
                (funcResp!['response']?['result'] as Map<String, dynamic>?);
            final url = result?['gcs_url'] as String?;
            if (url != null && url.isNotEmpty) gcsUrl = url;
          }
        }
      }
    }

    return (artifactName, gcsUrl);
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
      throw Exception('Failed to generate image. Please try another photo.');
    }

    final part = jsonDecode(response.body) as Map<String, dynamic>;
    final inlineData = part['inlineData'] as Map<String, dynamic>?;
    if (inlineData == null) return null;

    final data = inlineData['data'] as String?;
    if (data == null) return null;

    return base64Decode(data);
  }
}
