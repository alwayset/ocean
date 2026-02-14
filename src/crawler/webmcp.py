"""WebMCP crawler — discover tools exposed via navigator.modelContext on websites.

WebMCP (Chrome 146+) allows websites to expose tools to AI agents via:
  navigator.modelContext.registerTool({
    name: "searchProducts",
    description: "Search for products by query",
    inputSchema: { ... },
    handler: async (input) => { ... }
  })

This crawler uses headless Chrome to visit pages, detect WebMCP registrations,
and extract tool definitions for indexing.

Status: SKELETON — requires Playwright/Puppeteer installation for headless Chrome.
"""

import asyncio
import json
import logging
from urllib.parse import urlparse

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.provider import Provider
from src.models.tool import Tool
from src.search.embeddings import build_tool_text, embed_texts

logger = logging.getLogger(__name__)

# JavaScript to inject into pages to intercept WebMCP registrations
INTERCEPT_SCRIPT = """
(function() {
    var tools = [];
    window.__ocean_webmcp_tools = tools;

    function wrapRegisterTool(obj) {
        var orig = obj.registerTool;
        obj.registerTool = function(toolDef) {
            tools.push({
                name: toolDef.name || 'unnamed',
                description: toolDef.description || '',
                inputSchema: toolDef.inputSchema || null,
                outputSchema: toolDef.outputSchema || null,
            });
            if (orig) return orig.call(this, toolDef);
        };
        return obj;
    }

    var _mc = wrapRegisterTool({});
    try {
        Object.defineProperty(navigator, 'modelContext', {
            get: function() { return _mc; },
            set: function(val) {
                if (val && typeof val === 'object') {
                    wrapRegisterTool(val);
                }
                _mc = val;
            },
            configurable: true,
            enumerable: true
        });
    } catch(e) {
        if (!navigator.modelContext) {
            navigator.modelContext = _mc;
        } else {
            wrapRegisterTool(navigator.modelContext);
        }
    }
})();
"""

EXTRACT_SCRIPT = "() => JSON.stringify(window.__ocean_webmcp_tools || [])"


async def crawl_page_webmcp(page, url: str) -> list[dict]:
    """Visit a page with headless Chrome and extract WebMCP tool registrations.

    Args:
        page: Playwright page object
        url: URL to visit

    Returns:
        List of tool definitions found on the page
    """
    try:
        # Inject interceptor before page loads
        await page.add_init_script(INTERCEPT_SCRIPT)

        # Navigate to the page
        await page.goto(url, wait_until="networkidle", timeout=15000)

        # Wait a bit for any async registrations
        await asyncio.sleep(2)

        # Extract captured tools
        tools_json = await page.evaluate(EXTRACT_SCRIPT)
        tools = json.loads(tools_json)

        if tools:
            logger.info(f"Found {len(tools)} WebMCP tools at {url}")

        return tools

    except Exception as e:
        logger.debug(f"Error crawling {url} for WebMCP: {e}")
        return []


async def crawl_urls_webmcp(db: AsyncSession, urls: list[str]) -> dict:
    """Crawl a list of URLs for WebMCP tool registrations using Playwright.

    Requires: pip install playwright && playwright install chromium
    """
    stats = {
        "urls_crawled": 0,
        "urls_with_tools": 0,
        "tools_added": 0,
        "errors": 0,
    }

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: Playwright not installed. Run:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return stats

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Ocean-Crawler/0.1 (WebMCP Discovery Engine)"
        )

        for url in urls:
            page = await context.new_page()
            try:
                tools = await crawl_page_webmcp(page, url)
                stats["urls_crawled"] += 1

                if tools:
                    stats["urls_with_tools"] += 1
                    domain = urlparse(url).hostname or url

                    # Get or create provider
                    from src.db import async_session
                    async with async_session() as batch_db:
                        stmt = select(Provider).where(Provider.domain == domain)
                        provider = (await batch_db.execute(stmt)).scalar_one_or_none()
                        if provider is None:
                            provider = Provider(
                                domain=domain,
                                name=domain,
                                homepage_url=url,
                            )
                            batch_db.add(provider)
                            await batch_db.flush()

                        # Embed and store tools
                        texts = [
                            build_tool_text(t["name"], t["description"], domain)
                            for t in tools
                        ]
                        embeddings = await embed_texts(texts)

                        for tool_data, embedding in zip(tools, embeddings):
                            stmt = select(Tool).where(
                                Tool.provider_id == provider.id,
                                Tool.name == tool_data["name"],
                                Tool.protocol == "webmcp",
                            )
                            existing = (await batch_db.execute(stmt)).scalar_one_or_none()

                            if existing:
                                existing.description = tool_data["description"] or existing.description
                                existing.input_schema = tool_data["inputSchema"]
                                existing.embedding = embedding
                                existing.last_seen = func.now()
                            else:
                                tool = Tool(
                                    provider_id=provider.id,
                                    name=tool_data["name"],
                                    description=tool_data["description"] or tool_data["name"],
                                    protocol="webmcp",
                                    input_schema=tool_data["inputSchema"],
                                    endpoint=url,
                                    embedding=embedding,
                                    metadata_={
                                        "source": "webmcp_crawl",
                                        "page_url": url,
                                    },
                                )
                                batch_db.add(tool)
                                stats["tools_added"] += 1

                        await batch_db.commit()

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                stats["errors"] += 1
            finally:
                await page.close()

        await browser.close()

    return stats
