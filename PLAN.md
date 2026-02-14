# Google for Agent — Product & Technical Plan

## Executive Summary

**Google for Agent** is a discovery engine that lets AI agents find the right tools and services at runtime. It crawls, indexes, ranks, and serves tool descriptions from multiple protocols (WebMCP, MCP, A2A, OpenAPI) through a single semantic search API.

**Core thesis:** WebMCP and MCP are creating an explosion of agent-callable tools on the web. Discovery is the missing layer — the spec authors acknowledge it. Whoever builds the canonical discovery infrastructure owns the "attention layer" of the agent economy.

---

## 1. Why Now

### The Discovery Gap

| Protocol | Discovery mechanism | Status |
|----------|-------------------|--------|
| WebMCP | None — agent must visit the page | Spec explicitly says "search engines or directories might fill this gap" |
| MCP | `.well-known/mcp/server.json` — decentralized, no aggregator | Preview, no ranking/quality |
| A2A | `.well-known/agent-card.json` — decentralized | Production-ready, no aggregator |
| OpenAPI | Manual integration | Mature but no agent-native discovery |

### Competitive Landscape

| Player | What they do | Gap |
|--------|-------------|-----|
| Official MCP Registry | Minimal metadata store | No UX, no quality signals, no search |
| Smithery (7,300 tools) | MCP directory + hosting | Human-browsable, not agent-native |
| Glama | MCP directory + quality scores | Single protocol, no runtime API |
| PulseMCP (8,230 servers) | MCP directory | Listing only, no semantic search |
| RapidAPI (dead) | API marketplace | Disintermediation killed it |
| ChatGPT Plugin Store (dead) | LLM plugin marketplace | Bad discovery, bad economics |
| GPT Store | Custom GPT marketplace | No creator economics, closed ecosystem |
| AWS/Google Cloud Marketplaces | Enterprise procurement | Not agent-native, enterprise-only |

**What nobody has:**
1. Cross-protocol discovery (WebMCP + MCP + A2A + OpenAPI in one index)
2. Agent-native runtime API (semantic intent → ranked tools)
3. Quality signals at scale (reliability, latency, accuracy monitoring)
4. Economic model that works (learned from RapidAPI/GPT Store failures)

---

## 2. Product Vision

### For Agents (Demand Side)
```
POST /v1/discover
{
  "intent": "book_hotel",
  "constraints": {
    "location": "Tokyo",
    "check_in": "2026-04-01",
    "optimize": "price",
    "protocols": ["mcp", "webmcp"],
    "min_reliability": 0.95
  }
}

→ [
    {
      "provider": "booking.com",
      "tool": "searchHotels",
      "protocol": "webmcp",
      "reliability": 0.97,
      "avg_latency_ms": 1200,
      "coverage_score": 0.95,
      "verified": true,
      "endpoint": "https://booking.com/.well-known/webmcp",
      "schema": { ... }
    },
    ...
  ]
```

Agents call our API with a semantic intent. We return ranked, quality-scored tools they can immediately invoke. One API call replaces "guess which website to visit."

### For Tool Providers (Supply Side)
- **Auto-discovery:** We crawl and index your tools automatically. You don't need to register.
- **Claim & enhance:** Verify ownership, add metadata, see analytics.
- **Promoted placement:** Pay to rank higher for specific intents (the business model).
- **Quality dashboard:** See your reliability score, latency percentiles, error rates vs competitors.

### For Developers (Builder Side)
- **SDK:** `pip install agentfind` / `npm install agentfind`
- **One-line integration:** `tools = agentfind.discover("book hotel in Tokyo")`
- **Framework plugins:** LangChain, CrewAI, AutoGen, Semantic Kernel integrations.

---

## 3. Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Agent / Developer                     │
│              (SDK / REST API / Dashboard)                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Discovery API                          │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │  Semantic    │ │   Ranking    │ │   Result         │  │
│  │  Search      │ │   Engine     │ │   Formatting     │  │
│  │  (pgvector)  │ │  (quality +  │ │  (protocol-aware)│  │
│  │             │ │   relevance) │ │                  │  │
│  └─────────────┘ └──────────────┘ └──────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    Tool Index                            │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  PostgreSQL + pgvector                              │ │
│  │  - tools (name, desc, schema, protocol, provider)   │ │
│  │  - embeddings (tool description vectors)            │ │
│  │  - quality_metrics (uptime, latency, error_rate)    │ │
│  │  - providers (domain, verified, metadata)           │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       ▲
                       │
