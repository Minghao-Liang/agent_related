package builtin

import "backend-go/internal/prompts"

type provider struct{}

func NewProvider() prompts.Provider {
	return &provider{}
}

func (p *provider) QueryWriterInstructions() string {
	return QueryWriterInstructions
}

func (p *provider) WebSearcherInstructions() string {
	return WebSearcherInstructions
}

func (p *provider) ReflectionInstructions() string {
	return ReflectionInstructions
}

func (p *provider) AnswerInstructions() string {
	return AnswerInstructions
}
