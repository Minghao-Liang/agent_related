package agent

import (
	"backend-go/internal/domain"
	"backend-go/internal/llm"
	"backend-go/internal/prompts"
	"context"
	"strings"
)

func (r *runner) finalizeAnswer(ctx context.Context, state *AgentState) (domain.Message, error) {
	topicStr := r.topicExtractor.ResearchTopic(state.Messages)
	summariesStr := strings.Join(state.WebResearchResults, "\n\n")

	prompt := prompts.Render(r.prompts.AnswerInstructions(), map[string]interface{}{
		"research_topic": topicStr,
		"current_date":   getCurrentDate(),
		"summaries":      summariesStr,
	})

	msgs := []domain.Message{
		{Role: domain.RoleSystem, Content: prompt},
	}

	model := r.cfg.AnswerModel
	if state.ReasoningModel != "" {
		model = state.ReasoningModel
	}

	resp, err := r.llmClient.Generate(ctx, msgs, llm.WithModel(model), llm.WithTemperature(r.cfg.TemperatureAnswer))
	if err != nil {
		return domain.Message{}, err
	}

	finalContent, usedSources := r.citation.ReplaceShortRefs(resp.Content, state.SourcesGathered)
	state.SourcesGathered = usedSources

	return domain.Message{
		Role:    domain.RoleAI,
		Content: finalContent,
	}, nil
}
