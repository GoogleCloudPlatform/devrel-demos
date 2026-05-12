// Removed dart:io import
import 'package:flutter/foundation.dart';
import 'package:fashion_app/core_app/utils/image_utils.dart';
import 'package:fashion_app/workshop_tasks/step_1_try_it_on/services/try_it_on_service.dart';
import 'package:fashion_app/core_app/models/product.dart';
import 'package:fashion_app/core_app/services/mock/mock_data_service.dart';

enum TryOnState { initial, imagePicked, generating, success, error }

// We use `ChangeNotifier` to turn this class into a reactive state container.
// Whenever the internal data changes (like `_state` or `_userImageBytes`),
// we call `notifyListeners()` to tell Flutter to automatically rebuild
// any Widget in the UI that is listening to this provider.
class TryItOnProvider with ChangeNotifier {
  // We use dependency injection (DI) here. Instead of hard-coding the ImagePicker
  // logic inside this class, we inject a generic function. This makes the class
  // incredibly easy to test (since we can just inject a dummy function that returns mock bytes)
  // and decouples the Provider from specific Flutter hardware plugins.
  final Future<Uint8List?> Function({bool fromCamera}) _imagePickerPlugin;

  // Similarly, the AIService is injected so we can swap between Firebase, GenKit,
  // or mock ADK servers without changing any business logic in this file.
  final TryItOnService _aiService;

  TryOnState _state = TryOnState.initial;
  Uint8List? _userImageBytes;
  Uint8List? _generatedImage;
  String? _errorMessage;
  int _selectedProductIndex = 0;
  bool _wasLastGenerationCached = false;
  String? _fittingGcsUrl;
  final Map<String, Uint8List> _sessionCache = {};

  final List<Product> _products = MockDataService.pick(4);

  TryItOnProvider({
    required TryItOnService aiService,
    Future<Uint8List?> Function({bool fromCamera})? imagePickerPlugin,
  }) : _aiService = aiService,
       _imagePickerPlugin = imagePickerPlugin ?? ImageUtils.pickImageBytes;

  // --- Public Getters ---
  // In Dart, variables starting with an underscore (e.g., `_state`) are strictly private
  // to this file. We do this to prevent UI code from accidentally overwriting our state
  // directly. Instead, we expose them safely as read-only getters down below.
  TryOnState get state => _state;
  Uint8List? get userImageBytes => _userImageBytes;
  Uint8List? get generatedImage => _generatedImage;
  String? get errorMessage => _errorMessage;
  int get selectedProductIndex => _selectedProductIndex;
  List<Product> get products => _products;
  bool get wasLastGenerationCached => _wasLastGenerationCached;
  bool get isGenerating => _state == TryOnState.generating;
  String? get fittingGcsUrl => _fittingGcsUrl;
  Product? get selectedProduct =>
      _products.isNotEmpty ? _products[_selectedProductIndex] : null;

  void initializeWithProduct(Product? product) {
    if (product == null) return;

    _products.removeWhere((p) => p.id == product.id);
    _products.insert(0, product);

    _selectedProductIndex = 0;

    // The most important part of state management! This broadcasts a notification
    // to the UI tree, telling any Widget watching this provider to redraw itself.
    notifyListeners();
  }

  void setSelectedProductIndex(int index) {
    _selectedProductIndex = index;
    notifyListeners();
  }

  // --- State Transition Helpers ---
  // Rather than scattering `_state = TryOnState.something`, `_errorMessage = null`,
  // and `notifyListeners()` all over the class, we consolidate state transitions
  // into these single-responsibility private helper methods. This prevents bugs where
  // a developer might forget to clear an error message when moving to a success state.

  void _setImagePicked(Uint8List bytes) {
    _userImageBytes = bytes;
    _generatedImage = null;
    _errorMessage = null;
    _state = TryOnState.imagePicked;
    notifyListeners();
  }

  void _setSuccess(Uint8List image, {bool isCached = false}) {
    _generatedImage = image;
    _errorMessage = null;
    _wasLastGenerationCached = isCached;
    _state = TryOnState.success;
    notifyListeners();
  }

  void _setGenerating() {
    _state = TryOnState.generating;
    _errorMessage = null;
    _wasLastGenerationCached = false;
    notifyListeners();
  }

  void _setError(String message) {
    _errorMessage = message;
    _state = TryOnState.error;
    notifyListeners();
  }

  Future<bool> pickImage({bool fromCamera = false}) async {
    try {
      final pickedBytes = await _imagePickerPlugin(fromCamera: fromCamera);

      if (pickedBytes != null) {
        _setImagePicked(pickedBytes);
        return true;
      }
    } catch (e) {
      debugPrint('Error picking image: $e');
      _setError('Error picking image');
    }
    return false;
  }

  Future<String?> processTryOn(
    String productImagePath, {
    bool pickNewImage = false,
    bool fromCamera = false,
  }) async {
    if (_userImageBytes == null || pickNewImage == true) {
      final picked = await pickImage(fromCamera: fromCamera);
      if (!picked) return 'IMAGE_PICK_CANCELLED';
    }

    return await generateTryOnImage(productImagePath);
  }

  Future<String?> generateTryOnImage(String productImagePath) async {
    // Dart Type Promotion: By assigning the nullable class variable `_userImageBytes`
    // to a local `final` variable, the Dart compiler can statically prove that it will
    // never mysteriously turn `null` halfway through the function. This allows us to
    // drop the dangerous force-unwrap bang operator (!) later down in the file.
    final userImageBytes = _userImageBytes;
    if (userImageBytes == null) {
      _setError('No image selected.');
      return _errorMessage;
    }

    final productUint8List = await ImageUtils.loadBytes(productImagePath);

    final cachedImage = ImageUtils.getCachedImage(
      _sessionCache,
      userImageBytes,
      productUint8List,
    );

    if (cachedImage != null) {
      _setSuccess(cachedImage, isCached: true);
      return null;
    }

    // If we've reached this code, there is no cache hit, so we must make a network
    // request and generate a try on image. Update the TryItOnProvider state to
    // generating, which should trigger a loading state in the UI.
    _setGenerating();

    try {
      final (generatedBytes, gcsUrl) = await _aiService.generateTryOnImage(
        userImageBytes,
        productUint8List,
      );

      if (generatedBytes != null) {
        _fittingGcsUrl = gcsUrl;
        ImageUtils.cacheImage(
          _sessionCache,
          userImageBytes,
          productUint8List,
          generatedBytes,
        );
        _setSuccess(generatedBytes);
      } else {
        _setError('No image generated.');
      }
    } catch (e) {
      debugPrint('Generation error: $e');
      _setError(e.toString().replaceAll('Exception: ', ''));
    }

    return _state == TryOnState.success ? null : _errorMessage;
  }
}
