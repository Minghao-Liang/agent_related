package citation

import (
	"backend-go/internal/domain"
	"backend-go/internal/search"
	"fmt"
	"strings"
)

type builder struct{}

func NewBuilder() Builder {
	return &builder{}
}

func (b *builder) ResolveURLs(results []search.SearchResult) map[string]string {
	resolvedMap := make(map[string]string)
	for idx, result := range results {
		if result.Link != "" {
			if _, exists := resolvedMap[result.Link]; !exists {
				resolvedMap[result.Link] = fmt.Sprintf("([%d])", idx+1)
			}
		}
	}
	return resolvedMap
}

func (b *builder) BuildSources(results []search.SearchResult, resolved map[string]string) []domain.Source {
	var sources []domain.Source
	for _, result := range results {
		if result.Link == "" {
			continue
		}
		shortRef, ok := resolved[result.Link]
		if ok {
			sources = append(sources, domain.Source{
				Label:    result.Title,
				ShortRef: shortRef,
				URL:      result.Link,
			})
		}
	}
	return sources
}

func (b *builder) ReplaceShortRefs(answer string, sources []domain.Source) (string, []domain.Source) {
	finalAnswer := answer
	var usedSources []domain.Source
	seen := make(map[string]struct{})
	for _, source := range sources {
		if _, ok := seen[source.ShortRef]; ok {
			continue
		}
		if !strings.Contains(finalAnswer, source.ShortRef) {
			continue
		}
		seen[source.ShortRef] = struct{}{}
		replacement := fmt.Sprintf("([%s](%s))", source.Label, source.URL)
		finalAnswer = strings.ReplaceAll(finalAnswer, source.ShortRef, replacement)
		usedSources = append(usedSources, source)
	}
	return finalAnswer, usedSources
}
