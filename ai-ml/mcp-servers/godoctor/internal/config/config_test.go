package config

import (
	"testing"
)

func TestLoad(t *testing.T) {
	tests := []struct {
		name         string
		args         []string
		wantProfile  Profile
		wantDisabled []string
	}{
		{
			name:        "default",
			args:        []string{},
			wantProfile: ProfileStandard,
		},
		{
			name:         "disable single tool",
			args:         []string{"--disable", "review_code"},
			wantProfile:  ProfileStandard,
			wantDisabled: []string{"review_code"},
		},
		{
			name:         "disable multiple tools",
			args:         []string{"--disable", "review_code,write, edit_code"},
			wantProfile:  ProfileStandard,
			wantDisabled: []string{"review_code", "write", "edit_code"},
		},
		{
			name:         "disable empty",
			args:         []string{"--disable", ""},
			wantProfile:  ProfileStandard,
			wantDisabled: []string{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cfg, err := Load(tt.args)
			if err != nil {
				t.Fatalf("Load() error = %v", err)
			}
			
			if cfg.Profile != tt.wantProfile {
				t.Errorf("Load() Profile = %v, want %v", cfg.Profile, tt.wantProfile)
			}

			if len(tt.wantDisabled) != len(cfg.DisabledTools) {
				t.Errorf("Load().DisabledTools len = %v, want %v", len(cfg.DisabledTools), len(tt.wantDisabled))
			}
			for _, d := range tt.wantDisabled {
				if !cfg.DisabledTools[d] {
					t.Errorf("Load().DisabledTools[%q] not found", d)
				}
			}
		})
	}
}
