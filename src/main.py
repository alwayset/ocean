"""Ocean — Discovery engine for AI agent tools."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.discover import router as discover_router
from src.api.health import router as health_router
from src.api.tools import router as tools_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: could run initial crawl or warm caches
    yield
    # Shutdown: cleanup


app = FastAPI(
    title="Ocean",
    description="Discovery engine for AI agent tools. Find the right MCP, WebMCP, A2A, and OpenAPI tools with semantic search.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(discover_router)
app.include_router(tools_router)


@app.get("/")
async def root():
    return {
        "name": "Ocean",
        "version": "0.1.0",
        "description": "Semantic discovery engine for AI agent tools",
        "docs": "/docs",
        "endpoints": {
            "discover": "POST /v1/discover",
            "tools": "GET /v1/tools",
            "stats": "GET /v1/stats",
            "health": "GET /health",
        },
    }
