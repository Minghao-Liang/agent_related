package llm

import (
	"backend-go/internal/domain"
	"context"
)

type ChatLLM interface {
	Generate(ctx context.Context, messages []domain.Message, opts ...Option) (domain.Message, error)
}

type Option func(*Options)

type Options struct {
	Temperature float64
	Model       string
}

func WithTemperature(t float64) Option {
	return func(o *Options) {
		o.Temperature = t
	}
}

func WithModel(m string) Option {
	return func(o *Options) {
		o.Model = m
	}
}
