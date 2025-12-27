package agent

import (
	"backend-go/internal/domain"
	"backend-go/internal/llm"
	"backend-go/internal/prompts"
	"context"
	"strings"
)

type ReflectionOutput struct {
	IsSufficient    bool     `json:"is_sufficient"`
	KnowledgeGap    string   `json:"knowledge_gap"`
	FollowUpQueries []string `json:"follow_up_queries"`
}

func (r *runner) reflection(ctx context.Context, state *AgentState) (ReflectionOutput, error) {
	topicStr := r.topicExtractor.ResearchTopic(state.Messages)
	summariesStr := strings.Join(state.WebResearchResults, "\n\n")

	prompt := prompts.Render(r.prompts.ReflectionInstructions(), map[string]interface{}{
		"research_topic": topicStr,
		"summaries":      summariesStr,
	})

	msgs := []domain.Message{
		{Role: domain.RoleSystem, Content: prompt},
	}

	model := r.cfg.ReflectionModel
	if state.ReasoningModel != "" {
		model = state.ReasoningModel
	}

	var output ReflectionOutput
	err := r.jsonGen.GenerateJSON(ctx, msgs, &output, llm.WithModel(model), llm.WithTemperature(r.cfg.TemperatureReflect))
	if err != nil {
		return ReflectionOutput{}, err
	}

	return output, nil
}
