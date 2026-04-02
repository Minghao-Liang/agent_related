# miniCoder

**miniCoder** is a lightweight, interactive AI coding assistant CLI powered by large language models. It acts as an autonomous pair-programmer directly in your terminal, equipped with tools to inspect files, run shell commands, and write or edit code.

## Features

- **Interactive CLI**: A conversational interface to collaborate with the AI.
- **Tool Usage**: The AI can autonomously run bash commands, read/write/edit files, search (glob/grep), and fetch web pages to complete tasks.
- **Multi-Model Support**: Works out of the box with Claude models, as well as compatible providers like MiniMax, GLM (Zhipu), Kimi (Moonshot), and DeepSeek.
- **Rich Console UI**: Utilizes `rich` for beautifully formatted terminal output and live streaming responses.
- **Session Management**: Built-in slash commands to manage conversation history and track token usage/costs.

## Installation

miniCoder uses `uv` for fast, reliable Python environment management.

1. Clone or download the repository.
2. Install `uv` if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

### Requirements
- Python 3.8+
- `anthropic>=0.25.0`
- `python-dotenv>=1.0.0`
- `rich>=13.7.0`

## Configuration

miniCoder uses a `.env` file for configuration. Copy the provided `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit the `.env` file to set your API key and preferred model:

```env
ANTHROPIC_API_KEY=your-api-key-here
MODEL_ID=claude-sonnet-4-6
```

### Supported Providers

miniCoder supports any compatible API endpoint. You can configure this by setting the `ANTHROPIC_BASE_URL` and `MODEL_ID` in your `.env` file. Some supported alternatives include:

- **MiniMax** (`MiniMax-M2.5`)
- **GLM / Zhipu** (`glm-5`)
- **Kimi / Moonshot** (`kimi-k2.5`)
- **DeepSeek** (`deepseek-chat`)

*(See `.env.example` for detailed configuration URLs for different regions).*

### Other Environment Variables

- `MINICODER_WORKDIR`: The working directory for the agent (defaults to the current working directory).
- `MINICODER_MAX_TURNS`: The maximum number of agent turns per request to prevent infinite loops (defaults to 16).

## Usage

Start the interactive loop by running:

```bash
python agent_loop.py
```

Once running, you can simply type your request (e.g., *"Write a Python script to scrape a website"*, or *"Find all TODOs in the codebase"*). The AI will use its tools to accomplish the task and report back.

### Slash Commands

Inside the miniCoder CLI, you can use the following commands:

- `/help` - Show available commands
- `/clear` - Clear conversation history and reset token counters
- `/cost` - Show session turn and token usage (input/output/total)
- `/exit` or `/quit` - Exit the application

## Built-in Tools

miniCoder empowers the AI with the following tools:

- `bash`: Run a shell command in the working directory (with basic safety blocks).
- `read_file`: Read a UTF-8 text file.
- `write_file`: Write text content to a new or existing file.
- `file_edit`: Replace specific text in a file.
- `glob`: Find files matching a pattern (supports `**`).
- `grep`: Regex search across files within the working directory.
- `web_fetch`: Fetch text content from a URL.

## License

[MIT](LICENSE)
