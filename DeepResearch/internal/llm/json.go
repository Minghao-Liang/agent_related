package llm

import (
	"backend-go/internal/domain"
	"context"
	"encoding/json"
	"fmt"
	"strings"
)

type JSONGenerator interface {
	GenerateJSON(ctx context.Context, messages []domain.Message, target interface{}, opts ...Option) error
}

type jsonGenerator struct {
	llm ChatLLM
}

func NewJSONGenerator(llm ChatLLM) JSONGenerator {
	return &jsonGenerator{llm: llm}
}

func (j *jsonGenerator) GenerateJSON(ctx context.Context, messages []domain.Message, target interface{}, opts ...Option) error {
	resp, err := j.llm.Generate(ctx, messages, opts...)
	if err != nil {
		return err
	}

	// Clean up response (remove markdown code blocks)
	content := CleanJSON(resp.Content)

	err = json.Unmarshal([]byte(content), target)
	if err != nil {
		return fmt.Errorf("failed to parse JSON: %w. Content: %s", err, content)
	}

	return nil
}

func CleanJSON(s string) string {
	s = strings.TrimSpace(s)
	s = strings.TrimPrefix(s, "```json")
	s = strings.TrimPrefix(s, "```")
	s = strings.TrimSuffix(s, "```")
	return strings.TrimSpace(s)
}
