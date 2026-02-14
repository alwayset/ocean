"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-6">
      <div className="w-full max-w-2xl text-center">
        <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
          Ocean
        </h1>
        <p className="mt-4 text-lg text-muted">
          Discover the right tool for your AI agent. Search across MCP, WebMCP,
          A2A, and OpenAPI — instantly.
        </p>

        <form onSubmit={handleSearch} className="mt-10">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='Try "send email", "search flights", "read database"...'
              className="w-full rounded-2xl border border-border bg-card px-6 py-4 pr-24 text-lg shadow-sm outline-none placeholder:text-muted/60 focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-white hover:bg-accent-dark transition-colors"
            >
              Search
            </button>
          </div>
        </form>

        <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-3">
          <div className="rounded-xl border border-border p-6 text-left">
            <div className="text-2xl">&#x1F50D;</div>
            <h3 className="mt-3 font-semibold">Semantic Discovery</h3>
            <p className="mt-1 text-sm text-muted">
              Describe what you need in natural language. Ocean finds the right
              tools using vector similarity search.
            </p>
          </div>
          <div className="rounded-xl border border-border p-6 text-left">
            <div className="text-2xl">&#x1F310;</div>
            <h3 className="mt-3 font-semibold">Multi-Protocol</h3>
            <p className="mt-1 text-sm text-muted">
              One index across MCP servers, WebMCP pages, A2A agents, and
              OpenAPI specs. Unified search.
            </p>
          </div>
          <div className="rounded-xl border border-border p-6 text-left">
            <div className="text-2xl">&#x26A1;</div>
            <h3 className="mt-3 font-semibold">Agent-Native API</h3>
            <p className="mt-1 text-sm text-muted">
              Built for agents, not just humans. POST an intent, get ranked
              tools with schemas ready to invoke.
            </p>
          </div>
        </div>

        <div className="mt-16 rounded-xl border border-border bg-card p-6 text-left">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">
            Quick Start
          </p>
          <pre className="mt-3 overflow-x-auto font-mono text-sm leading-relaxed">
            <code>{`curl -X POST https://ocean-api-production.up.railway.app/v1/discover \\
  -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \\
  -d '{"intent": "send an email with attachments"}'`}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
