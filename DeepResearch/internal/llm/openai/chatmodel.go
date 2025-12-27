package openai

import (
	"backend-go/internal/domain"
	"backend-go/internal/llm"
	"context"

	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/schema"
)

type ChatModel struct {
	baseUrl string
	apiKey  string
}

func NewChatModel(baseUrl, apiKey string) *ChatModel {
	return &ChatModel{
		baseUrl: baseUrl,
		apiKey:  apiKey,
	}
}

func (c *ChatModel) Generate(ctx context.Context, messages []domain.Message, opts ...llm.Option) (domain.Message, error) {
	options := &llm.Options{
		Temperature: 0,
		Model:       "kimi-k2-0905-preview", // default
	}
	for _, o := range opts {
		o(options)
	}

	// Create Eino OpenAI ChatModel
	chatModel, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
		BaseURL:     c.baseUrl,
		APIKey:      c.apiKey,
		Model:       options.Model,
		Temperature: func() *float32 { f := float32(options.Temperature); return &f }(),
	})
	if err != nil {
		return domain.Message{}, err
	}

	// Convert messages
	var einoMsgs []*schema.Message
	for _, m := range messages {
		role := schema.User
		switch m.Role {
		case domain.RoleSystem:
			role = schema.System
		case domain.RoleAI:
			role = schema.Assistant
		}
		einoMsgs = append(einoMsgs, &schema.Message{
			Role:    role,
			Content: m.Content,
		})
	}

	resp, err := chatModel.Generate(ctx, einoMsgs)
	if err != nil {
		return domain.Message{}, err
	}

	return domain.Message{
		Role:    domain.RoleAI,
		Content: resp.Content,
	}, nil
}
