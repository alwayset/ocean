"""Seed list collector — gather known MCP server domains from public registries."""

import httpx


# Well-known MCP registries and lists to bootstrap from
SEED_SOURCES = [
    # Official MCP registry
    "https://registry.modelcontextprotocol.io",
    # awesome-mcp-servers GitHub raw list
    "https://raw.githubusercontent.com/punkpeye/awesome-mcp-servers/main/README.md",
]

# Manually curated seed domains of known MCP server providers
MANUAL_SEEDS = [
    "github.com",
    "slack.com",
    "notion.so",
    "linear.app",
    "stripe.com",
    "twilio.com",
    "sendgrid.com",
    "openai.com",
    "anthropic.com",
    "replicate.com",
    "huggingface.co",
    "supabase.com",
    "vercel.com",
    "cloudflare.com",
    "sentry.io",
    "datadog.com",
    "figma.com",
    "airtable.com",
    "zapier.com",
    "shopify.com",
    "google.com",
    "microsoft.com",
    "aws.amazon.com",
    "gitlab.com",
    "bitbucket.org",
    "jira.atlassian.com",
    "confluence.atlassian.com",
    "salesforce.com",
    "hubspot.com",
    "mailchimp.com",
    "twitch.tv",
    "discord.com",
    "spotify.com",
    "youtube.com",
    "reddit.com",
    "wikipedia.org",
    "stackoverflow.com",
]


async def collect_seed_domains() -> list[str]:
    """Collect a list of domains to crawl for MCP server declarations.

    In MVP, we start with manual seeds + scraping known registries.
    """
    domains = set(MANUAL_SEEDS)

    # Try to fetch from Smithery API for additional domains
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://smithery.ai/api/servers", params={"limit": 100})
            if resp.status_code == 200:
                data = resp.json()
                for server in data.get("servers", data if isinstance(data, list) else []):
                    if isinstance(server, dict):
                        url = server.get("url", "") or server.get("homepage", "")
                        if url:
                            # Extract domain from URL
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            if parsed.hostname:
                                domains.add(parsed.hostname)
    except Exception:
        pass  # Smithery API may not be publicly available; fall back to manual seeds

    return sorted(domains)
