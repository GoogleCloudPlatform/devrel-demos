package stylist

import (
	"testing"
)

func TestExtractProductIDs_RawJSON(t *testing.T) {
	input := `{
		"outfits": [
			{
				"commentary": "Great look",
				"image": "img1",
				"products": [
					{"id": "id_bomber_jacket", "title": "Bomber Jacket", "subtitle": "Classic", "price": 150, "image": "bomber_jacket.png"},
					{"id": "id_flutter_hat", "title": "Flutter Hat", "subtitle": "Hat", "price": 25, "image": "flutter_hat.png"}
				]
			},
			{
				"commentary": "Casual vibe",
				"image": "img2",
				"products": [
					{"id": "id_hightop", "title": "High Top", "subtitle": "Shoes", "price": 95, "image": "hightop.png"},
					{"id": "id_plaid_shirt", "title": "Plaid Shirt", "subtitle": "Shirt", "price": 45, "image": "plaid_shirt.png"}
				]
			},
			{
				"commentary": "Evening style",
				"image": "img3",
				"products": [
					{"id": "id_product_1", "title": "Red Dress", "subtitle": "Dress", "price": 45, "image": "product_1.png"},
					{"id": "id_bomber_jacket", "title": "Bomber Jacket", "subtitle": "Classic", "price": 150, "image": "bomber_jacket.png"}
				]
			}
		]
	}`

	ids := extractProductIDs(input)

	// Should have 5 unique IDs (bomber_jacket appears twice but deduped)
	if len(ids) != 5 {
		t.Errorf("expected 5 unique product IDs, got %d: %v", len(ids), ids)
	}

	expected := map[string]bool{
		"id_bomber_jacket": true,
		"id_flutter_hat":   true,
		"id_hightop":       true,
		"id_plaid_shirt":   true,
		"id_product_1":     true,
	}
	for _, id := range ids {
		if !expected[id] {
			t.Errorf("unexpected product ID: %s", id)
		}
	}
}

func TestExtractProductIDs_MarkdownFenced(t *testing.T) {
	input := "Here are your outfits:\n```json\n" + `{
		"outfits": [
			{
				"commentary": "Test",
				"products": [
					{"id": "id_style_1", "title": "Dress", "subtitle": "Sub", "price": 82, "image": "prod1_var1.png"}
				]
			}
		]
	}` + "\n```\n"

	ids := extractProductIDs(input)
	if len(ids) != 1 || ids[0] != "id_style_1" {
		t.Errorf("expected [id_style_1], got %v", ids)
	}
}

func TestExtractProductIDs_NoJSON(t *testing.T) {
	ids := extractProductIDs("This is just plain text with no JSON.")
	if len(ids) != 0 {
		t.Errorf("expected no product IDs, got %v", ids)
	}
}

func TestExtractProductIDs_EmptyOutfits(t *testing.T) {
	input := `{"outfits": []}`
	ids := extractProductIDs(input)
	if len(ids) != 0 {
		t.Errorf("expected no product IDs, got %v", ids)
	}
}

func TestExtractProductIDs_EmptyProducts(t *testing.T) {
	input := `{"outfits": [{"commentary": "test", "products": []}]}`
	ids := extractProductIDs(input)
	if len(ids) != 0 {
		t.Errorf("expected no product IDs, got %v", ids)
	}
}
