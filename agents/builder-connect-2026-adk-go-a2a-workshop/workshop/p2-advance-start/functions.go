// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// The concierge's advanced capabilities, which main.go wires in:
//
//   - newSkills: the skills in skills/, loaded when a request needs them.
//   - newWorkspace: a workspace folder with read_file, write_file and bash,
//     which runs only the commands the attendee approves.
//   - newDayPlanner: day_planner, a graph workflow that researches in
//     parallel, plans, checks the plan in code, and asks before saving it.

package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"google.golang.org/genai"

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/agent/llmagent"
	"google.golang.org/adk/v2/agent/workflowagent"
	"google.golang.org/adk/v2/model"
	"google.golang.org/adk/v2/session"
	"google.golang.org/adk/v2/tool"
	"google.golang.org/adk/v2/tool/functiontool"
	"google.golang.org/adk/v2/tool/skilltoolset"
	"google.golang.org/adk/v2/tool/skilltoolset/skill"
	"google.golang.org/adk/v2/workflow"
)

// Skills.

// newSkills returns the skills in skills/. A skill is a folder with a
// SKILL.md. The model sees only the skills' names and descriptions, and loads
// a skill's instructions, references and assets when a request needs them.
func newSkills(ctx context.Context) (tool.Toolset, error) {
	return skilltoolset.New(ctx, skilltoolset.Config{Source: skill.NewFileSystemSource(os.DirFS("skills"))})
}

// The workspace: files the agent reads and writes, and where bash runs.

// workspace is a folder the agent works in. Its file tools can't reach
// outside it: os.Root rejects paths that leave the folder.
type workspace struct {
	dir  string
	root *os.Root
}

// newWorkspace opens the folder dir, creating it if needed, and returns it
// with the tools that work in it: read_file, write_file and bash.
func newWorkspace(dir string) (*workspace, []tool.Tool, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, nil, err
	}
	root, err := os.OpenRoot(dir)
	if err != nil {
		return nil, nil, err
	}
	w := &workspace{dir: dir, root: root}
	readFile, err := functiontool.New(functiontool.Config{
		Name:        "read_file",
		Description: "Reads a text file in the attendee's workspace.",
	}, w.readFile)
	if err != nil {
		return nil, nil, err
	}
	writeFile, err := functiontool.New(functiontool.Config{
		Name:        "write_file",
		Description: "Writes a text file in the attendee's workspace, creating folders as needed and replacing the file if it exists.",
	}, w.writeFile)
	if err != nil {
		return nil, nil, err
	}
	bash, err := functiontool.New(functiontool.Config{
		Name:        "bash",
		Description: "Runs a bash command in the attendee's workspace folder and returns its output. The attendee approves every command first.",
	}, w.bash)
	if err != nil {
		return nil, nil, err
	}
	return w, []tool.Tool{readFile, writeFile, bash}, nil
}

type readArgs struct {
	Path string `json:"path" jsonschema:"Path of the file, relative to the workspace."`
}

type readResult struct {
	Content string `json:"content"`
}

func (w *workspace) readFile(_ agent.Context, in readArgs) (readResult, error) {
	b, err := w.root.ReadFile(in.Path)
	if err != nil {
		return readResult{}, err
	}
	return readResult{Content: string(b)}, nil
}

type writeArgs struct {
	Path    string `json:"path" jsonschema:"Path of the file, relative to the workspace."`
	Content string `json:"content" jsonschema:"The whole content of the file."`
}

type writeResult struct {
	Written string `json:"written"`
}

func (w *workspace) writeFile(_ agent.Context, in writeArgs) (writeResult, error) {
	if err := w.root.MkdirAll(path.Dir(in.Path), 0o755); err != nil {
		return writeResult{}, err
	}
	if err := w.root.WriteFile(in.Path, []byte(in.Content), 0o644); err != nil {
		return writeResult{}, err
	}
	return writeResult{Written: in.Path}, nil
}

