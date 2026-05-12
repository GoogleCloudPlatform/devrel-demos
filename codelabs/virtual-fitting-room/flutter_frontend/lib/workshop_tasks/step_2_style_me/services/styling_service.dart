import 'package:fashion_app/workshop_tasks/step_2_style_me/models/outfit.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/style_request.dart';

/// An abstract service that provides personalized outfit recommendations
/// based on user preferences and allows refining them via feedback.
abstract class StylingService {
  Future<List<Outfit>> getStyleSuggestions(StyleRequest request);
  Future<List<Outfit>> refineWithFeedback(String feedback);
}
