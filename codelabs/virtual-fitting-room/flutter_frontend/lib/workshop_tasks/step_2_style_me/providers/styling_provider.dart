import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/outfit.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/style_request.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/services/styling_service.dart';

enum StylingState { initial, loading, success, error }

/// The [StylingProvider] manages the state for the "Style Me" / AI Stylist feature.
///
/// WHY THIS EXISTS:
/// This acts as the centralized ViewModel for the entire outfit recommendation flow.
/// When the user asks for a new outfit (via [getStyleSuggestions]) or provides chat feedback
/// on an existing outfit (via [refineWithFeedback]), this provider handles talking to the
/// [StylingService].
///
/// The UI (like the StylingScreen or Chat UI) simply listens to this provider. When the user taps
/// "Style Me", the UI calls the method, and the provider automatically switches to `loading` state,
/// causing the UI to show a loading spinner. When the AI responds, the state flips to `success`,
/// the [_outfits] list is populated, and the UI automatically rebuilds to show the Outfit cards.
class StylingProvider with ChangeNotifier {
  final StylingService _stylingService;

  StylingState _state = StylingState.initial;
  List<Outfit> _outfits = [];
  String? _errorMessage;
  StyleRequest? _currentRequest;

  StylingProvider({required StylingService stylingService})
    : _stylingService = stylingService;

  StylingState get state => _state;
  List<Outfit> get outfits => _outfits;
  String? get errorMessage => _errorMessage;
  StyleRequest? get currentRequest => _currentRequest;

  bool get isLoading => _state == StylingState.loading;
  bool get hasError => _state == StylingState.error;
  bool get isSuccess => _state == StylingState.success;

  // --- Private State Setters ---
  // Centralized methods to transition between our styling states (loading the AI response,
  // successfully showing outfits, or showing an error).
  // Using private methods ensures we always call `notifyListeners()` when the UI needs an update.

  void _setLoading() {
    _state = StylingState.loading;
    _errorMessage = null;
    notifyListeners();
  }

  void _setSuccess(List<Outfit> newOutfits) {
    _state = StylingState.success;
    _outfits = newOutfits;
    _errorMessage = null;
    notifyListeners();
  }

  void _setError(String message) {
    _state = StylingState.error;
    _errorMessage = message;
    notifyListeners();
  }

  /// Sends the initial [StyleRequest] (context, occasion, vibe) to the AI stylist.
  /// Returns [true] if outfits were generated successfully, or [false] if it fails.
  Future<bool> getStyleSuggestions(StyleRequest request) async {
    // Prevent the user from spamming the "Style Me" button while the AI is already "thinking".
    if (_state == StylingState.loading) return false;

    _currentRequest = request;
    _setLoading();
    try {
      final suggestions = await _stylingService.getStyleSuggestions(request);
      _setSuccess(suggestions);
      return true;
    } on TimeoutException {
      _setError('The styling is taking too long to respond. Please try again.');
    } on FormatException {
      _setError('We received bad data from the server.');
    } catch (e) {
      debugPrint('Unknown error getting style suggestions: $e');
      _setError('Something went wrong. Please try again.');
    }
    return false;
  }

  /// Sends conversational chat [feedback] (e.g., "make it more casual") back to the AI
  /// to refine the previously generated outfits.
  /// Returns [true] if the new outfits were generated, or [false] if it fails.
  Future<bool> refineWithFeedback(String feedback) async {
    // Prevent the user from sending multiple chat messages while the AI is still processing the last one.
    if (_state == StylingState.loading) return false;

    _setLoading();
    try {
      final suggestions = await _stylingService.refineWithFeedback(feedback);
      _setSuccess(suggestions);
      return true;
    } on TimeoutException {
      _setError('The styling is taking too long to respond. Please try again.');
    } on FormatException {
      _setError('We received bad data from the server.');
    } catch (e) {
      debugPrint('Unknown error refining style suggestions: $e');
      _setError('Something went wrong. Please try again.');
    }
    return false;
  }
}
