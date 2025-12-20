// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package fog

import (
	"math"
	"testing"
)

func TestCountWords(t *testing.T) {
	testCases := []struct {
		name                 string
		text                 string
		expectedWords        int
		expectedComplexWords int
	}{
		{
			name:                 "Simple case",
			text:                 "This is a sentence. This is another sentence.",
			expectedWords:        8,
			expectedComplexWords: 3, // sentence (3), another (3), sentence (3)
		},
		{
			name:                 "Empty string",
			text:                 "",
			expectedWords:        0,
			expectedComplexWords: 0,
		},
		{
			name:                 "Text with no words",
			text:                 "...",
			expectedWords:        0,
			expectedComplexWords: 0,
		},
		{
			name:                 "Text with extra spaces",
			text:                 "  leading and trailing spaces  ",
			expectedWords:        4,
			expectedComplexWords: 0,
		},
		{
			name:                 "With complex words",
			text:                 "This is a difficult and complicated sentence.",
			expectedWords:        7,
			expectedComplexWords: 3, // difficult (3), complicated (4), sentence (3)
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			words, complexWords := CountWords(tc.text)
			if words != tc.expectedWords {
				t.Errorf("expected %d words, got %d", tc.expectedWords, words)
			}
			if complexWords != tc.expectedComplexWords {
				t.Errorf("expected %d complex words, got %d", tc.expectedComplexWords, complexWords)
			}
		})
	}
}

func TestCountSentences(t *testing.T) {
	testCases := []struct {
		name     string
		text     string
		expected int
	}{
		{
			name:     "Simple case",
			text:     "This is a sentence. This is another sentence.",
			expected: 2,
		},
		{
			name:     "Empty string",
			text:     "",
			expected: 0,
		},
		{
			name:     "Multiple punctuation",
			text:     "What is this? I don't know! Let's find out.",
			expected: 3,
		},
		{
			name:     "No punctuation",
			text:     "this is one long sentence",
			expected: 0,
		},
		{
			name:     "Consecutive punctuation",
			text:     "Hello... world?!",
			expected: 2,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			got := CountSentences(tc.text)
			if got != tc.expected {
				t.Errorf("expected %d, got %d", tc.expected, got)
			}
		})
	}
}

func TestIsComplexWord(t *testing.T) {
	testCases := []struct {
		word     string
		expected bool
	}{
		{"complex", false},
		{"sentence", true},
		{"difficult", true},
		{"dog", false},
		{"understanding", true},
		{"beautiful", true},
		{"requires", true},
	}

	for _, tc := range testCases {
		t.Run(tc.word, func(t *testing.T) {
			if got := IsComplexWord(tc.word); got != tc.expected {
				t.Errorf("for word '%s', expected %t but got %t", tc.word, tc.expected, got)
			}
		})
	}
}

func TestCalculateFogIndex(t *testing.T) {
	testCases := []struct {
		name          string
		text          string
		expected      float64
		expectError   bool
		expectedError string
	}{
		{
			name:        "Simple case",
			text:        "This is a sentence. This is another sentence.",
			expected:    16.6,
			expectError: false,
		},
		{
			name:          "Empty string",
			text:          "",
			expected:      0.0,
			expectError:   true,
			expectedError: "text does not contain any words",
		},
		{
			name:        "Wikipedia example",
			text:        "The quick brown fox jumps over the lazy dog.",
			expected:    3.6,
			expectError: false,
		},
		{
			name:        "Complex example",
			text:        "Automated testing is a cornerstone of modern software development.",
			expected:    21.38,
			expectError: false,
		},
		{
			name:          "Sad path: No sentences",
			text:          "just a bunch of words",
			expected:      0.0,
			expectError:   true,
			expectedError: "text does not contain any sentences",
		},
		{
			name:          "Sad path: Only punctuation",
			text:          "!!! ?? ..",
			expected:      0.0,
			expectError:   true,
			expectedError: "text does not contain any words",
		},
		{
			name:        "Corner case: All complex words",
			text:        "Difficult complicated understanding.",
			expected:    41.2,
			expectError: false,
		},
		{
			name:        "Corner case: Text with numbers",
			text:        "123 apples and 456 oranges.",
			expected:    10.0,
			expectError: false,
		},
		{
			name:        "Corner case: Long sentence (100+ words)",
			text:        "This is an exceedingly long and convoluted sentence, meticulously crafted to test the boundaries of the Gunning Fog Index calculation, which, as we know, is a formula designed to assess the readability of a given passage of English prose by considering both the average sentence length and the percentage of complex words, a task that requires careful enumeration of both words and sentences, as well as a robust and consistent method for determining syllable counts in order to classify words as either simple or complex, thereby providing a numerical score that corresponds to the number of years of formal education a person needs to understand the text on the first reading.",
			expected:    54.49,
			expectError: false,
		},
		{
			name:        "Corner case: Long paragraph",
			text:        "This is an exceedingly long and convoluted sentence, meticulously crafted to test the boundaries of the Gunning Fog Index calculation. Which, as we know, is a formula designed to assess the readability of a given passage of English prose by considering both the average sentence length and the percentage of complex words. A task that requires careful enumeration of both words and sentences, as well as a robust and consistent method for determining syllable counts in order to classify words as either simple or complex. Thereby providing a numerical score that corresponds to the number of years of formal education a person needs to understand the text on the first reading.",
			expected:    21.19,
			expectError: false,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := CalculateFogIndex(tc.text)
			if tc.expectError {
				if err == nil {
					t.Errorf("expected an error but got none")
				}
				if err != nil && err.Error() != tc.expectedError {
					t.Errorf("expected error '%s' but got '%s'", tc.expectedError, err.Error())
				}
			} else {
				if err != nil {
					t.Errorf("did not expect an error but got: %v", err)
				}
				// Using a small tolerance for float comparison
				if math.Abs(got-tc.expected) > 1e-9 {
					t.Errorf("expected %f, got %f", tc.expected, got)
				}
			}
		})
	}
}

