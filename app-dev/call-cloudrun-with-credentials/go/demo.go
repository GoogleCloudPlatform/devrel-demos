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

// getIDToken detects the ADC type and chooses the correct flow.
func getIDToken(ctx context.Context, audience string) (string, error) {
	creds, err := idtoken.NewCredentials(&idtoken.Options{
		Audience: audience,
	})
	if err != nil {
		return "", fmt.Errorf("failed to detect default credentials: %w", err)
	}

	// 2. Check if the detected credentials are "Impersonated Service Account"
	// We check the raw JSON. If it's a metadata server cred, JSON will be empty (safe).
	var rawCreds map[string]interface{}
	var isImpersonated bool

	if len(creds.JSON()) > 0 {
		if err := json.Unmarshal(creds.JSON(), &rawCreds); err == nil {
			if typeVal, ok := rawCreds["type"].(string); ok && typeVal == "impersonated_service_account" {
				isImpersonated = true
			}
		}
	}

	// 3. Branching Logic
	if isImpersonated {
		fmt.Println("👉 Detected Impersonated ADC. Configuring explicit impersonation...")
		return getTokenViaImpersonation(ctx, audience, rawCreds)
	}

	token, err := creds.Token(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to retrieve token: %w", err)
	}
	return token.Value, nil
}

// getTokenViaImpersonation manually handles the double-hop auth.
func getTokenViaImpersonation(ctx context.Context, audience string, rawCreds map[string]interface{}) (string, error) {
	// A. extract target service account email
	impURL, ok := rawCreds["service_account_impersonation_url"].(string)
	if !ok {
		return "", fmt.Errorf("malformed ADC: missing service_account_impersonation_url")
	}
	re := regexp.MustCompile(`serviceAccounts/([^:]+):`)
	matches := re.FindStringSubmatch(impURL)
	if len(matches) < 2 {
		return "", fmt.Errorf("could not extract service account email from URL")
	}
	targetSA := matches[1]
	fmt.Printf("   Target Principal: %s\n", targetSA)

	// B. Acquire base creds with the default scope
	baseCreds, err := credentials.DetectDefault(&credentials.DetectOptions{
		Scopes:           []string{"https://www.googleapis.com/auth/cloud-platform"},
	})
	if err != nil {
		return "", fmt.Errorf("failed to load base credentials: %w", err)
	}

	// C. generate ID token using the base creds to impersonate the target
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

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	fmt.Printf("✅ Response: %s\n", string(body))
	return nil
}