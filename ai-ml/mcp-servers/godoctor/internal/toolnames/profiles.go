package toolnames

// ProfileDef defines a set of tools enabled for a profile.
type ProfileDef struct {
	Name        string   `json:"name" yaml:"name"`
	Description string   `json:"description" yaml:"description"`
	Tools       []string `json:"tools" yaml:"tools"` // List of INTERNAL tool names to enable
}

// DefaultProfiles returns the hardcoded default profile definitions.
func DefaultProfiles() map[string]ProfileDef {
	return map[string]ProfileDef{
		"standard": {
			Name:        "standard",
			Description: "The default profile. Balanced for general coding tasks.",
			Tools: []string{
				"agent.specialist",
				"cmd.run",
				"file.edit",
				"file.list",
				"file.outline",
				"file.read",
				"go.build",
				"go.docs",
				"go.test",
				"project.map",
				"symbol.inspect",
			},
		},
		"advanced": {
			Name:        "advanced",
			Description: "Enables all experimental and legacy features. The 'Kitchen Sink'.",
			Tools: []string{
				// All tools (implicitly handled by logic usually, but here explicit)
				"agent.master", "agent.review", "agent.specialist",
				"cmd.run", "file.create", "file.edit", "file.edit_legacy", "file.list", "file.outline", "file.read",
				"go.build", "go.diff", "go.docs", "go.get", "go.install", "go.mod", "go.modernize", "go.test",
				"project.map",
				"symbol.inspect", "symbol.rename",
			},
		},
		"oracle": {
			Name:        "oracle",
			Description: "Forced Agentic Flow. The user sees only one tool.",
			Tools: []string{
				"agent.specialist",
			},
		},
	}
}

// ActiveProfiles holds the currently active profile definitions.
// It is initialized with defaults but can be overridden.
var ActiveProfiles = DefaultProfiles()
