package prompts

import (
	"fmt"
	"strings"
)

func Render(template string, vars map[string]interface{}) string {
	result := template
	for k, v := range vars {
		key := "{" + k + "}"
		valStr := fmt.Sprintf("%v", v)
		result = strings.ReplaceAll(result, key, valStr)
	}
	return result
}
