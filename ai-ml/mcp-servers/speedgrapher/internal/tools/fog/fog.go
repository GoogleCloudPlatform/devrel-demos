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
	"context"
	"fmt"
	"math"
	"regexp"
	"strings"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const (
	FogCategoryUnreadable   = "Unreadable: Likely incomprehensible to most readers."
	FogCategoryHardToRead   = "Hard to Read: Requires significant effort, even for experts."
	FogCategoryProfessional = "Professional Audiences: Best for readers with specialized knowledge."
	FogCategoryGeneral      = "General Audiences: Clear and accessible for most readers."
	FogCategorySimplistic   = "Simplistic: May be perceived as childish or overly simple."
)

// Register registers the fog tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:        "fog",
		Description: "Calculates the Gunning Fog Index to estimate the readability of an English text. Lower scores indicate easier reading.",
	}, fogHandler)
}

// FogParams defines the input parameters for the fog tool.
type FogParams struct {
	Text string `json:"text" jsonschema:"The text to analyze for readability. Must contain at least one sentence."`
}

// FogResult defines the structured output for the fog tool.
type FogResult struct {
	FogIndex                float64 `json:"fog_index"`
	Classification          string  `json:"classification"`
	TotalWords              int     `json:"total_words"`
	TotalSentences          int     `json:"total_sentences"`
	AverageSentenceLength   float64 `json:"average_sentence_length"`
	PercentageComplexWords  float64 `json:"percentage_complex_words"`
	ComplexWords            int     `json:"complex_words"`
}

func fogHandler(_ context.Context, _ *mcp.CallToolRequest, input FogParams) (*mcp.CallToolResult, *FogResult, error) {
	text := input.Text
	if text == "" {
		return nil, nil, newError("text cannot be empty")
	}

	totalWords, complexWords := CountWords(text)
	totalSentences := CountSentences(text)

	if totalWords == 0 {
		return nil, nil, newError("text does not contain any words")
	}
	if totalSentences == 0 {
		return nil, nil, newError("text does not contain any sentences")
	}

	averageSentenceLength := float64(totalWords) / float64(totalSentences)
	percentageComplexWords := 100 * (float64(complexWords) / float64(totalWords))

	index := 0.4 * (averageSentenceLength + percentageComplexWords)
	index = math.Round(index*100) / 100

	classification := ClassifyFogIndex(index)

	result := &FogResult{
		FogIndex:                index,
		Classification:          classification,
		TotalWords:              totalWords,
		TotalSentences:          totalSentences,
		AverageSentenceLength:   math.Round(averageSentenceLength*100) / 100,
		PercentageComplexWords:  math.Round(percentageComplexWords*100) / 100,
		ComplexWords:            complexWords,
	}

	return nil, result, nil
}

func newError(format string, a ...any) error {
	return fmt.Errorf(format, a...)
}

// CountWords counts the number of words and complex words in a given text.
// It removes all punctuation and then counts words based on spaces.
func CountWords(text string) (int, int) {
	// remove all punctuation
	cleanText := regexp.MustCompile(`[[:punct:]]`).ReplaceAllString(text, "")
	words := strings.Fields(cleanText)

	complexWordCount := 0
	for _, word := range words {
		if IsComplexWord(word) {
			complexWordCount++
		}
	}

	return len(words), complexWordCount
}

// CountSentences counts the number of sentences in a given text.
// It counts sentences by looking for sentence-ending punctuation (. ! ?).
// This is a simplistic approach and may not be accurate for all cases (e.g., abbreviations).
func CountSentences(text string) int {
	// This regex counts sentences by looking for sentence-ending punctuation.
	// It's a simple approach and might not be perfect for all cases.
	re := regexp.MustCompile(`[.!?]+`)
	sentences := re.FindAllString(text, -1)
	return len(sentences)
}

// IsComplexWord determines if a word is "complex" by checking if it has three or more syllables.
// This implementation does not exclude proper nouns, familiar jargon, or compound words.
func IsComplexWord(word string) bool {
	return countSyllables(word) >= 3
}

// CalculateFogIndex calculates the Gunning Fog Index for a given text, rounded to two decimal places.
func CalculateFogIndex(text string) (float64, error) {
	totalWords, complexWords := CountWords(text)
	totalSentences := CountSentences(text)

	if totalWords == 0 {
		return 0.0, newError("text does not contain any words")
	}
	if totalSentences == 0 {
		return 0.0, newError("text does not contain any sentences")
	}

	averageSentenceLength := float64(totalWords) / float64(totalSentences)
	percentageComplexWords := 100 * (float64(complexWords) / float64(totalWords))

	index := 0.4 * (averageSentenceLength + percentageComplexWords)
	return math.Round(index*100) / 100, nil
}

// ClassifyFogIndex classifies the Gunning Fog Index into a readability category.
func ClassifyFogIndex(index float64) string {
	switch {
	case index >= 22:
		return FogCategoryUnreadable
	case index >= 18:
		return FogCategoryHardToRead
	case index >= 13:
		return FogCategoryProfessional
	case index >= 9:
		return FogCategoryGeneral
	default:
		return FogCategorySimplistic
	}
}
