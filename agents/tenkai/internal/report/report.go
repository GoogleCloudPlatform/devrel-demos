package report

import (
	"io"
	"os"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
)

// Reporter generates reports from run results.
type Reporter struct {
	Results []runner.Result
	Out     io.Writer
	Cfg     *config.Configuration
	Notes   []string
}

// New creates a new Reporter.
func New(results []runner.Result, out io.Writer, cfg *config.Configuration, notes []string) *Reporter {
	return &Reporter{
		Results: results,
		Out:     out,
		Cfg:     cfg,
		Notes:   notes,
	}
}

// GenerateMarkdownReport creates an enhanced markdown report file.
func (r *Reporter) GenerateMarkdownReport(path string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	return r.GenerateMarkdown(f)
}

// GenerateMarkdown writes the enhanced markdown report to the provided writer.
func (r *Reporter) GenerateMarkdown(w io.Writer) error {
	gen := &EnhancedMarkdownGenerator{
		Results: r.Results,
		Cfg:     r.Cfg,
		Notes:   r.Notes,
		w:       w,
	}

	return gen.Generate()
}
