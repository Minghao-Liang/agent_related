package ddg

import (
	"backend-go/internal/search"
	"context"
	"errors"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
)

type Client struct {
	httpClient *http.Client
	baseURL    string
	userAgent  string
}

func NewClient() *Client {
	return &Client{
		httpClient: &http.Client{Timeout: 15 * time.Second},
		baseURL:    "https://html.duckduckgo.com/html/",
		userAgent:  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	}
}

func (c *Client) Search(ctx context.Context, query string, maxResults int) ([]search.SearchResult, error) {
	if strings.TrimSpace(query) == "" {
		return nil, errors.New("query is empty")
	}
	if maxResults <= 0 {
		return []search.SearchResult{}, nil
	}

	u, err := url.Parse(c.baseURL)
	if err != nil {
		return nil, err
	}
	qv := u.Query()
	qv.Set("q", query)
	u.RawQuery = qv.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", c.userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.9")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, errors.New("duckduckgo returned non-2xx status")
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, err
	}

	results := make([]search.SearchResult, 0, maxResults)
	doc.Find("div.result").EachWithBreak(func(_ int, s *goquery.Selection) bool {
		a := s.Find("a.result__a").First()
		href, _ := a.Attr("href")
		title := strings.TrimSpace(a.Text())
		if href == "" || title == "" {
			return true
		}
		href = normalizeDDGLink(href)

		snippet := strings.TrimSpace(s.Find("a.result__snippet").First().Text())
		if snippet == "" {
			snippet = strings.TrimSpace(s.Find("div.result__snippet").First().Text())
		}

		results = append(results, search.SearchResult{
			Title:   title,
			Link:    href,
			Snippet: snippet,
		})

		return len(results) < maxResults
	})

	if len(results) == 0 {
		return nil, errors.New("no results")
	}

	return results, nil
}

func normalizeDDGLink(href string) string {
	u, err := url.Parse(href)
	if err != nil {
		return href
	}
	if !strings.Contains(u.Host, "duckduckgo.com") {
		return href
	}
	if u.Path != "/l/" {
		return href
	}
	uddg := u.Query().Get("uddg")
	if uddg == "" {
		return href
	}
	decoded, err := url.QueryUnescape(uddg)
	if err != nil {
		return href
	}
	return decoded
}
