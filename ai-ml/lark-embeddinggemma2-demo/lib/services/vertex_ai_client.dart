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
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'api_config.dart';

class VertexAiException implements Exception {
  final String message;
  final int? statusCode;

  const VertexAiException(this.message, [this.statusCode]);

  @override
  String toString() => 'VertexAiException: $message (code: $statusCode)';
}

class VertexAiAuthException extends VertexAiException {
  const VertexAiAuthException(String message, [int? statusCode])
      : super(message, statusCode ?? 401);
}

class VertexAiScaleUpException extends VertexAiException {
  const VertexAiScaleUpException(String message, [int? statusCode])
      : super(message, statusCode ?? 429);
}

class VertexAiClient {
  static const String defaultEndpoint = String.fromEnvironment(
    'VERTEX_ENDPOINT_URL',
    defaultValue:
        'https://YOUR_ENDPOINT_ID.us-central1-YOUR_PROJECT_NUMBER.prediction.vertexai.goog/v1/projects/YOUR_PROJECT_ID/locations/us-central1/endpoints/YOUR_ENDPOINT_ID:rawPredict',
  );

  final http.Client _httpClient;
  final String _defaultEndpointUrl;
  final String? _defaultToken;

  VertexAiClient({
    http.Client? httpClient,
    String? defaultEndpointUrl,
    String? defaultToken,
  })  : _httpClient = httpClient ?? http.Client(),
        _defaultEndpointUrl = defaultEndpointUrl ?? (kIsWeb ? '/api/embed' : ApiConfig.url('/api/embed')),
        _defaultToken = defaultToken;

  String? get defaultToken => _defaultToken;
  String get defaultEndpointUrl => _defaultEndpointUrl;

  /// Sends a text prompt to the live Vertex AI EmbeddingGemma 2 endpoint
  /// and returns the 768-dimensional unit embedding vector.
  Future<List<double>> embedText(
    String text, {
    String? token,
    String? endpointUrl,
  }) async {
    final activeToken = token ?? _defaultToken;
    final activeUrl = endpointUrl ?? _defaultEndpointUrl;

    final isLocalProxy = activeUrl.startsWith('/') ||
        activeUrl.contains('localhost') ||
        activeUrl.contains('127.0.0.1') ||
        activeUrl.contains('10.0.2.2');

    if (!isLocalProxy && (activeToken == null || activeToken.trim().isEmpty)) {
      throw const VertexAiAuthException(
        'Authentication token is required. Provide a valid Google Cloud access token.',
        401,
      );
    }

    final uri = Uri.parse(activeUrl);
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (activeToken != null && activeToken.trim().isNotEmpty) {
      headers['Authorization'] = 'Bearer ${activeToken.trim()}';
    }

    final payload = json.encode({
      'model': 'google/embeddinggemma-2',
      'input': ['task: search query | query: $text'],
    });

    try {
      final response = await _httpClient.post(
        uri,
        headers: headers,
        body: payload,
      );

      if (response.statusCode == 200) {
        final decoded = json.decode(response.body) as Map<String, dynamic>;
        final data = decoded['data'] as List<dynamic>;
        if (data.isEmpty) {
          throw const VertexAiException('Empty data received from Vertex AI');
        }
        final embeddingRaw = data.first['embedding'] as List<dynamic>;
        return embeddingRaw.map((e) => (e as num).toDouble()).toList();
      } else if (response.statusCode == 401 || response.statusCode == 403) {
        throw VertexAiAuthException(
          'Authentication failed. Token may be expired or lack Vertex AI permissions: ${response.body}',
          response.statusCode,
        );
      } else if (response.statusCode == 429) {
        throw VertexAiScaleUpException(
          'Model endpoint is warming up / scaling up from zero: ${response.body}',
          429,
        );
      } else {
        throw VertexAiException(
          'Vertex AI error ${response.statusCode}: ${response.body}',
          response.statusCode,
        );
      }
    } on VertexAiException {
      rethrow;
    } catch (e) {
      throw VertexAiException('Network error connecting to Vertex AI: $e');
    }
  }

  /// Pings the endpoint to test connectivity and authentication.
  Future<bool> testConnection({String? token, String? endpointUrl}) async {
    try {
      await embedText('ping', token: token, endpointUrl: endpointUrl);
      return true;
    } catch (_) {
      return false;
    }
  }
}
