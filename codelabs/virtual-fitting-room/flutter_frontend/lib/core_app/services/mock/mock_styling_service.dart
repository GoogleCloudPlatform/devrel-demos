import 'package:fashion_app/workshop_tasks/step_2_style_me/models/outfit.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/models/style_request.dart';
import 'package:fashion_app/core_app/services/mock/mock_data_service.dart';
import 'package:fashion_app/workshop_tasks/step_2_style_me/services/styling_service.dart';

class MockStylingService implements StylingService {
  @override
  Future<List<Outfit>> getStyleSuggestions(StyleRequest request) async {
    // Simulate network delay
    await Future.delayed(const Duration(seconds: 2));
    return MockDataService.getMockOutfits();
  }

  @override
  Future<List<Outfit>> refineWithFeedback(String feedback) async {
    return MockDataService.getAlternativeOutfits(feedback);
  }
}
