package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"regexp"
	"time"

	"cloud.google.com/go/auth/credentials"
	"cloud.google.com/go/auth/credentials/idtoken"
	"cloud.google.com/go/auth/credentials/impersonate"
)

func main() {
	// 1. Parse Command Line Arguments
	urlPtr := flag.String("url", "", "Cloud Run service URL (required)")
	flag.Parse()

	if *urlPtr == "" {
		fmt.Fprintln(os.Stderr, "Error: --url argument is required")
		flag.PrintDefaults()
		os.Exit(1)
	}
	serviceURL := *urlPtr

	// 2. Setup Context
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// 3. Acquire ID Token
	tokenValue, err := getIDToken(ctx, serviceURL)
	if err != nil {
		log.Fatalf("❌ Failed to acquire ID token: %v", err)
	}
	fmt.Println("🎉 ID token acquired successfully.")

	// 4. Make Authenticated Call
	if err := callService(ctx, serviceURL, tokenValue); err != nil {
		log.Fatalf("❌ Service call failed: %v", err)
	}
	fmt.Println("🎉 Service call completed successfully.")
}

func getIDToken(ctx context.Context, audience string) (string, error) {
	creds, err := idtoken.NewCredentials(&idtoken.Options{
		Audience: audience,
	})
	if err != nil {
		return "", fmt.Errorf("failed to detect default credentials: %w", err)
	}

	// Option D: Detect Impersonated Credentials
	var rawCreds map[string]interface{}

	if len(creds.JSON()) > 0 {
		if err := json.Unmarshal(creds.JSON(), &rawCreds); err != nil {
			return "", err
		}
		if typeVal, ok := rawCreds["type"].(string); ok && typeVal == "impersonated_service_account" {
			return getTokenViaImpersonation(ctx, audience, rawCreds)
		}
	}

	// Options A, B and C: Metadata Server, User or Service Account Credentials
	token, err := creds.Token(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to retrieve token: %w", err)
	}
	return token.Value, nil
}

var serviceAccountNameRegex = regexp.MustCompile(`serviceAccounts/([^:]+):`)

func getTokenViaImpersonation(ctx context.Context, audience string, rawCreds map[string]interface{}) (string, error) {
	// 1. extract target service account email
	impURL, ok := rawCreds["service_account_impersonation_url"].(string)
	if !ok {
		return "", fmt.Errorf("malformed ADC: missing service_account_impersonation_url")
	}
	matches := serviceAccountNameRegex.FindStringSubmatch(impURL)
	if len(matches) < 2 {
		return "", fmt.Errorf("could not extract service account email from URL")
	}
	targetSA := matches[1]
	fmt.Printf("   Target Principal: %s\n", targetSA)

	// 2. Acquire base creds with the default scope
	baseCreds, err := credentials.DetectDefault(&credentials.DetectOptions{
		Scopes:           []string{"https://www.googleapis.com/auth/cloud-platform"},
	})
	if err != nil {
		return "", fmt.Errorf("failed to load base credentials: %w", err)
	}

	// 3. generate ID token using the base creds to impersonate the target
	impCreds, err := impersonate.NewIDTokenCredentials(&impersonate.IDTokenOptions{
		Audience:        audience,
		TargetPrincipal: targetSA,
		Credentials:     baseCreds,
	})
	if err != nil {
		return "", fmt.Errorf("failed to create impersonated credentials: %w", err)
	}

	token, err := impCreds.Token(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to obtain impersonated token: %w", err)
	}
	
	return token.Value, nil
}

func callService(ctx context.Context, url, token string) error {
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	fmt.Printf("🎉 --- Response Content (First 200 chars) ---\n")
	fmt.Printf("%s\n", string(body[:200]))
	return nil
}