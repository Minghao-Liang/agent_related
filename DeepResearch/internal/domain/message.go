package domain

type Role string

const (
	RoleSystem Role = "system"
	RoleUser   Role = "user"
	RoleAI     Role = "ai"
)

type Message struct {
	Role    Role   `json:"type"`
	Content string `json:"content"`
	ID      string `json:"id,omitempty"`
}