type bashArgs struct {
	Command string `json:"command" jsonschema:"The command to run with bash, in the workspace folder."`
}

type bashResult struct {
	Output   string `json:"output"`
	ExitCode int    `json:"exit_code"`
}

func (w *workspace) bash(ctx agent.Context, in bashArgs) (bashResult, error) {
	// Ask the attendee first. ADK shows them the command, and calls this
	// tool again only if they approve it.
	if ctx.ToolConfirmation() == nil {
		if err := ctx.RequestConfirmation("Run this command in the workspace?", in); err != nil {
			return bashResult{}, err
		}
		ctx.Actions().SkipSummarization = true
		return bashResult{}, tool.ErrConfirmationRequired
	}

	cmdCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	cmd := exec.CommandContext(cmdCtx, "bash", "-c", in.Command)
	cmd.Dir = w.dir
	out, err := cmd.CombinedOutput()
	var exitErr *exec.ExitError
	if err != nil && !errors.As(err, &exitErr) {
		return bashResult{}, err // bash didn't start
	}
	if cmdCtx.Err() != nil {
		out = append(out, "\n[stopped after 30 seconds]"...)
	}
	if len(out) > 10_000 {
		out = append(out[:10_000], "\n[output truncated]"...)
	}
	return bashResult{Output: string(out), ExitCode: cmd.ProcessState.ExitCode()}, nil
}

// The day planner: a graph workflow.
//
//	start ─┬─ agenda_scout ─┬─ gather ─ brief ─ planner ─ check ─ok─ approve ─save─ save
//	       └─ tech_scout ───┘                      ▲        │           │
//	                                               ├──fix───┘           │
//	                                               └──────revise────────┘

// planEntry and planCheck are the agenda server's check_plan result.
type planEntry struct {
	ID    string `json:"id"`
	Date  string `json:"date"`
	Start string `json:"start"`
	End   string `json:"end"`
	Title string `json:"title"`
}

type planCheck struct {
	Sessions []planEntry `json:"sessions"`
	Overlaps []struct {
		First  planEntry `json:"first"`
		Second planEntry `json:"second"`
	} `json:"overlaps"`
	NotFound []string `json:"not_found"`
}

// checkPlan calls the agenda server's check_plan tool directly, as an MCP
// client, so the check runs in code rather than in the model.
func checkPlan(ctx context.Context, ids []string) (planCheck, error) {
	client := mcp.NewClient(&mcp.Implementation{Name: "day-planner"}, nil)
	cs, err := client.Connect(ctx, &mcp.StreamableClientTransport{Endpoint: serverURL("AGENDA_MCP_URL", 8090)}, nil)
	if err != nil {
		return planCheck{}, err
	}
	defer cs.Close()
	res, err := cs.CallTool(ctx, &mcp.CallToolParams{Name: "check_plan", Arguments: map[string]any{"ids": ids}})
	if err != nil {
		return planCheck{}, err
	}
	b, err := json.Marshal(res.StructuredContent)
	if err != nil {
		return planCheck{}, err
	}
	var out planCheck
	return out, json.Unmarshal(b, &out)
}

// result is a node's output event: what the next node gets, the route to
// take, and values to keep in the session state. State reaches the session
// only on an event, and an event's Output, unlike a returned string, stays
// out of the chat.
func result(ctx agent.Context, output any, route string, state map[string]any) *session.Event {
	ev := session.NewEvent(ctx, ctx.InvocationID())
	ev.Output = output
	if route != "" {
		ev.Routes = []string{route}
	}
	ev.Actions.StateDelta = state
	return ev
}

