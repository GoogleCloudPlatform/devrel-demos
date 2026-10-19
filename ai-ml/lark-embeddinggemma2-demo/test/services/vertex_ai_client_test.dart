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
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:lark_memory/services/vertex_ai_client.dart';

class MockHttpClient extends http.BaseClient {
  final Future<http.Response> Function(http.Request request) handler;

  MockHttpClient(this.handler);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final httpRequest = request as http.Request;
    final response = await handler(httpRequest);
    return http.StreamedResponse(
      Stream.value(response.bodyBytes),
      response.statusCode,
      headers: response.headers,
    );
  }
}

void main() {
  const dummyToken = 'test-token-123';
  const dummyEndpoint = 'https://mg-endpoint.vertexai.goog/v1/rawPredict';

  group('VertexAiClient.embedText', () {
    test('sends formatted request and returns 768-d embedding on 200 OK', () async {
      final mockVector = List<double>.filled(768, 0.036);

      final client = VertexAiClient(
        httpClient: MockHttpClient((req) async {
          expect(req.headers['Authorization'], 'Bearer $dummyToken');
          expect(req.headers['Content-Type'], 'application/json');
          
          final body = json.decode(req.body);
          expect(body['model'], 'google/embeddinggemma-2');
          expect(body['input'], ['task: search query | query: ramen tonight']);

          return http.Response(
            json.encode({
              'data': [
                {'embedding': mockVector}
              ]
            }),
            200,
          );
        }),
        defaultEndpointUrl: dummyEndpoint,
        defaultToken: dummyToken,
      );

      final result = await client.embedText('ramen tonight');
      expect(result.length, 768);
      expect(result.first, closeTo(0.036, 1e-5));
    });

    test('throws VertexAiScaleUpException on HTTP 429 scale-up response', () async {
      final client = VertexAiClient(
        httpClient: MockHttpClient((req) async {
          return http.Response(
            'Model is not yet ready for inference. Please wait while model completes scale-up from zero',
            429,
          );
        }),
        defaultEndpointUrl: dummyEndpoint,
        defaultToken: dummyToken,
      );

      expect(
        () => client.embedText('test'),
        throwsA(isA<VertexAiScaleUpException>()),
      );
    });

    test('throws VertexAiAuthException on HTTP 401 Unauthorized', () async {
      final client = VertexAiClient(
        httpClient: MockHttpClient((req) async {
          return http.Response('Unauthorized', 401);
        }),
        defaultEndpointUrl: dummyEndpoint,
        defaultToken: dummyToken,
      );

      expect(
        () => client.embedText('test'),
        throwsA(isA<VertexAiAuthException>()),
      );
    });

    test('testConnection returns true on successful 200 ping', () async {
      final client = VertexAiClient(
        httpClient: MockHttpClient((req) async {
          return http.Response(
            json.encode({
              'data': [
                {'embedding': List<double>.filled(768, 0.0)}
              ]
            }),
            200,
          );
        }),
        defaultEndpointUrl: dummyEndpoint,
        defaultToken: dummyToken,
      );

      final ok = await client.testConnection();
      expect(ok, isTrue);
    });

    test('testConnection returns false on HTTP error', () async {
      final client = VertexAiClient(
        httpClient: MockHttpClient((req) async {
          return http.Response('Server Error', 500);
        }),
        defaultEndpointUrl: dummyEndpoint,
        defaultToken: dummyToken,
      );

      final ok = await client.testConnection();
      expect(ok, isFalse);
    });
  });
}
