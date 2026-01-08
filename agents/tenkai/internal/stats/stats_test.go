package stats

import (
	"math"
	"testing"
)

func TestMean(t *testing.T) {
	data := []float64{1, 2, 3, 4, 5}
	expected := 3.0
	if res := Mean(data); res != expected {
		t.Errorf("Expected %f, got %f", expected, res)
	}
}

func TestVariance(t *testing.T) {
	data := []float64{1, 2, 3, 4, 5}
	expected := 2.5
	if res := Variance(data); res != expected {
		t.Errorf("Expected %f, got %f", expected, res)
	}
}

func TestWelchTTest(t *testing.T) {
	// Group 1: Mean 10, SD 2
	data1 := []float64{8, 9, 10, 11, 12}
	// Group 2: Mean 20, SD 2
	data2 := []float64{18, 19, 20, 21, 22}

	p := WelchTTest(data1, data2)
	if p > 0.05 {
		t.Errorf("Expected significant p-value (<0.05), got %f", p)
	}

	// Identical groups
	p2 := WelchTTest(data1, data1)
	if p2 < 0.9 {
		t.Errorf("Expected non-significant p-value (>0.9), got %f", p2)
	}
}

func TestFisherExactTest(t *testing.T) {
	// Very significant difference
	// A: 10/10 successes
	// C: 0/10 successes
	p := FisherExactTest(10, 0, 0, 10)
	if p > 0.001 {
		t.Errorf("Expected very significant p-value (<0.001), got %f", p)
	}

	// No difference
	// A: 5/10 successes
	// C: 5/10 successes
	p2 := FisherExactTest(5, 5, 5, 5)
	if p2 < 0.9 {
		t.Errorf("Expected non-significant p-value (>0.9), got %f", p2)
	}

	// Boundary case: small sample
	// A: 3/3 successes
	// C: 0/3 successes
	p3 := FisherExactTest(3, 0, 0, 3)
	// For 3/3 vs 0/3, there are 20 total ways to pick 3 items out of 6.
	// Only 1 way is all 3 from group A. So P(X=3) = 1/20 = 0.05.
	// P(X=0) is also 1/20 = 0.05.
	// So two-sided p-value should be 0.10.
	if math.Abs(p3-0.1) > 0.01 {
		t.Errorf("Expected p-value around 0.1, got %f", p3)
	}
}
