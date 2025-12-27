package agent

import "backend-go/internal/domain"

type AgentState struct {
	Messages                []domain.Message
	SearchQueries           []string // Latest batch of queries
	WebResearchResults      []string // Summaries
	SourcesGathered         []domain.Source
	InitialSearchQueryCount int
	MaxResearchLoops        int
	ResearchLoopCount       int
	ReasoningModel          string
	IsSufficient            bool
	KnowledgeGap            string
	FollowUpQueries         []string
}
