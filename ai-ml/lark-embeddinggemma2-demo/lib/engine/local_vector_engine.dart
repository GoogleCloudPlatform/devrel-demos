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

import 'dart:math' as math;
import '../models/memory_item.dart';

class LocalVectorEngine {
  /// Computes the dot product between two vectors.
  /// For unit-normalized vectors (such as EmbeddingGemma 2 outputs),
  /// the dot product is mathematically equivalent to cosine similarity.
  static double dotProduct(List<double> a, List<double> b) {
    final len = math.min(a.length, b.length);
    if (len == 0) return 0.0;

    double sum = 0.0;
    for (int i = 0; i < len; i++) {
      sum += a[i] * b[i];
    }
    return sum;
  }

  /// Truncates an embedding vector using Matryoshka Representation Learning (MRL)
  /// and re-normalizes the truncated slice to unit length (L2 norm = 1.0).
  static List<double> truncateMrl(List<double> vector, int targetDim) {
    if (targetDim >= vector.length || targetDim <= 0) {
      return vector;
    }

    final slice = vector.sublist(0, targetDim);
    double sumSq = 0.0;
    for (int i = 0; i < targetDim; i++) {
      sumSq += slice[i] * slice[i];
    }

    final norm = math.sqrt(sumSq);
    if (norm == 0.0) return slice;

    final result = List<double>.filled(targetDim, 0.0);
    for (int i = 0; i < targetDim; i++) {
      result[i] = slice[i] / norm;
    }
    return result;
  }

  /// Minimum floor to consider a match confident in EmbeddingGemma 2.
  static const double defaultConfidenceThreshold = 0.69;

  /// Strong confidence threshold above which adjacent matches are always kept
  /// as long as they are within [maxDropFromTop] of the best match.
  static const double strongConfidenceThreshold = 0.75;

  /// Maximum allowed similarity drop from the #1 match before cutting off results.
  static const double maxDropFromTop = 0.12;

  /// Maximum allowed step drop between consecutive static items when below [strongConfidenceThreshold].
  static const double maxStepDrop = 0.031;

  /// Maximum allowed step drop into temporal multi-modal items (video, voiceMemo),
  /// whose unit embedding vectors encode multiple scenes or song verses.
  static const double maxTemporalStepDrop = 0.075;

  /// Ranks memories purely by EmbeddingGemma 2 cosine similarity to the query vector.
  /// Optionally filters by media type, truncates to MRL dimension,
  /// and applies a confidence threshold plus adaptive drop-off cutoff.
  static List<ScoredMemory> rank(
    List<double> queryVector,
    List<MemoryItem> items, {
    MediaType? filterType,
    int dimension = 768,
    double minScore = -1.0,
    bool adaptiveCutoff = true,
  }) {
    if (queryVector.isEmpty || items.isEmpty) {
      return const [];
    }

    final effectiveQuery = (dimension < queryVector.length)
        ? truncateMrl(queryVector, dimension)
        : queryVector;

    final scored = <ScoredMemory>[];

    for (final item in items) {
      if (filterType != null && item.type != filterType) {
        continue;
      }

      final effectiveItem = (dimension < item.embedding.length)
          ? truncateMrl(item.embedding, dimension)
          : item.embedding;

      final rawScore = dotProduct(effectiveQuery, effectiveItem);

      if (rawScore < minScore) {
        continue;
      }

      scored.add(ScoredMemory(
        item: item,
        score: rawScore,
      ));
    }

    // Sort in descending order of EmbeddingGemma 2 similarity score
    scored.sort((a, b) => b.score.compareTo(a.score));

    // When filtering by the default confidence floor, also stop at the natural
    // similarity cliff for items below strongConfidenceThreshold (0.75) so
    // partial matches for multi-part queries are excluded while all relevant
    // items (including multi-scene videos and multi-verse songs) for
    // single-concept queries are preserved.
    if (adaptiveCutoff &&
        minScore >= defaultConfidenceThreshold &&
        scored.length > 1) {
      final topScore = scored.first.score;
      final kept = <ScoredMemory>[scored.first];
      for (int i = 1; i < scored.length; i++) {
        final cur = scored[i].score;
        final prev = scored[i - 1].score;
        if (cur < strongConfidenceThreshold) {
          final itemType = scored[i].item.type;
          final isTemporalMedia =
              itemType == MediaType.video || itemType == MediaType.voiceMemo;
          final allowedStepDrop =
              isTemporalMedia ? maxTemporalStepDrop : maxStepDrop;
          if ((topScore - cur) > maxDropFromTop ||
              (prev - cur) > allowedStepDrop) {
            break;
          }
        }
        kept.add(scored[i]);
      }
      return kept;
    }

    return scored;
  }
}
