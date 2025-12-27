package citation

import (
	"backend-go/internal/domain"
	"backend-go/internal/search"
)

type Builder interface {
	ResolveURLs(results []search.SearchResult) map[string]string
	BuildSources(results []search.SearchResult, resolved map[string]string) []domain.Source
	ReplaceShortRefs(answer string, sources []domain.Source) (string, []domain.Source)
}
