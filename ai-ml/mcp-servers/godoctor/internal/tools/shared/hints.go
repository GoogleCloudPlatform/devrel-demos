package shared

import (
	"fmt"
	"regexp"
	"strings"

	"golang.org/x/tools/go/packages"
)

var (
	// undefinedPkg match: "undefined: pkgname.Symbol"
	undefinedPkgRe = regexp.MustCompile(`undefined:\s+([a-zA-Z0-9_]+)\.`)
	// importError match: "could not import github.com/foo/bar" or "package github.com/foo/bar is not in GOROOT"
	importErrorRe = regexp.MustCompile(`(?:could not import|package)\s+([a-zA-Z0-9_./-]+)`)
)

// GetDocHint checks a list of package errors for API usage issues and returns a generic doc hint.
func GetDocHint(errs []packages.Error) string {
	for _, e := range errs {
		if hint := generateHint(e.Msg); hint != "" {
			return hint
		}
	}
	return ""
}

// GetDocHintFromOutput checks a raw output string for API usage issues and returns a generic doc hint.
func GetDocHintFromOutput(output string) string {
	return generateHint(output)
}

func generateHint(msg string) string {
	// Check for "undefined: pkg.Symbol"
	if matches := undefinedPkgRe.FindStringSubmatch(msg); len(matches) > 1 {
		pkgName := matches[1]
		return fmt.Sprintf("\n\n**HINT:** usage of '%s' failed. Try calling `go_docs` on that package to see the correct API.", pkgName)
	}

	// Check for "could not import ..."
	if matches := importErrorRe.FindStringSubmatch(msg); len(matches) > 1 {
		pkgPath := matches[1]
		return fmt.Sprintf("\n\n**HINT:** import '%s' failed. Try calling `go_docs` on \"%s\" to verify the package path and exports.", pkgPath, pkgPath)
	}

	return ""
}

// CleanError strips noisy artifacts from Go compiler errors, such as empty name quotes.
func CleanError(msg string) string {
	// Remove the literal '("" )' or ': ""' artifacts that confuse agents.
	msg = strings.ReplaceAll(msg, `(invalid package name: "")`, `(invalid package name)`)
	msg = strings.ReplaceAll(msg, `invalid package name: ""`, `invalid package name`)
	return msg
}
