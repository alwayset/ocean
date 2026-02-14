"""Seed the database with real MCP tool data from public registries."""

import asyncio
import json

import httpx
from sqlalchemy import select

from src.config import settings
from src.db import async_session
from src.models.provider import Provider
from src.models.tool import Tool
from src.search.embeddings import build_tool_text, embed_texts

# Curated list of well-known MCP servers with their tools
# Sourced from smithery.ai and awesome-mcp-servers
SEED_SERVERS = [
    {
        "domain": "github.com",
        "name": "GitHub",
        "description": "GitHub MCP server for repository management",
        "tools": [
            {"name": "create_repository", "description": "Create a new GitHub repository with specified name, description, and visibility settings", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "private": {"type": "boolean"}}, "required": ["name"]}},
            {"name": "search_repositories", "description": "Search for GitHub repositories by keyword, language, or topic", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "language": {"type": "string"}, "sort": {"type": "string", "enum": ["stars", "forks", "updated"]}}, "required": ["query"]}},
            {"name": "create_issue", "description": "Create a new issue in a GitHub repository", "input_schema": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}}, "required": ["owner", "repo", "title"]}},
            {"name": "create_pull_request", "description": "Create a pull request to merge changes between branches", "input_schema": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}, "head": {"type": "string"}, "base": {"type": "string"}}, "required": ["owner", "repo", "title", "head", "base"]}},
            {"name": "get_file_contents", "description": "Read the contents of a file from a GitHub repository", "input_schema": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "path": {"type": "string"}}, "required": ["owner", "repo", "path"]}},
            {"name": "list_commits", "description": "List recent commits in a GitHub repository", "input_schema": {"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "sha": {"type": "string"}}, "required": ["owner", "repo"]}},
        ],
    },
    {
        "domain": "slack.com",
        "name": "Slack",
        "description": "Slack MCP server for messaging and channel management",
        "tools": [
            {"name": "send_message", "description": "Send a message to a Slack channel or direct message", "input_schema": {"type": "object", "properties": {"channel": {"type": "string"}, "text": {"type": "string"}}, "required": ["channel", "text"]}},
            {"name": "list_channels", "description": "List all public Slack channels in the workspace", "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
            {"name": "search_messages", "description": "Search for messages across Slack channels by keyword", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "count": {"type": "integer"}}, "required": ["query"]}},
            {"name": "get_channel_history", "description": "Retrieve recent message history from a Slack channel", "input_schema": {"type": "object", "properties": {"channel": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["channel"]}},
        ],
    },
    {
        "domain": "notion.so",
        "name": "Notion",
        "description": "Notion MCP server for workspace and page management",
        "tools": [
            {"name": "search_pages", "description": "Search for pages in a Notion workspace by title or content", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
            {"name": "create_page", "description": "Create a new page in Notion with title and content blocks", "input_schema": {"type": "object", "properties": {"parent_id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}}, "required": ["title"]}},
            {"name": "update_page", "description": "Update an existing Notion page properties or content", "input_schema": {"type": "object", "properties": {"page_id": {"type": "string"}, "properties": {"type": "object"}}, "required": ["page_id"]}},
            {"name": "query_database", "description": "Query a Notion database with filters and sorts", "input_schema": {"type": "object", "properties": {"database_id": {"type": "string"}, "filter": {"type": "object"}, "sorts": {"type": "array"}}, "required": ["database_id"]}},
        ],
    },
    {
        "domain": "linear.app",
        "name": "Linear",
        "description": "Linear MCP server for issue tracking and project management",
        "tools": [
            {"name": "create_issue", "description": "Create a new issue in Linear with title, description, and priority", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "team_id": {"type": "string"}, "priority": {"type": "integer"}}, "required": ["title", "team_id"]}},
            {"name": "list_issues", "description": "List issues from Linear with optional filters by status, assignee, or project", "input_schema": {"type": "object", "properties": {"team_id": {"type": "string"}, "status": {"type": "string"}, "assignee": {"type": "string"}}}},
            {"name": "update_issue", "description": "Update an existing Linear issue status, priority, or assignee", "input_schema": {"type": "object", "properties": {"issue_id": {"type": "string"}, "status": {"type": "string"}, "priority": {"type": "integer"}}, "required": ["issue_id"]}},
            {"name": "search_issues", "description": "Search for Linear issues by keyword across all projects", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
        ],
    },
    {
        "domain": "stripe.com",
        "name": "Stripe",
        "description": "Stripe MCP server for payment processing and financial operations",
        "tools": [
            {"name": "create_payment_intent", "description": "Create a Stripe payment intent for processing a customer payment", "input_schema": {"type": "object", "properties": {"amount": {"type": "integer"}, "currency": {"type": "string"}, "customer": {"type": "string"}}, "required": ["amount", "currency"]}},
            {"name": "list_customers", "description": "List Stripe customers with optional search filters", "input_schema": {"type": "object", "properties": {"email": {"type": "string"}, "limit": {"type": "integer"}}}},
            {"name": "create_invoice", "description": "Create and send an invoice to a Stripe customer", "input_schema": {"type": "object", "properties": {"customer": {"type": "string"}, "items": {"type": "array"}}, "required": ["customer"]}},
            {"name": "get_balance", "description": "Retrieve the current Stripe account balance", "input_schema": {"type": "object", "properties": {}}},
            {"name": "list_transactions", "description": "List recent balance transactions with optional date filtering", "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}, "created_after": {"type": "string"}}}},
        ],
    },
    {
        "domain": "postgresql.org",
        "name": "PostgreSQL",
        "description": "PostgreSQL MCP server for database operations",
        "tools": [
            {"name": "query", "description": "Execute a read-only SQL query against a PostgreSQL database and return results", "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}, "params": {"type": "array"}}, "required": ["sql"]}},
            {"name": "execute", "description": "Execute a write SQL statement (INSERT, UPDATE, DELETE) on PostgreSQL", "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}, "params": {"type": "array"}}, "required": ["sql"]}},
            {"name": "list_tables", "description": "List all tables in the connected PostgreSQL database", "input_schema": {"type": "object", "properties": {"schema": {"type": "string"}}}},
            {"name": "describe_table", "description": "Get the column names, types, and constraints of a PostgreSQL table", "input_schema": {"type": "object", "properties": {"table_name": {"type": "string"}}, "required": ["table_name"]}},
        ],
    },
    {
        "domain": "google.com",
        "name": "Google Drive",
        "description": "Google Drive MCP server for file management and document operations",
        "tools": [
            {"name": "search_files", "description": "Search for files in Google Drive by name, type, or content", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "mime_type": {"type": "string"}}, "required": ["query"]}},
            {"name": "read_file", "description": "Read the contents of a file from Google Drive", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}}, "required": ["file_id"]}},
            {"name": "create_file", "description": "Create a new file in Google Drive with specified content and type", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "content": {"type": "string"}, "mime_type": {"type": "string"}}, "required": ["name", "content"]}},
            {"name": "share_file", "description": "Share a Google Drive file with specified users or make it public", "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}, "email": {"type": "string"}, "role": {"type": "string"}}, "required": ["file_id"]}},
        ],
    },
    {
        "domain": "sendgrid.com",
        "name": "SendGrid",
        "description": "SendGrid MCP server for email sending and management",
        "tools": [
            {"name": "send_email", "description": "Send an email via SendGrid with subject, body, and attachments", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "from": {"type": "string"}}, "required": ["to", "subject", "body"]}},
            {"name": "send_template_email", "description": "Send an email using a pre-defined SendGrid template with dynamic data", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "template_id": {"type": "string"}, "dynamic_data": {"type": "object"}}, "required": ["to", "template_id"]}},
            {"name": "list_templates", "description": "List all email templates available in SendGrid", "input_schema": {"type": "object", "properties": {}}},
        ],
    },
    {
        "domain": "sentry.io",
        "name": "Sentry",
        "description": "Sentry MCP server for error tracking and monitoring",
        "tools": [
            {"name": "list_issues", "description": "List unresolved error issues from Sentry with optional project filter", "input_schema": {"type": "object", "properties": {"project": {"type": "string"}, "query": {"type": "string"}}}},
            {"name": "get_issue_details", "description": "Get detailed information about a specific Sentry error issue", "input_schema": {"type": "object", "properties": {"issue_id": {"type": "string"}}, "required": ["issue_id"]}},
            {"name": "resolve_issue", "description": "Mark a Sentry issue as resolved", "input_schema": {"type": "object", "properties": {"issue_id": {"type": "string"}}, "required": ["issue_id"]}},
        ],
    },
    {
        "domain": "figma.com",
        "name": "Figma",
        "description": "Figma MCP server for design file inspection and data extraction",
        "tools": [
            {"name": "get_file", "description": "Get metadata and node tree of a Figma design file", "input_schema": {"type": "object", "properties": {"file_key": {"type": "string"}}, "required": ["file_key"]}},
            {"name": "get_components", "description": "List all components in a Figma file or team library", "input_schema": {"type": "object", "properties": {"file_key": {"type": "string"}}, "required": ["file_key"]}},
            {"name": "export_image", "description": "Export a node from a Figma file as PNG, SVG, or PDF", "input_schema": {"type": "object", "properties": {"file_key": {"type": "string"}, "node_id": {"type": "string"}, "format": {"type": "string", "enum": ["png", "svg", "pdf"]}}, "required": ["file_key", "node_id"]}},
        ],
    },
    {
        "domain": "supabase.com",
        "name": "Supabase",
        "description": "Supabase MCP server for database, auth, and storage operations",
        "tools": [
            {"name": "query_table", "description": "Query data from a Supabase table with filters, pagination, and ordering", "input_schema": {"type": "object", "properties": {"table": {"type": "string"}, "select": {"type": "string"}, "filter": {"type": "object"}, "limit": {"type": "integer"}}, "required": ["table"]}},
            {"name": "insert_row", "description": "Insert a new row into a Supabase table", "input_schema": {"type": "object", "properties": {"table": {"type": "string"}, "data": {"type": "object"}}, "required": ["table", "data"]}},
            {"name": "upload_file", "description": "Upload a file to Supabase Storage bucket", "input_schema": {"type": "object", "properties": {"bucket": {"type": "string"}, "path": {"type": "string"}, "file": {"type": "string"}}, "required": ["bucket", "path", "file"]}},
            {"name": "list_users", "description": "List authenticated users from Supabase Auth", "input_schema": {"type": "object", "properties": {"page": {"type": "integer"}, "per_page": {"type": "integer"}}}},
        ],
    },
    {
        "domain": "cloudflare.com",
        "name": "Cloudflare",
        "description": "Cloudflare MCP server for DNS, Workers, and CDN management",
        "tools": [
            {"name": "list_zones", "description": "List all DNS zones managed by Cloudflare", "input_schema": {"type": "object", "properties": {}}},
            {"name": "create_dns_record", "description": "Create a new DNS record in a Cloudflare zone", "input_schema": {"type": "object", "properties": {"zone_id": {"type": "string"}, "type": {"type": "string"}, "name": {"type": "string"}, "content": {"type": "string"}}, "required": ["zone_id", "type", "name", "content"]}},
            {"name": "deploy_worker", "description": "Deploy a Cloudflare Worker script", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "script": {"type": "string"}}, "required": ["name", "script"]}},
            {"name": "purge_cache", "description": "Purge cached content from Cloudflare CDN for a zone", "input_schema": {"type": "object", "properties": {"zone_id": {"type": "string"}, "urls": {"type": "array"}}, "required": ["zone_id"]}},
        ],
    },
    {
        "domain": "twilio.com",
        "name": "Twilio",
        "description": "Twilio MCP server for SMS, voice, and communication APIs",
        "tools": [
            {"name": "send_sms", "description": "Send an SMS text message via Twilio to a phone number", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "body": {"type": "string"}, "from": {"type": "string"}}, "required": ["to", "body"]}},
            {"name": "make_call", "description": "Initiate a phone call via Twilio with TwiML instructions", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "from": {"type": "string"}, "twiml": {"type": "string"}}, "required": ["to", "twiml"]}},
            {"name": "list_messages", "description": "List recent SMS messages sent or received via Twilio", "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}, "to": {"type": "string"}}}},
        ],
    },
    {
        "domain": "airtable.com",
        "name": "Airtable",
        "description": "Airtable MCP server for spreadsheet-database operations",
        "tools": [
            {"name": "list_records", "description": "List records from an Airtable base table with optional filtering and sorting", "input_schema": {"type": "object", "properties": {"base_id": {"type": "string"}, "table_name": {"type": "string"}, "filter": {"type": "string"}, "sort": {"type": "array"}}, "required": ["base_id", "table_name"]}},
            {"name": "create_record", "description": "Create a new record in an Airtable table", "input_schema": {"type": "object", "properties": {"base_id": {"type": "string"}, "table_name": {"type": "string"}, "fields": {"type": "object"}}, "required": ["base_id", "table_name", "fields"]}},
            {"name": "update_record", "description": "Update fields of an existing Airtable record", "input_schema": {"type": "object", "properties": {"base_id": {"type": "string"}, "table_name": {"type": "string"}, "record_id": {"type": "string"}, "fields": {"type": "object"}}, "required": ["base_id", "table_name", "record_id", "fields"]}},
        ],
    },
    {
        "domain": "vercel.com",
        "name": "Vercel",
        "description": "Vercel MCP server for deployment and project management",
        "tools": [
            {"name": "list_deployments", "description": "List recent deployments on Vercel with status and URL", "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "limit": {"type": "integer"}}}},
            {"name": "create_deployment", "description": "Trigger a new deployment on Vercel from a Git branch", "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "ref": {"type": "string"}}, "required": ["project_id"]}},
            {"name": "get_deployment_logs", "description": "Retrieve build and runtime logs for a Vercel deployment", "input_schema": {"type": "object", "properties": {"deployment_id": {"type": "string"}}, "required": ["deployment_id"]}},
            {"name": "set_env_variable", "description": "Set or update an environment variable for a Vercel project", "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"}, "target": {"type": "array"}}, "required": ["project_id", "key", "value"]}},
        ],
    },
]


