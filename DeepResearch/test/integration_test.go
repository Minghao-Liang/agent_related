package test

import (
	"backend-go/internal/agent"
	"backend-go/internal/config"
	"backend-go/internal/domain"
	"backend-go/internal/llm"
	"backend-go/internal/prompts/builtin"
	"backend-go/internal/search/ddg"
	"context"
	"strings"
	"testing"
)

type MockSink struct {
	Events []domain.AgentEvent
}

func (s *MockSink) Emit(ctx context.Context, evt domain.AgentEvent) {
	s.Events = append(s.Events, evt)
}

type MockLLM struct{}

func (m *MockLLM) Generate(ctx context.Context, messages []domain.Message, opts ...llm.Option) (domain.Message, error) {
	// Inspect the prompt (System message) to decide what to return
    var prompt string
    if len(messages) > 0 {
        prompt = messages[0].Content
    }
    
    if strings.Contains(prompt, "Format your response as a JSON object") {
        if strings.Contains(prompt, "rationale") && strings.Contains(prompt, "query") {
             return domain.Message{
                Role: domain.RoleAI,
                Content: `{"rationale": "test", "query": ["test query"]}`,
            }, nil
        }
        if strings.Contains(prompt, "is_sufficient") {
             return domain.Message{
                Role: domain.RoleAI,
                Content: `{"is_sufficient": true, "knowledge_gap": "", "follow_up_queries": []}`,
            }, nil
        }
    }
    
	return domain.Message{
		Role:    domain.RoleAI,
		Content: "This is a mock summary or answer. ([1])",
	}, nil
}

func TestAgentFlow(t *testing.T) {
	cfg := &config.ModelConfig{
		MaxRetries: 1,
	}
	
	llmClient := &MockLLM{}
	searchClient := ddg.NewClient() // Returns mock results
	promptsProvider := builtin.NewProvider()
	
	runner := agent.NewRunner(cfg, llmClient, searchClient, promptsProvider)
	
	sink := &MockSink{}
	req := domain.AgentRequest{
		Messages: []domain.Message{{Role: domain.RoleUser, Content: "Test question"}},
		InitialSearchQueryCount: 1,
		MaxResearchLoops: 1,
	}
	
	result, err := runner.Run(context.Background(), req, sink)
	if err != nil {
		t.Fatalf("Run failed: %v", err)
	}
	
	if len(result.Messages) == 0 {
		t.Error("Expected messages in result")
	}
	
	// Check events
	hasQuery := false
	hasResearch := false
	hasAnswer := false
	
	for _, evt := range sink.Events {
		switch evt.Type {
		case domain.EventGenerateQuery:
			hasQuery = true
		case domain.EventWebResearch:
			hasResearch = true
		case domain.EventFinalizeAnswer:
			hasAnswer = true
		}
	}
	
	if !hasQuery {
		t.Error("Missing GenerateQuery event")
	}
	if !hasResearch {
		t.Error("Missing WebResearch event")
	}
	if !hasAnswer {
		t.Error("Missing FinalizeAnswer event")
	}
}
