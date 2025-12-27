package config

type ModelConfig struct {
	BaseURL             string
	APIKey              string
	QueryGeneratorModel string
	ReflectionModel     string
	AnswerModel         string
	TemperatureQuery    float64
	TemperatureReflect  float64
	TemperatureAnswer   float64
	MaxRetries          int
}
