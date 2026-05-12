package catalog

import (
	"context"
	_ "embed"
	"fmt"
	"goagents/tools"
	"os"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model/gemini"
	"google.golang.org/adk/tool"
	"google.golang.org/adk/tool/functiontool"
	"google.golang.org/genai"
	"gopkg.in/yaml.v3"
)

//go:embed instructions.md
var instructions string

type Product struct {
	ID       string   `json:"id" yaml:"id"`
	Title    string   `json:"title" yaml:"title"`
	Subtitle string   `json:"subtitle" yaml:"subtitle"`
	Price    float64  `json:"price" yaml:"price"`
	Images   []string `json:"images" yaml:"images"`
}

var catalogProducts []Product
var defaultCatalogFile = "catalog/catalog.yaml"

func loadCatalog(fn string) error {
	data, err := os.ReadFile(fn)
	if err != nil {
		return fmt.Errorf("failed to read catalog file: %w", err)
	}
	if err := yaml.Unmarshal(data, &catalogProducts); err != nil {
		return fmt.Errorf("failed to parse catalog yaml: %w", err)
	}
	return nil
}

type ListProductsArgs struct{}

type ListProductsResult struct {
	Products []Product `json:"products"`
}

// ListProducts function tool handler
func ListProducts(ctx tool.Context, args ListProductsArgs) (ListProductsResult, error) {
	if len(catalogProducts) == 0 {
		if err := loadCatalog(defaultCatalogFile); err != nil {
			return ListProductsResult{}, err
		}
	}
	return ListProductsResult{Products: catalogProducts}, nil
}

func NewCatalogAgent(project string, filename string) (agent.Agent, error) {
	// Preload catalog to fail early if file is missing/invalid
	if filename == "" {
		filename = defaultCatalogFile
	}

	ctx := context.Background()
	m, err := gemini.NewModel(ctx, "gemini-3-flash-preview", &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  project,
		Location: "global",
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create model: %w", err)
	}
	if err := loadCatalog(filename); err != nil {
		return nil, fmt.Errorf("failed to load catalog: %w", err)
	}

	listTool, err := functiontool.New(functiontool.Config{
		Name:        "listProducts",
		Description: "list all products in the catalog",
	}, ListProducts)
	if err != nil {
		return nil, fmt.Errorf("failed to create list products tool: %w", err)
	}

	imageTool, err := tools.NewImageTool()
	if err != nil {
		return nil, fmt.Errorf("failed to create get product image tool: %w", err)
	}

	return llmagent.New(llmagent.Config{
		Name:        "catalog_agent",
		Model:       m,
		Description: "An agent that can search and list products from the catalog",
		Instruction: instructions,
		Tools:       []tool.Tool{listTool, imageTool},
	})
}
