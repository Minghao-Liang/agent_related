# langgraph-mcp

An example project that integrates an MCP (Model Context Protocol) "Perception Tools" server with a LangChain Agent. It includes:
- A versatile MCP server (`perception-tools/server.py`) offering web/document/media parsing, search, public/private data sources, and filesystem operations
- An interactive agent (`agent.py`) that loads MCP tools automatically and uses an LLM to drive conversation and tool calls

## Project Structure

```
tool/langgraph-mcp/
├─ agent.py                     # Interactive agent entry; loads MCP tools and chats
├─ requirements.txt             # Project dependencies
└─ perception-tools/            # MCP server and tool implementations
   ├─ server.py                 # MCP server registering all tools
   ├─ search_tools.py           # General search and file download
   ├─ multimodal_tools.py       # Web, document, image, video parsing
   ├─ filesystem_tools.py       # File read, grep search, text summarization
   ├─ public_data_tools.py      # Weather, FX, Wikipedia, ArXiv, Wayback
   ├─ private_data_tools.py     # Google Calendar, Notion (optional)
   ├─ pubchem_tools.py          # PubChem chemical data
   ├─ yahoo_finance_tools.py    # Yahoo Finance quotes and financials
   ├─ document_processing_tools.py  # PDF/DOCX/PPTX/CSV extraction
   ├─ media_processing_tools.py     # Audio transcription, OCR, image/video analysis
   ├─ google_search_enhanced.py     # Google CSE API (DuckDuckGo fallback)
   ├─ wiki_enhanced.py, arxiv_enhanced.py, wayback_enhanced.py
   └─ __init__.py
```

## Requirements

- Python 3.10+ (recommended 3.11)
- Network access (many tools require internet)
- Optional system dependencies:
  - OCR: `tesseract-ocr` (if enabling `pytesseract`)

## Installation

Create a virtual environment and install dependencies:

```bash
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r tool/langgraph-mcp/requirements.txt
```

## Environment Variables

Store secrets in `.env` or export them before running:

- `KIMI_API_KEY`: required for Moonshot API (used in `agent.py`)
- Optional: `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` (enable Google Custom Search)

Example `.env`:

```
KIMI_API_KEY=your_moonshot_key_here
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id
```

## Run the Interactive Agent

`agent.py` will start the MCP server (`perception-tools/server.py`) as a subprocess and load all tools:

```bash
python tool/langgraph-mcp/agent.py
```

Type natural language commands to chat with the agent. Type `exit` or `quit` to leave.

### Example Prompts

- "Search recent news about OpenAI and provide links"
- "Read pages 1–3 of this PDF and summarize key points"
- "Parse this image and describe the scene"
- "Query AAPL latest stock price and company info"
- "Compress this long text into a 300-word summary"

## Tool Overview (Partial)

- Search & Web: `web_search`, `google_search_enhanced`, `webpage_reader`
- Document Parsing: `document_reader`, `pdf_extract`, `docx_extract`, `pptx_extract`, `csv_parse`
- Media Processing: `image_parser`, `video_parser`, `audio_transcribe`, `image_ocr`, `image_analyze`, `video_analyze`
- Filesystem: `file_reader`, `grep`, `text_summarizer`
- Public Data: `weather`, `currency_converter`, `wikipedia_search`, `arxiv_search`, `wayback_search`
- Stocks & Financials: `stock_price`, `yfinance_quote`, `yfinance_historical`, `yfinance_company_info`, `yfinance_financials`
- Chemistry: `pubchem_search`, `pubchem_properties`, `pubchem_synonyms`, `pubchem_similar`

See `perception-tools/server.py` for full tool list and parameters.

## Model & Endpoint Configuration

`agent.py` uses Moonshot Kimi by default:

- `model_name="kimi-k2-0905-preview"`
- `base_url="https://api.moonshot.cn/v1"`
- `api_key` is read from `KIMI_API_KEY`

To switch model or provider, edit the initialization parameters in `agent.py`.

## Design & Workflow

- The agent is built via LangChain `create_agent` and prefers tool-first operations for retrieval/parsing/computation
- Each interaction prints "Tools used" for observability of tool calls
- The MCP server uses `FastMCP` to register tools with typed parameters and documented behavior

## Troubleshooting

- Missing `KIMI_API_KEY`: model calls will fail; set it in environment or `.env`
- Google search not configured: falls back to DuckDuckGo; results may be limited or unstable
- OCR errors: ensure `tesseract-ocr` and language packs are installed
- Encoding issues: adjust the `encoding` parameter when reading local files (default `utf-8`)

## Credits

- The `perception-tools` directory is referenced from `https://github.com/bojieli/ai-agent-book-projects`.