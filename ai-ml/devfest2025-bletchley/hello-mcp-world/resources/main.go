package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	myagent "gaia/internal/agent"
	"gaia/internal/model/ollama"
	"gaia/internal/rag"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/model"
	"google.golang.org/adk/model/gemini"
	"google.golang.org/adk/runner"
	"google.golang.org/adk/session"
	"google.golang.org/genai"
)

const appName = "aida"

func main() {
	ctx := context.Background()

	// 1. Initialize RAG clients
	queriesRAG, err := rag.New("packs.db")
	if err != nil {
		log.Fatalf("Failed to open packs.db: %v", err)
	}
	defer queriesRAG.Close()

	schemaRAG, err := rag.New("schema.db")
	if err != nil {
		log.Fatalf("Failed to open schema.db: %v", err)
	}
	defer schemaRAG.Close()

	// 2. Initialize Agent
	aidaAgent, dynModel, err := myagent.New(ctx, queriesRAG, schemaRAG)
	if err != nil {
		log.Fatalf("Failed to create agent: %v", err)
	}

	// 3. Initialize Session Service
	sessionService := session.InMemoryService()

	// 4. Initialize Runner
	aidaRunner, err := runner.New(runner.Config{
		AppName:        appName,
		Agent:          aidaAgent,
		SessionService: sessionService,
	})
	if err != nil {
		log.Fatalf("Failed to create runner: %v", err)
	}

	// 5. Set up HTTP handlers
	mux := http.NewServeMux()

	// Static files
	mux.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("static"))))
	mux.Handle("/assets/", http.StripPrefix("/assets/", http.FileServer(http.Dir("assets"))))

	// Root serves index.html
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		http.ServeFile(w, r, "templates/index.html")
	})

	// Specific asset endpoints from main.py
	assetHandler := func(filename string) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
			http.ServeFile(w, r, "assets/"+filename)
		}
	}
	mux.HandleFunc("/idle", assetHandler("idle.png"))
	mux.HandleFunc("/blink", assetHandler("blink.png"))
	mux.HandleFunc("/talk", assetHandler("talk.png"))
	mux.HandleFunc("/think", assetHandler("think.png"))
	mux.HandleFunc("/think_blink", assetHandler("think_blink.png"))
	mux.HandleFunc("/teehee", assetHandler("teehee.png"))
	mux.HandleFunc("/error", assetHandler("error.png"))

	// Config/Session endpoints
	mux.HandleFunc("/config/model", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			currentModelName := dynModel.Name()
			modelID := "gemini"
			if strings.Contains(currentModelName, "qwen") {
				modelID = "qwen"
			} else if strings.Contains(currentModelName, "gpt-oss") {
				modelID = "gpt-oss"
			}
			json.NewEncoder(w).Encode(map[string]string{"model_id": modelID})
		} else if r.Method == http.MethodPost {
			var body struct {
				ModelID string `json:"model_id"`
			}
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				http.Error(w, "Bad request", http.StatusBadRequest)
				return
			}

			var newModel model.LLM
			var err error
			switch body.ModelID {
			case "gemini":
				newModel, err = gemini.NewModel(r.Context(), "gemini-2.5-flash", nil)
			case "qwen":
				newModel = ollama.New("qwen2.5", "")
			case "gptoss", "gpt-oss":
				newModel = ollama.New("gpt-oss", "")
			default:
				http.Error(w, "Invalid model ID", http.StatusBadRequest)
				return
			}

			if err != nil {
				log.Printf("Failed to create model %s: %v", body.ModelID, err)
				http.Error(w, fmt.Sprintf("Failed to create model: %v", err), http.StatusInternalServerError)
				return
			}

			dynModel.Set(newModel)
			log.Printf("--- MODEL SWITCHED TO: %s ---", newModel.Name())
			json.NewEncoder(w).Encode(map[string]string{"status": "ok", "current_model": newModel.Name()})
		}
	})

	mux.HandleFunc("/session/usage", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]any{
			"prompt_tokens":     0,
			"completion_tokens": 0,
			"total_tokens":      0,
			"max_tokens":        1000000,
		})
	})

	mux.HandleFunc("/session/clear", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		err := sessionService.Delete(r.Context(), &session.DeleteRequest{
			AppName:   appName,
			UserID:    "web_user",
			SessionID: "web_session",
		})
		if err != nil {
			log.Printf("Error clearing session: %v", err)
		}
		json.NewEncoder(w).Encode(map[string]string{"status": "ok", "message": "Session history cleared."})
	})

	// Chat endpoint
	mux.HandleFunc("/chat", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var body struct {
			Query string `json:"query"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, "Bad request", http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "application/x-ndjson")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")

		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
			return
		}

		userID := "web_user"
		sessionID := "web_session"

		// Ensure session exists
		_, err := sessionService.Get(r.Context(), &session.GetRequest{
			AppName:   appName,
			UserID:    userID,
			SessionID: sessionID,
		})
		if err != nil {
			_, err = sessionService.Create(r.Context(), &session.CreateRequest{
				AppName:   appName,
				UserID:    userID,
				SessionID: sessionID,
			})
			if err != nil {
				log.Printf("Failed to create session: %v", err)
				http.Error(w, "Failed to create session", http.StatusInternalServerError)
				return
			}
		}

		userMsg := &genai.Content{
			Role: "user",
			Parts: []*genai.Part{
				{Text: body.Query},
			},
		}

		// Run the agent and stream events
		for event, err := range aidaRunner.Run(r.Context(), userID, sessionID, userMsg, agent.RunConfig{}) {
			if err != nil {
				log.Printf("Error during run: %v", err)
				json.NewEncoder(w).Encode(map[string]string{"type": "text", "content": fmt.Sprintf("\nError: %v", err)})
				flusher.Flush()
				return
			}

			if event.Content == nil {
				continue
			}

			for _, part := range event.Content.Parts {
				// 1. Log function calls
				if part.FunctionCall != nil {
					fc := part.FunctionCall
					argsParts := make([]string, 0, len(fc.Args))
					for k, v := range fc.Args {
						argsParts = append(argsParts, fmt.Sprintf("%s='%v'", k, v))
					}
					logMsg := fmt.Sprintf("EXECUTING: %s(%s)", fc.Name, strings.Join(argsParts, ", "))
					json.NewEncoder(w).Encode(map[string]string{"type": "log", "content": logMsg})
					flusher.Flush()
				}

				// 2. Log function outputs
				if part.FunctionResponse != nil {
					fr := part.FunctionResponse
					var outputStr string
					if result, ok := fr.Response["result"]; ok {
						outputStr = fmt.Sprintf("%v", result)
					} else {
						// Fallback if 'result' key isn't used
						if val, ok := fr.Response["output"]; ok {
							outputStr = fmt.Sprintf("%v", val)
						} else if val, ok := fr.Response["results"]; ok {
							outBytes, _ := json.Marshal(val)
							outputStr = string(outBytes)
						} else {
							outBytes, _ := json.Marshal(fr.Response)
							outputStr = string(outBytes)
						}
					}

					json.NewEncoder(w).Encode(map[string]string{"type": "tool_output", "content": outputStr})
					flusher.Flush()
				}

				// 3. Stream text
				if part.Text != "" {
					if part.Thought {
						json.NewEncoder(w).Encode(map[string]string{"type": "log", "content": "THOUGHT: " + part.Text})
						flusher.Flush()
					} else if event.IsFinalResponse() {
						json.NewEncoder(w).Encode(map[string]string{"type": "text", "content": part.Text})
						flusher.Flush()
					}
				}
			}
		}
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}
	fmt.Printf("AIDA AGENT READY. Listening on :%s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}