func TestClassifyFogIndex(t *testing.T) {
	testCases := []struct {
		name     string
		index    float64
		expected string
	}{
		{name: "Unreadable", index: 23.0, expected: FogCategoryUnreadable},
		{name: "Hard to Read", index: 20.0, expected: FogCategoryHardToRead},
		{name: "Professional", index: 15.0, expected: FogCategoryProfessional},
		{name: "General", index: 10.0, expected: FogCategoryGeneral},
		{name: "Simplistic", index: 8.0, expected: FogCategorySimplistic},
		{name: "Boundary High", index: 21.99, expected: FogCategoryHardToRead},
		{name: "Boundary Low", index: 9.0, expected: FogCategoryGeneral},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			if got := ClassifyFogIndex(tc.index); got != tc.expected {
				t.Errorf("expected %q, got %q", tc.expected, got)
			}
		})
	}
}

func TestFogResult(t *testing.T) {
	testCases := []struct {
		name           string
		text           string
		expectedResult FogResult
		expectError    bool
	}{
		{
			name: "Simple case",
			text: "This is a sentence. This is another sentence.",
			expectedResult: FogResult{
				FogIndex:               16.6,
				Classification:         FogCategoryProfessional,
				TotalWords:             8,
				TotalSentences:         2,
				AverageSentenceLength:  4.0,
				PercentageComplexWords: 37.5,
				ComplexWords:           3,
			},
			expectError: false,
		},
		{
			name: "Wikipedia example",
			text: "The quick brown fox jumps over the lazy dog.",
			expectedResult: FogResult{
				FogIndex:               3.6,
				Classification:         FogCategorySimplistic,
				TotalWords:             9,
				TotalSentences:         1,
				AverageSentenceLength:  9.0,
				PercentageComplexWords: 0.0,
				ComplexWords:           0,
			},
			expectError: false,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			totalWords, complexWords := CountWords(tc.text)
			totalSentences := CountSentences(tc.text)

			if totalWords == 0 || totalSentences == 0 {
				if !tc.expectError {
					t.Errorf("expected no error, but got one due to zero words or sentences")
				}
				return
			}

			averageSentenceLength := float64(totalWords) / float64(totalSentences)
			percentageComplexWords := 100 * (float64(complexWords) / float64(totalWords))
			index := 0.4 * (averageSentenceLength + percentageComplexWords)
			index = math.Round(index*100) / 100
			classification := ClassifyFogIndex(index)

			result := FogResult{
				FogIndex:               index,
				Classification:         classification,
				TotalWords:             totalWords,
				TotalSentences:         totalSentences,
				AverageSentenceLength:  math.Round(averageSentenceLength*100) / 100,
				PercentageComplexWords: math.Round(percentageComplexWords*100) / 100,
				ComplexWords:           complexWords,
			}

			if math.Abs(result.FogIndex-tc.expectedResult.FogIndex) > 1e-9 {
				t.Errorf("expected FogIndex %f, got %f", tc.expectedResult.FogIndex, result.FogIndex)
			}
			if result.Classification != tc.expectedResult.Classification {
				t.Errorf("expected Classification %q, got %q", tc.expectedResult.Classification, result.Classification)
			}
			if result.TotalWords != tc.expectedResult.TotalWords {
				t.Errorf("expected TotalWords %d, got %d", tc.expectedResult.TotalWords, result.TotalWords)
			}
			if result.TotalSentences != tc.expectedResult.TotalSentences {
				t.Errorf("expected TotalSentences %d, got %d", tc.expectedResult.TotalSentences, result.TotalSentences)
			}
			if math.Abs(result.AverageSentenceLength-tc.expectedResult.AverageSentenceLength) > 1e-9 {
				t.Errorf("expected AverageSentenceLength %f, got %f", tc.expectedResult.AverageSentenceLength, result.AverageSentenceLength)
			}
			if math.Abs(result.PercentageComplexWords-tc.expectedResult.PercentageComplexWords) > 1e-9 {
				t.Errorf("expected PercentageComplexWords %f, got %f", tc.expectedResult.PercentageComplexWords, result.PercentageComplexWords)
			}
			if result.ComplexWords != tc.expectedResult.ComplexWords {
				t.Errorf("expected ComplexWords %d, got %d", tc.expectedResult.ComplexWords, result.ComplexWords)
			}
		})
	}
}
