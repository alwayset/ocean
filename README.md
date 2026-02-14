# Ocean

Semantic discovery engine for AI agent tools. Crawls, indexes, and ranks tools from MCP, WebMCP, A2A, and OpenAPI — so agents can find the right tool at runtime.

## The Problem

WebMCP and MCP are creating thousands of agent-callable tools on the web. But there's no discovery layer — agents have to know which website to visit or which MCP server to connect to. The specs themselves acknowledge this gap.

Ocean fills it.

## What This Does

```
POST /v1/discover
{
  "intent": "send an email with attachments",
  "constraints": { "protocol": "mcp" }
}

→ Ranked list of tools matching your intent, with schemas ready for invocation
```

## Quick Start

```bash
# Clone and setup
cp .env.example .env  # Add your GEMINI_API_KEY

# Start services
docker compose up -d

# Run migrations
alembic upgrade head

# Seed and crawl
python -m src.cli crawl

# API is at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/discover` | POST | Semantic search — find tools by intent |
| `/v1/tools` | GET | Browse all indexed tools |
| `/v1/tools/{id}` | GET | Tool details + schema |
| `/v1/stats` | GET | Index statistics |
| `/health` | GET | Health check |

## Architecture

```
Crawler → Tool Index (Postgres + pgvector) → Discovery API → Agent
```

- **Crawler**: Discovers tools from `.well-known/mcp/server.json` endpoints
- **Index**: Stores tool metadata + Gemini embedding vectors
- **Discovery API**: Semantic search via pgvector cosine similarity
- **Coming soon**: WebMCP page scanning, A2A agent card indexing, quality monitoring, web dashboard

## Development

```bash
pip install -e ".[dev]"
pytest
```