async def seed():
    """Seed the database with curated MCP tool data."""
    async with async_session() as db:
        total_tools = 0

        for server in SEED_SERVERS:
            # Create or get provider
            stmt = select(Provider).where(Provider.domain == server["domain"])
            provider = (await db.execute(stmt)).scalar_one_or_none()

            if provider is None:
                provider = Provider(
                    domain=server["domain"],
                    name=server["name"],
                    description=server["description"],
                    homepage_url=f"https://{server['domain']}",
                )
                db.add(provider)
                await db.flush()
                print(f"  Created provider: {server['name']}")

            # Prepare tool texts for batch embedding
            texts = [
                build_tool_text(t["name"], t["description"], server["domain"])
                for t in server["tools"]
            ]

            print(f"  Embedding {len(texts)} tools for {server['name']}...")
            embeddings = await embed_texts(texts)

            for tool_data, embedding in zip(server["tools"], embeddings):
                # Check if tool already exists
                stmt = select(Tool).where(
                    Tool.provider_id == provider.id,
                    Tool.name == tool_data["name"],
                    Tool.protocol == "mcp",
                )
                existing = (await db.execute(stmt)).scalar_one_or_none()

                if existing is None:
                    tool = Tool(
                        provider_id=provider.id,
                        name=tool_data["name"],
                        description=tool_data["description"],
                        protocol="mcp",
                        input_schema=tool_data.get("input_schema"),
                        endpoint=f"https://{server['domain']}/.well-known/mcp/server.json",
                        embedding=embedding,
                    )
                    db.add(tool)
                    total_tools += 1

            await db.flush()

        await db.commit()
        print(f"\nDone! Seeded {total_tools} tools from {len(SEED_SERVERS)} providers.")


if __name__ == "__main__":
    asyncio.run(seed())
