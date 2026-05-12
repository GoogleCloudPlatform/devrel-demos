import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:crypto/crypto.dart';

class ImageUtils {
  static final ImagePicker _picker = ImagePicker();

  /// Loads image bytes from either a network URL or a local asset path.
  static Future<Uint8List> loadBytes(String imagePath) async {
    if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
      final response = await http.get(Uri.parse(imagePath));
      return response.bodyBytes;
    } else {
      final ByteData byteData = await rootBundle.load(imagePath);
      return byteData.buffer.asUint8List();
    }
  }

  /// Picks an image from the device camera or gallery and returns its bytes.
  static Future<Uint8List?> pickImageBytes({bool fromCamera = false}) async {
    final pickedFile = await _picker.pickImage(
      source: fromCamera ? ImageSource.camera : ImageSource.gallery,
      maxWidth: 1920,
      maxHeight: 2400,
      imageQuality: 85,
    );
    return pickedFile?.readAsBytes();
  }

  /// Generates an MD5 hash cache key from the combined bytes of user and product images.
  static String generateCacheKey(Uint8List userBytes, Uint8List productBytes) {
    final cacheBytes = [...userBytes, ...productBytes];
    return md5.convert(cacheBytes).toString();
  }

  /// Checks the provided cache map for an existing generated image.
  static Uint8List? getCachedImage(
    Map<String, Uint8List> cache,
    Uint8List userBytes,
    Uint8List productBytes,
  ) {
    final key = generateCacheKey(userBytes, productBytes);
    return cache[key];
  }

  /// Saves the generated image into the provided cache map.
  static void cacheImage(
    Map<String, Uint8List> cache,
    Uint8List userBytes,
    Uint8List productBytes,
    Uint8List generatedImage,
  ) {
    final key = generateCacheKey(userBytes, productBytes);
    cache[key] = generatedImage;
  }
}
