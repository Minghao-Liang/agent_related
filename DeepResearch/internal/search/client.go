package search

import "context"

type SearchResult struct {
	Title   string
	Link    string
	Snippet string
}

type Client interface {
	Search(ctx context.Context, query string, maxResults int) ([]SearchResult, error)
}
