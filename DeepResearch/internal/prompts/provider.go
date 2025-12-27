package prompts

type Provider interface {
	QueryWriterInstructions() string
	WebSearcherInstructions() string
	ReflectionInstructions() string
	AnswerInstructions() string
}
