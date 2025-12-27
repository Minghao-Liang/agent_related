package topic

import (
	"backend-go/internal/domain"
	"fmt"
	"strings"
)

type Extractor interface {
	ResearchTopic(messages []domain.Message) string
}

type extractor struct{}

func NewExtractor() Extractor {
	return &extractor{}
}

func (e *extractor) ResearchTopic(messages []domain.Message) string {
	if len(messages) == 1 {
		return messages[len(messages)-1].Content
	}
	var sb strings.Builder
	for _, msg := range messages {
		role := "User"
		if msg.Role == domain.RoleAI {
			role = "Assistant"
		}
		sb.WriteString(fmt.Sprintf("%s: %s\n", role, msg.Content))
	}
	return sb.String()
}
