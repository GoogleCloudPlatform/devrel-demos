package cmd

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"

	"github.com/danicat/testquery/internal/database"
	_ "github.com/mattn/go-sqlite3"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/spf13/cobra"
)

var mcpCmd = &cobra.Command{
	Use:   "mcp",
	Short: "Run the MCP server.",
	Long:  `Run the MCP server to expose testquery as a tool.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		s := mcp.NewServer(&mcp.Implementation{}, nil)
		mcp.AddTool(s, &mcp.Tool{
			Name:        "query",
			Description: "Query the test database",
		}, func(ctx context.Context, ss *mcp.ServerSession, ctp *mcp.CallToolParamsFor[map[string]any]) (*mcp.CallToolResultFor[any], error) {
			q, ok := ctp.Arguments["query"].(string)
			if !ok {
				return &mcp.CallToolResultFor[any]{
					Content: []mcp.Content{
						&mcp.TextContent{
							Text: "Invalid query argument",
						},
					},
					IsError: true,
				}, nil
			}

			var b bytes.Buffer
			if err := RunQueryInMemory(&b, q, "./..."); err != nil {
				return &mcp.CallToolResultFor[any]{
					Content: []mcp.Content{
						&mcp.TextContent{
							Text: err.Error(),
						},
					},
					IsError: true,
				}, nil
			}

			return &mcp.CallToolResultFor[any]{
				Content: []mcp.Content{
					&mcp.TextContent{
						Text: b.String(),
					},
				},
			}, nil
		})

		mcp.AddTool(s, &mcp.Tool{
			Name:        "discover",
			Description: "Discover all available tables and their schemas",
		}, func(ctx context.Context, ss *mcp.ServerSession, ctp *mcp.CallToolParamsFor[map[string]any]) (*mcp.CallToolResultFor[any], error) {
			schema, err := getSchema()
			if err != nil {
				return &mcp.CallToolResultFor[any]{
					Content: []mcp.Content{
						&mcp.TextContent{
							Text: err.Error(),
						},
					},
					IsError: true,
				}, nil
			}

			b, err := json.Marshal(schema)
			if err != nil {
				return &mcp.CallToolResultFor[any]{
					Content: []mcp.Content{
						&mcp.TextContent{
							Text: err.Error(),
						},
					},
					IsError: true,
				}, nil
			}

			return &mcp.CallToolResultFor[any]{
				Content: []mcp.Content{
					&mcp.TextContent{
						Text: string(b),
					},
				},
			}, nil
		})

		transport := mcp.NewStdioTransport()
		return s.Run(context.Background(), transport)
	},
}

func getSchema() (map[string]string, error) {
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		return nil, fmt.Errorf("failed to open in-memory database: %w", err)
	}
	defer db.Close()

	if err := database.CreateTables(db); err != nil {
		return nil, fmt.Errorf("failed to create tables: %w", err)
	}

	rows, err := db.Query("SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'view')")
	if err != nil {
		return nil, fmt.Errorf("failed to query schema: %w", err)
	}
	defer rows.Close()

	schema := make(map[string]string)
	for rows.Next() {
		var name, sql string
		if err := rows.Scan(&name, &sql); err != nil {
			return nil, fmt.Errorf("failed to scan schema row: %w", err)
		}
		schema[name] = sql
	}

	return schema, nil
}

func init() {
	rootCmd.AddCommand(mcpCmd)
}
