package server

import (
	"testing"

	"github.com/danicat/godoctor/internal/config"
)

func TestServer_RegisterHandlers_DisableTools(t *testing.T) {
	tests := []struct {
		name          string
		disabledTools map[string]bool
		wantErr       bool
	}{
		{
			name:          "no disabled tools",
			disabledTools: map[string]bool{},
			wantErr:       false,
		},
		{
			name:          "disable valid tool",
			disabledTools: map[string]bool{"code_review": true},
			wantErr:       false,
		},
		{
			name:          "disable previously experimental tool",
			disabledTools: map[string]bool{"file_create": true},
			wantErr:       false,
		},
		{
			name:          "disable invalid tool",
			disabledTools: map[string]bool{"invalid_tool": true},
			wantErr:       true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg := &config.Config{
				DisabledTools: tt.disabledTools,
			}
			s := New(cfg, "test")
			err := s.RegisterHandlers()
			if (err != nil) != tt.wantErr {
				t.Errorf("RegisterHandlers() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}
