"""Generate embeddings for tool descriptions and search queries using Gemini."""

from google import genai

from src.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def embed_text(text: str) -> list[float]:
    """Embed a single text string using Gemini."""
    client = _get_client()
    result = client.models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config={"output_dimensionality": settings.embedding_dimensions},
    )
    return list(result.embeddings[0].values)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single batch using Gemini."""
    if not texts:
        return []
    client = _get_client()
    result = client.models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config={"output_dimensionality": settings.embedding_dimensions},
    )
    return [list(e.values) for e in result.embeddings]


async def embed_query(text: str) -> list[float]:
    """Embed a search query."""
    client = _get_client()
    result = client.models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config={"output_dimensionality": settings.embedding_dimensions},
    )
    return list(result.embeddings[0].values)


def build_tool_text(name: str, description: str, provider_domain: str = "") -> str:
    """Build the text to embed for a tool. Combines name + description + provider for richer signal."""
    parts = [f"Tool: {name}"]
    if provider_domain:
        parts.append(f"Provider: {provider_domain}")
    parts.append(f"Description: {description}")
    return "\n".join(parts)
