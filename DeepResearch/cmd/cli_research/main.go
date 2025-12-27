package main

import (
	"backend-go/internal/agent"
	"backend-go/internal/config"
	"backend-go/internal/domain"
	"backend-go/internal/llm/openai"
	"backend-go/internal/prompts/builtin"
	"backend-go/internal/search/ddg"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
)

type StdoutSink struct{}

func (s *StdoutSink) Emit(ctx context.Context, evt domain.AgentEvent) {
	bytes, _ := json.MarshalIndent(evt, "", "  ")
	fmt.Printf("Event: %s\n%s\n\n", evt.Type, string(bytes))
}

func main() {
	// Flags
	question := flag.String("question", "What are the latest trends in renewable energy?", "The research question")
	initialQueries := flag.Int("initial-queries", 3, "Initial number of queries")
	maxLoops := flag.Int("max-loops", 3, "Max research loops")
	reasoningModel := flag.String("reasoning-model", "kimi-k2-thinking", "Model for reasoning")

	flag.Parse()

	// Config
	cfg := config.Load()
	if cfg.APIKey == "" {
		// Mock mode if no API Key?
		// The instructions say "Load env -> ModelConfig".
		// I'll fail if no API Key is present, but I should probably allow running with mock LLM if I had one.
		// For now, I'll log a warning but proceed, hoping the user provides it or we use a mock.
		// Wait, I only implemented OpenAI client. It will fail without API key.
		// But I'm running tests or verification.
		// I will check if I can run it.
		log.Println("Warning: API_KEY not set. OpenAI calls will likely fail.")
	}

	// Dependencies
	llmClient := openai.NewChatModel(cfg.BaseURL, cfg.APIKey)
	searchClient := ddg.NewClient()
	promptsProvider := builtin.NewProvider()

	// Runner
	runner := agent.NewRunner(cfg, llmClient, searchClient, promptsProvider)

	// Context
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle SIGINT
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		cancel()
	}()

	// Request
	req := domain.AgentRequest{
		Messages: []domain.Message{
			{Role: domain.RoleUser, Content: *question},
		},
		InitialSearchQueryCount: *initialQueries,
		MaxResearchLoops:        *maxLoops,
		ReasoningModel:          *reasoningModel,
	}

	// Run
	fmt.Printf("Starting research on: %s\n", *question)
	result, err := runner.Run(ctx, req, &StdoutSink{})
	if err != nil {
		log.Fatalf("Research failed: %v", err)
	}

	// Output result
	if len(result.Messages) > 0 {
		lastMsg := result.Messages[len(result.Messages)-1]
		fmt.Println("Final Answer:")
		fmt.Println(lastMsg.Content)

		// Write to file
		err := os.WriteFile("output.md", []byte(lastMsg.Content), 0644)
		if err != nil {
			log.Printf("Failed to write output.md: %v", err)
		} else {
			fmt.Println("Output written to output.md")
		}
	}
}
