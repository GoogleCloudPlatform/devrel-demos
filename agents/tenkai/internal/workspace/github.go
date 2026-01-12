package workspace

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

type githubIssue struct {
	Title string `json:"title"`
	Body  string `json:"body"`
}

func fetchGithubIssue(issueURL string) (*githubIssue, error) {
	// Parse URL: https://github.com/owner/repo/issues/number
	parts := strings.Split(issueURL, "/")
	if len(parts) < 7 {
		return nil, fmt.Errorf("invalid github issue url format")
	}
	owner := parts[3]
	repo := parts[4]
	number := parts[6]

	apiURL := fmt.Sprintf("https://api.github.com/repos/%s/%s/issues/%s", owner, repo, number)
	resp, err := http.Get(apiURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("github api returned status %d", resp.StatusCode)
	}

	var issue githubIssue
	if err := json.NewDecoder(resp.Body).Decode(&issue); err != nil {
		return nil, err
	}
	return &issue, nil
}
