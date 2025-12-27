package domain

type Source struct {
	Label    string `json:"label"`
	ShortRef string `json:"short_url"` // e.g. "([1])"
	URL      string `json:"value"`
}

type AgentRequest struct {
	Messages                []Message `json:"messages"`
	InitialSearchQueryCount int       `json:"initial_search_query_count"`
	MaxResearchLoops        int       `json:"max_research_loops"`
	ReasoningModel          string    `json:"reasoning_model"`
}

type AgentResult struct {
	Messages        []Message `json:"messages"`
	SourcesGathered []Source  `json:"sources_gathered,omitempty"`
}

type EventType string

const (
	EventGenerateQuery  EventType = "generate_query"
	EventWebResearch    EventType = "web_research"
	EventReflection     EventType = "reflection"
	EventFinalizeAnswer EventType = "finalize_answer"
)

type AgentEvent struct {
	Type    EventType `json:"type"`
	Payload any       `json:"payload"`
}
