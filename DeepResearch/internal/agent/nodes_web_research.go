package agent

import (
	"backend-go/internal/domain"
	"backend-go/internal/llm"
	"backend-go/internal/prompts"
	"context"
	"fmt"
	"sync"
)

func (r *runner) webResearch(ctx context.Context, state *AgentState, sink EventSink) ([]string, []domain.Source, error) {
	var summaries []string
	var allSources []domain.Source

	// Process queries concurrently
	var wg sync.WaitGroup
	var mu sync.Mutex

	for _, query := range state.SearchQueries {
		wg.Add(1)
		go func(q string) {
			defer wg.Done()

			// 1. Search
			results, err := r.searchClient.Search(ctx, q, 5) // maxResults hardcoded or config
			if err != nil {
				// Log error but continue?
				fmt.Printf("Search failed for %s: %v\n", q, err)
				return
			}

			// 2. Build Sources
			resolvedMap := r.citation.ResolveURLs(results)
			sources := r.citation.BuildSources(results, resolvedMap)

			// 3. Summarize
			prompt := prompts.Render(r.prompts.WebSearcherInstructions(), map[string]interface{}{
				"research_topic": q,
				"current_date":   getCurrentDate(),
			})

			var resultsText string
			for i, res := range results {
				resultsText += fmt.Sprintf("Source [%d]: %s\nURL: %s\nSnippet: %s\n\n", i+1, res.Title, res.Link, res.Snippet)
			}

			msgs := []domain.Message{
				{Role: domain.RoleSystem, Content: prompt},
				{Role: domain.RoleUser, Content: fmt.Sprintf("Search Results:\n%s", resultsText)},
			}

			resp, err := r.llmClient.Generate(ctx, msgs, llm.WithModel(r.cfg.QueryGeneratorModel), llm.WithTemperature(0))
			if err != nil {
				fmt.Printf("Summarize failed for %s: %v\n", q, err)
				return
			}

			summary := resp.Content

			mu.Lock()
			summaries = append(summaries, summary)
			allSources = append(allSources, sources...)

			if sink != nil {
				sink.Emit(ctx, domain.AgentEvent{
					Type: domain.EventWebResearch,
					Payload: map[string]interface{}{
						"search_query":        []string{q},
						"sources_gathered":    sources,
						"web_research_result": []string{summary},
					},
				})
			}
			mu.Unlock()

		}(query)
	}

	wg.Wait()

	return summaries, allSources, nil
}
