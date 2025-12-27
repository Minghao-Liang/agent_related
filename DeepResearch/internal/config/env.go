package config

import (
	"os"
	"strconv"
)

func Load() *ModelConfig {
	return &ModelConfig{
		BaseURL:             getEnv("BASE_URL", "https://api.moonshot.cn/v1"),
		APIKey:              getEnv("KIMI_API_KEY", "KIMI_API_KEY"),
		QueryGeneratorModel: getEnv("QUERY_GENERATOR_MODEL", "kimi-k2-0905-preview"),
		ReflectionModel:     getEnv("REFLECTION_MODEL", "kimi-k2-0905-preview"),
		AnswerModel:         getEnv("ANSWER_MODEL", "kimi-k2-thinking"),
		TemperatureQuery:    getEnvFloat("TEMPERATURE_QUERY", 0),
		TemperatureReflect:  getEnvFloat("TEMPERATURE_REFLECT", 1.0),
		TemperatureAnswer:   getEnvFloat("TEMPERATURE_ANSWER", 0),
		MaxRetries:          getEnvInt("MAX_RETRIES", 3),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvFloat(key string, fallback float64) float64 {
	if v := os.Getenv(key); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil {
			return f
		}
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return fallback
}
