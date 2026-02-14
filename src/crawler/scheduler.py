"""Celery tasks for scheduled crawling."""

from celery import Celery

from src.config import settings

app = Celery("agentfind", broker=settings.redis_url)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "crawl-mcp-servers": {
            "task": "src.crawler.scheduler.crawl_all",
            "schedule": settings.crawl_interval_hours * 3600,
        },
    },
)


@app.task
def crawl_all():
    """Run a full crawl of all known domains. Invoked by Celery beat."""
    import asyncio
    asyncio.run(_crawl_all_async())


async def _crawl_all_async():
    from src.crawler.mcp import crawl_domains
    from src.crawler.seed import collect_seed_domains
    from src.db import async_session

    domains = await collect_seed_domains()
    async with async_session() as db:
        stats = await crawl_domains(db, domains)
    return stats
