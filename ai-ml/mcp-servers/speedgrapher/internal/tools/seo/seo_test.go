package seo

import (
	"strings"
	"testing"

	"github.com/PuerkitoBio/goquery"
)

func TestAnalyzeSEO(t *testing.T) {
	html := `
		<html>
			<head>
				<title>Perfect SEO Title Example For Testing Keyword</title>
				<meta name="description" content="This is a perfect meta description that is long enough to pass the check and contains the keyword we are looking for in this test case.">
				<link rel="canonical" href="https://example.com/page">
			</head>
			<body>
				<h1>Main Keyword Heading</h1>
				<p>This is some content. It needs to be long enough to pass the word count check.
				Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
				Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
				Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
				Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
				Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
				Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
				Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
				Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
				Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
				Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
				Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
				Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
				Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
				Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
				Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
				Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
				Extra words to make sure we pass the count. Extra words to make sure we pass the count.
				</p>
				<img src="image.jpg" alt="Description of image">
				<a href="/internal">Internal Link</a>
			</body>
		</html>
	`

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		t.Fatalf("Failed to parse HTML: %v", err)
	}

	result := analyzeSEO(doc, "keyword")

	if result.Score != 100 {
		t.Errorf("Expected score 100, got %d", result.Score)
		for _, check := range result.Checks {
			if check.Status != "pass" {
				t.Logf("Failed check: %s - %s", check.Name, check.Description)
			}
		}
	}

	if result.Title != "Perfect SEO Title Example For Testing Keyword" {
		t.Errorf("Expected title 'Perfect SEO Title Example For Testing Keyword', got '%s'", result.Title)
	}
}

func TestAnalyzeSEOFailures(t *testing.T) {
	html := `
		<html>
			<head>
				<title>Short</title>
			</head>
			<body>
				<h1>No Keyword</h1>
				<img src="image.jpg">
			</body>
		</html>
	`

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		t.Fatalf("Failed to parse HTML: %v", err)
	}

	result := analyzeSEO(doc, "missing")

	if result.Score >= 100 {
		t.Errorf("Expected score < 100, got %d", result.Score)
	}

	// Check specific failures
	foundTitleWarning := false
	foundH1Warning := false
	foundImgWarning := false

	for _, check := range result.Checks {
		if check.Name == "Title Tag" && check.Status != "pass" {
			foundTitleWarning = true
		}
		if check.Name == "H1 Tag" && check.Status != "pass" {
			foundH1Warning = true
		}
		if check.Name == "Image Alt Text" && check.Status != "pass" {
			foundImgWarning = true
		}
	}

	if !foundTitleWarning {
		t.Error("Expected title warning")
	}
	if !foundH1Warning {
		t.Error("Expected H1 warning")
	}
	if !foundImgWarning {
		t.Error("Expected image alt warning")
	}
}

func TestConvertHugoMarkdownToHTML(t *testing.T) {
	markdown := `---
title: "My Hugo Post Title"
description: "This is a description for the Hugo post that is long enough."
canonical: "https://example.com/hugo-post"
---

# Heading 1

This is the body content.
[Link](https://example.com)
`

	html, err := convertHugoMarkdownToHTML(markdown)
	if err != nil {
		t.Fatalf("Failed to convert markdown: %v", err)
	}

	if !strings.Contains(html, "<title>My Hugo Post Title</title>") {
		t.Error("HTML missing title from front matter")
	}
	if !strings.Contains(html, `content="This is a description for the Hugo post that is long enough."`) {
		t.Error("HTML missing description from front matter")
	}
	if !strings.Contains(html, `<h1>Heading 1</h1>`) {
		t.Error("HTML missing converted body content")
	}
}