import 'dart:typed_data';

/// An abstract service that generates a composite try-on image by blending
/// a user's image with a product image.
abstract class TryItOnService {
  /// Returns (imageBytes, gcsUrl). gcsUrl is non-null when the backend
  /// persisted the result to GCS and can be referenced in future calls.
  Future<(Uint8List?, String?)> generateTryOnImage(
    Uint8List userImageBytes,
    Uint8List productImageBytes,
  );
}
