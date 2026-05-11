package tools

import (
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"

	"cloud.google.com/go/storage"
	"google.golang.org/adk/tool"
	"google.golang.org/adk/tool/functiontool"
	"google.golang.org/genai"
)

func NewImageTool() (tool.Tool, error) {
	imageTool, err := functiontool.New(functiontool.Config{
		Name:        "getProductImage",
		Description: "get the URL for a product image",
	}, GetProductImage)
	return imageTool, err
}

type GetProductImageArgs struct {
	ImageName string `json:"image_name"`
}

type GetProductImageResult struct {
	Image string `json:"image" jsonschema:"image data"`
}

func GetProductImage(ctx tool.Context, args GetProductImageArgs) (GetProductImageResult, error) {
	// first check for an artifact.
	_, err := ctx.Artifacts().Load(ctx, args.ImageName)
	if err == nil {
		slog.Info("Found artifact", "a", args.ImageName)
		return GetProductImageResult{Image: args.ImageName}, nil
	}
	// Then look in our GCS bucket
	bucket := os.Getenv("GCS_BUCKET")
	if bucket == "" {
		return GetProductImageResult{}, fmt.Errorf("GCS_BUCKET environment variable not set")
	}

	client, err := storage.NewClient(ctx)
	if err != nil {
		return GetProductImageResult{}, fmt.Errorf("failed to create storage client: %w", err)
	}
	defer client.Close()

	rc, err := client.Bucket(bucket).Object("catalog-assets/images/" + args.ImageName).NewReader(ctx)
	if err != nil {
		slog.Warn("failed to open image from GCS, falling back to local file", "err", err)
		localData, err := os.ReadFile(fmt.Sprintf("../flutter_frontend/assets/images/%s", args.ImageName))
		if err != nil {
			return GetProductImageResult{}, fmt.Errorf("failed to open image from local: %w", err)
		}
		mimeType := http.DetectContentType(localData)
		ctx.Artifacts().Save(ctx, args.ImageName, &genai.Part{InlineData: &genai.Blob{
			Data:        localData,
			DisplayName: args.ImageName,
			MIMEType:    mimeType,
		}})
		return GetProductImageResult{Image: args.ImageName}, nil
	}
	defer rc.Close()

	data, err := io.ReadAll(rc)
	if err != nil {
		return GetProductImageResult{}, fmt.Errorf("failed to read image: %w", err)
	}
	mimeType := http.DetectContentType(data)
	ctx.Artifacts().Save(ctx, args.ImageName, &genai.Part{InlineData: &genai.Blob{
		Data:        data,
		DisplayName: args.ImageName,
		MIMEType:    mimeType,
	}})

	return GetProductImageResult{Image: args.ImageName}, nil
}
