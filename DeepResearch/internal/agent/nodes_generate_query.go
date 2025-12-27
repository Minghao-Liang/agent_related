package agent

import (
	"backend-go/internal/domain"
	"backend-go/internal/llm"
	"backend-go/internal/prompts"
	"context"
)

type QueryGenerationOutput struct {
	Rationale string   `json:"rationale"`
	Queries   []string `json:"query"`
}

func (r *runner) generateQuery(ctx context.Context, state *AgentState) ([]string, error) {
	topicStr := r.topicExtractor.ResearchTopic(state.Messages)

	prompt := prompts.Render(r.prompts.QueryWriterInstructions(), map[string]interface{}{
		"research_topic": topicStr,
		"current_date":   getCurrentDate(),
		"number_queries": state.InitialSearchQueryCount,
	})

	messages := []domain.Message{
		{Role: domain.RoleSystem, Content: prompt},
	}

	var output QueryGenerationOutput
	err := r.jsonGen.GenerateJSON(ctx, messages, &output, llm.WithModel(r.cfg.QueryGeneratorModel), llm.WithTemperature(r.cfg.TemperatureQuery))
	if err != nil {
		return nil, err
	}

	return output.Queries, nil
}