func newDayPlanner(m model.LLM, agenda, technologies tool.Toolset, ws *workspace) (agent.Agent, error) {
	const listRules = `Today is 3 November 2026 (Builder Connect); 4 November is
Google Cloud Summit Poland. List every candidate session as one line:
"<id> | <date> <start>-<end> | <title>". Output only the list.`
	agendaScout, err := llmagent.New(llmagent.Config{
		Name:        "agenda_scout",
		Model:       m,
		Description: "Finds candidate sessions in the agenda.",
		Instruction: "Find sessions in the agenda that match the attendee's interests and time window, with search_sessions. " + listRules,
		Toolsets:    []tool.Toolset{agenda},
	})
	if err != nil {
		return nil, err
	}
	techScout, err := llmagent.New(llmagent.Config{
		Name:        "tech_scout",
		Model:       m,
		Description: "Finds candidate sessions through the technologies they cover.",
		Instruction: "Find the technologies that match the attendee's interests, such as a programming language or a product, with find_technologies, " +
			"then search the agenda once with all their names and aliases as terms. " + listRules,
		Toolsets: []tool.Toolset{agenda, technologies},
	})
	if err != nil {
		return nil, err
	}
	planner, err := llmagent.New(llmagent.Config{
		Name:        "planner",
		Model:       m,
		Description: "Picks the sessions for the plan.",
		Instruction: `You plan an attendee's conference day. From the candidate sessions you are
given, pick the best ones for the attendee's request: no overlaps, respect the
time window, and leave lunch free if asked. Fix every problem you are told about.`,
		// The model must answer with this JSON, which the check node reads.
		OutputSchema: &genai.Schema{
			Type: genai.TypeObject,
			Properties: map[string]*genai.Schema{
				"ids":    {Type: genai.TypeArray, Items: &genai.Schema{Type: genai.TypeString}, Description: "Ids of the chosen sessions."},
				"reason": {Type: genai.TypeString, Description: "One sentence on why these sessions."},
			},
			Required: []string{"ids", "reason"},
		},
	})
	if err != nil {
		return nil, err
	}

	agendaNode, err := workflow.NewAgentNode(agendaScout, workflow.NodeConfig{})
	if err != nil {
		return nil, err
	}
	techNode, err := workflow.NewAgentNode(techScout, workflow.NodeConfig{})
	if err != nil {
		return nil, err
	}
	planNode, err := workflow.NewAgentNode(planner, workflow.NodeConfig{})
	if err != nil {
		return nil, err
	}

	// gather waits for both scouts, and passes on a map of their outputs.
	gather := workflow.NewJoinNode("gather")

	// brief turns the scouts' findings into the planner's input, and keeps it
	// for later rounds.
	brief := workflow.NewFunctionNode("brief", func(ctx agent.Context, found map[string]any) (any, error) {
		var request strings.Builder
		if uc := ctx.UserContent(); uc != nil {
			for _, p := range uc.Parts {
				request.WriteString(p.Text)
			}
		}
		b := fmt.Sprintf("Attendee's request: %s\n\nCandidate sessions:\n%v\n%v", request.String(), found["agenda_scout"], found["tech_scout"])
		return result(ctx, b, "", map[string]any{"brief": b, "attempts": 0, "round": 0}), nil
	}, workflow.NodeConfig{})

	// check verifies the plan against the agenda in code: every session must
	// exist and none may overlap. Problems go back to the planner, up to three
	// times.
	check := workflow.NewFunctionNode("check", func(ctx agent.Context, in any) (any, error) {
		var proposal struct {
			IDs    []string `json:"ids"`
			Reason string   `json:"reason"`
		}
		raw, ok := in.(string)
		if !ok { // already decoded JSON
			b, _ := json.Marshal(in)
			raw = string(b)
		}
		if err := json.Unmarshal([]byte(raw), &proposal); err != nil {
			return nil, fmt.Errorf("planner output is not a plan: %w", err)
		}
		checked, err := checkPlan(ctx, proposal.IDs)
		if err != nil {
			return nil, err
		}
		var problems []string
		for _, o := range checked.Overlaps {
			problems = append(problems, fmt.Sprintf("%q overlaps %q", o.First.Title, o.Second.Title))
		}
		for _, id := range checked.NotFound {
			problems = append(problems, fmt.Sprintf("no session has id %q", id))
		}
		if len(checked.Sessions) == 0 {
			problems = append(problems, "the plan is empty")
		}
		attempts, _ := ctx.State().Get("attempts")
		if n, _ := attempts.(int); len(problems) > 0 && n < 3 {
			brief, _ := ctx.State().Get("brief")
			retry := fmt.Sprintf("%v\n\nYour previous plan had problems: %s. Plan again.", brief, strings.Join(problems, "; "))
			return result(ctx, retry, "fix", map[string]any{"attempts": n + 1}), nil
		}
		var plan strings.Builder
		for _, s := range checked.Sessions {
			fmt.Fprintf(&plan, "- %s %s–%s  %s\n", s.Date, s.Start, s.End, s.Title)
		}
		return result(ctx, proposal.Reason, "ok", map[string]any{"plan": plan.String()}), nil
	}, workflow.NodeConfig{})

	// approve shows the plan and pauses the workflow until the attendee
	// answers. It then runs again, and ResumeOrRequestInput returns the
	// answer. The round number keeps each request's id unique when the plan
	// is revised.
	rerun := true
	approve := workflow.NewEmittingFunctionNode("approve", func(ctx agent.Context, reason any, emit func(*session.Event) error) (any, error) {
		plan, _ := ctx.State().Get("plan")
		round, _ := ctx.State().Get("round")
		reply, err := workflow.ResumeOrRequestInput(ctx, emit, session.RequestInput{
			InterruptID: fmt.Sprintf("approve-%s-%v", ctx.InvocationID(), round),
			Message:     fmt.Sprintf("Here's your plan:\n%v\n%v\n\nSave it? Answer yes, or tell me what to change.", plan, reason),
		})
		if err != nil {
			return nil, err // ErrNodeInterrupted: wait for the answer
		}
		switch answer := strings.ToLower(strings.TrimSpace(fmt.Sprint(reply))); {
		case answer == "y", answer == "ok", answer == "save", strings.HasPrefix(answer, "yes"):
			return nil, emit(result(ctx, plan, "save", nil))
		}
		brief, _ := ctx.State().Get("brief")
		n, _ := round.(int)
		revise := fmt.Sprintf("%v\n\nYour previous plan was:\n%v\nThe attendee wants this changed: %v", brief, plan, reply)
		return nil, emit(result(ctx, revise, "revise", map[string]any{"attempts": 0, "round": n + 1}))
	}, workflow.NodeConfig{RerunOnResume: &rerun})

	// save writes the approved plan to the workspace.
	save := workflow.NewFunctionNode("save", func(ctx agent.Context, plan any) (any, error) {
		if err := ws.root.WriteFile("my-plan.md", []byte("# My plan\n\n"+fmt.Sprint(plan)), 0o644); err != nil {
			return nil, err
		}
		return genai.NewContentFromText("Saved your plan to my-plan.md.", genai.RoleModel), nil
	}, workflow.NodeConfig{})

	eb := workflow.NewEdgeBuilder()
	eb.AddFanOut(workflow.Start, agendaNode, techNode)
	eb.AddFanIn(gather, agendaNode, techNode)
	eb.Add(gather, brief)
	eb.Add(brief, planNode)
	eb.Add(planNode, check)
	eb.AddRoutes(check, map[string]workflow.Node{"fix": planNode, "ok": approve})
	eb.AddRoutes(approve, map[string]workflow.Node{"save": save, "revise": planNode})

	return workflowagent.New(workflowagent.Config{
		Name:        "day_planner",
		Description: "Plans an attendee's day: researches in parallel, plans, checks the plan in code, and asks for approval before saving it.",
		Edges:       eb.Build(),
		SubAgents:   []agent.Agent{agendaScout, techScout, planner},
	})
}