┌─────────────────────────────────────────────────────────┐
│                    Crawler Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │  MCP      │ │  A2A     │ │  WebMCP  │ │  OpenAPI   │  │
│  │  Crawler  │ │  Crawler │ │  Crawler │ │  Crawler   │  │
│  │ .well-    │ │ .well-   │ │ page     │ │ specs from │  │
│  │ known/mcp │ │ known/   │ │ scanning │ │ APIs.guru  │  │
│  │           │ │ agent-   │ │          │ │ + manual   │  │
│  │           │ │ card     │ │          │ │            │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API Server | Python + FastAPI | Fast to prototype, async-native, great for ML pipelines |
| Database | PostgreSQL + pgvector | Vector search without separate infra (Pinecone etc.) |
| Embeddings | OpenAI `text-embedding-3-small` | Best cost/quality ratio, switch to local later |
| Crawler | Python async (httpx) | Async HTTP for parallel crawling |
| Task Queue | Redis + Celery (or arq) | Scheduled crawling, background jobs |
| Frontend | Next.js | Dashboard + public directory |
| Cache | Redis | API response caching, rate limiting |
| Deployment | Docker Compose → fly.io/Railway | Start simple, scale later |

### Database Schema (Core)

```sql
-- Tool providers (domains/companies)
CREATE TABLE providers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain      TEXT UNIQUE NOT NULL,
    name        TEXT,
    verified    BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Discovered tools
CREATE TABLE tools (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES providers(id),
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    protocol    TEXT NOT NULL CHECK (protocol IN ('mcp', 'webmcp', 'a2a', 'openapi')),
    input_schema JSONB,
    output_schema JSONB,
    endpoint    TEXT,
    metadata    JSONB DEFAULT '{}',
    embedding   vector(1536),
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    last_seen   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(provider_id, name, protocol)
);

-- Quality metrics (time-series, aggregated)
CREATE TABLE quality_metrics (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id     UUID REFERENCES tools(id),
    measured_at TIMESTAMPTZ DEFAULT now(),
    uptime      FLOAT,          -- 0-1, rolling 7-day
    avg_latency_ms INTEGER,
    p95_latency_ms INTEGER,
    error_rate  FLOAT,          -- 0-1, rolling 7-day
    sample_count INTEGER
);

-- Search/usage analytics
CREATE TABLE search_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query       TEXT NOT NULL,
    intent      TEXT,
    results     JSONB,
    selected_tool_id UUID REFERENCES tools(id),
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Vector similarity index
CREATE INDEX ON tools USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

## 4. MVP Scope (v0.1)

**Goal:** Prove that semantic tool discovery works and agents find it useful.

### What's IN

1. **MCP Server Crawler**
   - Crawl domains for `.well-known/mcp/server.json`
   - Seed list: scrape Smithery, PulseMCP, awesome-mcp-servers for known domains
   - Index tool name, description, input/output schema
   - Run on schedule (daily)

2. **Tool Index**
   - PostgreSQL + pgvector
   - Embed tool descriptions using OpenAI embeddings
   - Basic provider deduplication

3. **Discovery API** (`/v1/discover`)
   - Input: natural language intent + optional filters
   - Process: embed intent → vector similarity search → rank by relevance
   - Output: ranked list of tools with schemas
   - Rate-limited, API key auth

4. **Python SDK**
   - `pip install agentfind`
   - `agentfind.discover("send email")` → list of tools
   - `agentfind.tool_info("tool_id")` → full schema

5. **Basic Web Dashboard**
   - Browse all indexed tools
   - Search tools
   - View tool details + schema
   - Stats: total tools indexed, protocols breakdown

### What's OUT (v0.1)

- WebMCP crawling (requires headless browser, complex)
- A2A crawling (smaller ecosystem for now)
- OpenAPI crawling (large scope)
- Quality monitoring/scoring (need traffic first)
- Provider accounts / claiming
- Promoted placement / monetization
- Framework integrations (LangChain etc.)

---

## 5. Implementation Plan

### Phase 1: Foundation ✅
- [x] Project setup, git init
- [x] FastAPI app scaffold with config, logging, error handling
- [x] PostgreSQL + pgvector schema, migrations (Alembic)
- [x] Docker Compose (api + postgres + redis)
- [x] Basic health check endpoint

### Phase 2: Crawler ✅
- [x] Seed list collector — 37 domains from manual + Smithery
- [x] MCP `.well-known` crawler — async HTTP with concurrency control
- [x] Tool parser — extract tools from server.json, normalize schema
- [x] Embedding pipeline — Gemini `gemini-embedding-001` → 768-dim (Matryoshka truncation)
- [x] Store in database with deduplication (upsert logic)
- [x] Celery task for scheduled re-crawl (config ready)
- [x] Seed data — 15 curated providers, 59 tools

### Phase 3: Discovery API ✅
- [x] `/v1/discover` endpoint — intent embedding + pgvector cosine similarity
- [x] Result ranking — vector similarity with HNSW index
- [x] Filtering — by protocol, provider
- [x] `/v1/tools/{id}` — tool detail endpoint
- [x] `/v1/tools` — list/browse with pagination
- [x] `POST /v1/tools` — tool registration endpoint (providers can submit tools)
- [ ] API key management — simple key generation + rate limiting

### Phase 4: SDK + Dashboard ✅
- [x] Python SDK (`ocean-sdk` package) — `ocean_sdk.discover("send email")` → tools
- [x] CLI — `python -m src.cli search|crawl|seed|stats`
- [x] Next.js dashboard — browse, search, tool detail, stats pages
- [x] Landing page — feature cards, search box, curl example
- [ ] Deploy to fly.io or Railway

### Phase 5: Growth + Quality (Next)
- [ ] WebMCP crawler (headless Chrome, parse `navigator.modelContext` registrations)
- [ ] Quality monitoring — periodic tool health checks
- [ ] Provider claiming + verification
- [ ] Framework integrations (LangChain, CrewAI)
- [ ] Usage analytics + search quality metrics
- [ ] API key management + rate limiting

---

## 6. Business Model (Post-MVP)

### Revenue Streams

| Stream | Description | When |
|--------|------------|------|
| **Free tier** | 1,000 API calls/month, basic search | Day 1 |
| **Pro tier** | 50K calls/month, priority results, analytics | Month 3 |
| **Promoted placement** | Tool providers bid on intent keywords | Month 6 |
| **CPA (cost per action)** | Commission on transactions via discovered tools | Month 9+ |
| **Enterprise** | Private registry, custom ranking, SLA | Month 6+ |

### Why We Won't Be RapidAPI

RapidAPI failed because:
1. Developers bypassed the middleman after discovery (disintermediation)
2. The 20% commission was unjustifiable

Our model is different:
1. **We don't sit in the execution path** — agents call tools directly after discovery. No lock-in, no commission on usage.
2. **Revenue comes from attention, not execution** — like Google makes money from ads, not from hosting the websites.
3. **Network effect is on data, not users** — our quality signals improve with usage, making rankings more valuable.

---

## 7. Key Metrics

| Metric | Target (Month 1) | Target (Month 6) |
|--------|------------------|------------------|
| Tools indexed | 5,000+ | 50,000+ |
| Protocols covered | MCP | MCP + WebMCP + A2A |
| API calls/day | 100 | 10,000 |
| Search relevance (top-3 hit rate) | 70% | 90% |
| Unique API keys | 50 | 1,000 |
| Avg API latency | <500ms | <200ms |

---

## 8. Open Questions

1. **Embedding model choice** — Start with OpenAI for quality, switch to local (e5-small, BGE) for cost?
2. **Crawl ethics** — Should we respect robots.txt for `.well-known` paths? (Probably yes for pages, debatable for well-known)
3. **Schema compatibility scoring** — How to rank tools based on whether their input schema matches what the agent has available?
4. **Multi-protocol normalization** — How to present MCP tools and WebMCP tools in a unified result format?
5. **Trust bootstrapping** — Before we have usage data, how to estimate tool quality? (Provider reputation? GitHub stars? Community ratings?)

---

## 9. File Structure (MVP)

```
google-for-agent/
├── PLAN.md                  # This document
├── README.md                # Public README
├── docker-compose.yml       # Local dev environment
├── Dockerfile               # API server image
├── pyproject.toml           # Python project config
├── alembic.ini              # DB migration config
├── alembic/                 # DB migrations
│   └── versions/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings (env vars)
│   ├── db.py                # Database connection
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   ├── tool.py
│   │   └── quality.py
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── discover.py      # /v1/discover
│   │   ├── tools.py         # /v1/tools
│   │   └── health.py        # /health
│   ├── crawler/             # Crawler modules
│   │   ├── __init__.py
│   │   ├── mcp.py           # MCP .well-known crawler
│   │   ├── seed.py          # Seed list collector
│   │   └── scheduler.py     # Crawl scheduling
│   ├── search/              # Search engine
│   │   ├── __init__.py
│   │   ├── embeddings.py    # Embedding generation
│   │   └── ranking.py       # Result ranking
│   └── sdk/                 # Python SDK (published separately)
│       ├── __init__.py
│       └── client.py
├── tests/
│   ├── test_api.py
│   ├── test_crawler.py
│   └── test_search.py
└── web/                     # Next.js dashboard (later)
    └── ...
```
