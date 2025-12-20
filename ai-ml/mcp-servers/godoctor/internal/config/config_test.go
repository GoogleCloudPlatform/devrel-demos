package config

import (
	"testing"
)

func TestLoad(t *testing.T) {
	tests := []struct {
		name             string
		args             []string
		wantExperimental bool
	}{
		{
			name:             "default",
			args:             []string{},
			wantExperimental: false,
		},
		{
			name:             "experimental true",
			args:             []string{"--experimental"},
			wantExperimental: true,
		},
		{
			name:             "experimental explicit true",
			args:             []string{"--experimental=true"},
			wantExperimental: true,
		},
		{
			name:             "experimental explicit false",
			args:             []string{"--experimental=false"},
			wantExperimental: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg, err := Load(tt.args)
			if err != nil {
				t.Fatalf("Load() error = %v", err)
			}
			if cfg.Experimental != tt.wantExperimental {
				t.Errorf("Load().Experimental = %v, want %v", cfg.Experimental, tt.wantExperimental)
			}
		})
	}
}
