package agent

import (
	"backend-go/internal/citation"
	"backend-go/internal/config"
	"backend-go/internal/domain"
	"backend-go/internal/llm"
	"backend-go/internal/prompts"
	"backend-go/internal/search"
	"backend-go/internal/topic"
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/cloudwego/eino/compose"
)

type EventSink interface {
	Emit(ctx context.Context, evt domain.AgentEvent)
}

type Runner interface {
	Run(ctx context.Context, req domain.AgentRequest, sink EventSink) (domain.AgentResult, error)
}

type runner struct {
	cfg            *config.ModelConfig
	llmClient      llm.ChatLLM
	jsonGen        llm.JSONGenerator
	searchClient   search.Client
	prompts        prompts.Provider
	topicExtractor topic.Extractor
	citation       citation.Builder
	compiledGraph  compose.Runnable[*AgentState, *AgentState]
	compileOnce    sync.Once
	compileErr     error
}

func NewRunner(cfg *config.ModelConfig, llmClient llm.ChatLLM, searchClient search.Client, prompts prompts.Provider) Runner {
	return &runner{
		cfg:            cfg,
		llmClient:      llmClient,
		jsonGen:        llm.NewJSONGenerator(llmClient),
		searchClient:   searchClient,
		prompts:        prompts,
		topicExtractor: topic.NewExtractor(),
		citation:       citation.NewBuilder(),
	}
}

func (r *runner) Run(ctx context.Context, req domain.AgentRequest, sink EventSink) (domain.AgentResult, error) {
	state := &AgentState{
		Messages:                req.Messages,
		InitialSearchQueryCount: req.InitialSearchQueryCount,
		MaxResearchLoops:        req.MaxResearchLoops,
		ReasoningModel:          req.ReasoningModel,
		ResearchLoopCount:       0,
	}

	r.ensureCompiledGraph()
	if r.compileErr != nil {
		return domain.AgentResult{}, r.compileErr
	}

	ctx = withEventSink(ctx, sink)

	finalState, err := r.compiledGraph.Invoke(ctx, state)
	if err != nil {
		return domain.AgentResult{}, err
	}

	return domain.AgentResult{
		Messages:        finalState.Messages,
		SourcesGathered: finalState.SourcesGathered,
	}, nil
}

func getCurrentDate() string {
	return time.Now().Format("January 2, 2006")
}

type eventSinkKey struct{}

func withEventSink(ctx context.Context, sink EventSink) context.Context {
	return context.WithValue(ctx, eventSinkKey{}, sink)
}

func getEventSink(ctx context.Context) (EventSink, bool) {
	v := ctx.Value(eventSinkKey{})
	if v == nil {
		return nil, false
	}
	s, ok := v.(EventSink)
	return s, ok
}

func (r *runner) ensureCompiledGraph() {
	r.compileOnce.Do(func() {
		graph := compose.NewGraph[*AgentState, *AgentState]()

		if err := graph.AddLambdaNode("generate_query", compose.InvokableLambda(r.nodeGenerateQuery)); err != nil {
			r.compileErr = err
			return
		}
		if err := graph.AddLambdaNode("web_research", compose.InvokableLambda(r.nodeWebResearch)); err != nil {
			r.compileErr = err
			return
		}
		if err := graph.AddLambdaNode("reflection", compose.InvokableLambda(r.nodeReflection)); err != nil {
			r.compileErr = err
			return
		}
		if err := graph.AddLambdaNode("finalize_answer", compose.InvokableLambda(r.nodeFinalizeAnswer)); err != nil {
			r.compileErr = err
			return
		}

		if err := graph.AddEdge(compose.START, "generate_query"); err != nil {
			r.compileErr = err
			return
		}
		if err := graph.AddEdge("generate_query", "web_research"); err != nil {
			r.compileErr = err
			return
		}
		if err := graph.AddEdge("web_research", "reflection"); err != nil {
			r.compileErr = err
			return
		}

		branch := compose.NewGraphBranch(func(ctx context.Context, state *AgentState) (string, error) {
			if state.IsSufficient || state.ResearchLoopCount >= state.MaxResearchLoops {
				return "finalize_answer", nil
			}
			return "web_research", nil
		}, map[string]bool{
			"web_research":    true,
			"finalize_answer": true,
		})

		if err := graph.AddBranch("reflection", branch); err != nil {
			r.compileErr = err
			return
		}
		if err := graph.AddEdge("finalize_answer", compose.END); err != nil {
			r.compileErr = err
			return
		}

		r.compiledGraph, r.compileErr = graph.Compile(context.Background())
	})
}

func (r *runner) nodeGenerateQuery(ctx context.Context, state *AgentState) (*AgentState, error) {
	queries, err := r.generateQuery(ctx, state)
	if err != nil {
		return nil, fmt.Errorf("generate query failed: %w", err)
	}

	state.SearchQueries = queries

	if sink, ok := getEventSink(ctx); ok {
		sink.Emit(ctx, domain.AgentEvent{
			Type: domain.EventGenerateQuery,
			Payload: map[string]interface{}{
				"search_query": queries,
			},
		})
	}

	return state, nil
}

func (r *runner) nodeWebResearch(ctx context.Context, state *AgentState) (*AgentState, error) {
	sink, _ := getEventSink(ctx)

	summaries, sources, err := r.webResearch(ctx, state, sink)
	if err != nil {
		return nil, fmt.Errorf("web research failed: %w", err)
	}

	state.WebResearchResults = append(state.WebResearchResults, summaries...)
	state.SourcesGathered = append(state.SourcesGathered, sources...)

	return state, nil
}

func (r *runner) nodeReflection(ctx context.Context, state *AgentState) (*AgentState, error) {
	reflection, err := r.reflection(ctx, state)
	if err != nil {
		return nil, fmt.Errorf("reflection failed: %w", err)
	}

	state.ResearchLoopCount++
	state.IsSufficient = reflection.IsSufficient
	state.KnowledgeGap = reflection.KnowledgeGap
	state.FollowUpQueries = reflection.FollowUpQueries

	if !state.IsSufficient && len(state.FollowUpQueries) == 0 {
		state.IsSufficient = true
	}

	if sink, ok := getEventSink(ctx); ok {
		sink.Emit(ctx, domain.AgentEvent{
			Type: domain.EventReflection,
			Payload: map[string]interface{}{
				"is_sufficient":     state.IsSufficient,
				"knowledge_gap":     state.KnowledgeGap,
				"follow_up_queries": state.FollowUpQueries,
			},
		})
	}

	if !state.IsSufficient && state.ResearchLoopCount < state.MaxResearchLoops {
		state.SearchQueries = state.FollowUpQueries
	}

	return state, nil
}

func (r *runner) nodeFinalizeAnswer(ctx context.Context, state *AgentState) (*AgentState, error) {
	answerMsg, err := r.finalizeAnswer(ctx, state)
	if err != nil {
		return nil, fmt.Errorf("finalize answer failed: %w", err)
	}

	state.Messages = append(state.Messages, answerMsg)

	if sink, ok := getEventSink(ctx); ok {
		sink.Emit(ctx, domain.AgentEvent{
			Type: domain.EventFinalizeAnswer,
			Payload: map[string]interface{}{
				"messages": []interface{}{
					map[string]string{
						"type":    "ai",
						"content": answerMsg.Content,
						"id":      answerMsg.ID,
					},
				},
			},
		})
	}

	return state, nil
}
