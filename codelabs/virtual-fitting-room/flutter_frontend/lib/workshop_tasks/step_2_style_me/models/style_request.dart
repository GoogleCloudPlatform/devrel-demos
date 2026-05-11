import 'dart:typed_data';

class StyleRequest {
  final String location;
  final String occasion;
  final String notes;
  final Uint8List? userImageData;

  /// GCS URI (gs://...) of the user's last fitting-room result.
  /// When present it is passed to the stylist so fitting_tool can reuse it
  /// as the base image, preserving the user's actual appearance.
  final String? gcsUserImageUrl;

  /// The product the user already tried on — the stylist will include it
  /// in every generated outfit.
  final String? selectedProductId;
  final String? selectedProductTitle;

  const StyleRequest({
    required this.location,
    required this.occasion,
    required this.notes,
    this.userImageData,
    this.gcsUserImageUrl,
    this.selectedProductId,
    this.selectedProductTitle,
  });

  Map<String, dynamic> toJson() {
    return {'location': location, 'occasion': occasion, 'notes': notes};
  }

  factory StyleRequest.fromJson(Map<String, dynamic> json) {
    return StyleRequest(
      location: json['location'] ?? '',
      occasion: json['occasion'] ?? '',
      notes: json['notes'] ?? '',
    );
  }
}
