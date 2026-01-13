package server

import (
	"testing"

	"github.com/danicat/godoctor/internal/config"
)

func TestServer_RegisterHandlers_DisableTools(t *testing.T) {
	tests := []struct {
		name          string
		disabledTools map[string]bool
		experimental  bool
		wantErr       bool
	}{
		{
			name:          "no disabled tools",
			disabledTools: map[string]bool{},
			wantErr:       false,
		},
		{
			name:          "disable valid tool",
			disabledTools: map[string]bool{"review_code": true},
			wantErr:       false,
		},
		{
			name:          "disable experimental tool when experimental enabled",
			disabledTools: map[string]bool{"write": true},
			experimental:  true,
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
				Experimental:  tt.experimental,
			}
			s := New(cfg, "test")
			err := s.RegisterHandlers()
			if (err != nil) != tt.wantErr {
				t.Errorf("RegisterHandlers() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}
