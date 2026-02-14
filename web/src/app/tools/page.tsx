"use client";

import { useState, useEffect } from "react";
import { listTools, type ToolResult } from "@/lib/api";
import { ToolCard } from "@/components/tool-card";

const PROTOCOLS = ["all", "mcp", "webmcp", "a2a", "openapi"] as const;

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [protocol, setProtocol] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pageSize = 20;

  useEffect(() => {
    fetchTools();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, protocol]);

  async function fetchTools() {
    setLoading(true);
    setError(null);
    try {
      const data = await listTools(
        page,
        pageSize,
        protocol === "all" ? undefined : protocol
      );
      setTools(data.tools);
      setTotal(data.total);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to connect to API"
      );
    } finally {
      setLoading(false);
    }
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-bold">Browse Tools</h1>
      <p className="mt-1 text-muted">
        {total} tool{total !== 1 ? "s" : ""} indexed
      </p>

      <div className="mt-6 flex gap-2">
        {PROTOCOLS.map((p) => (
          <button
            key={p}
            onClick={() => {
              setProtocol(p);
              setPage(1);
            }}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              protocol === p
                ? "bg-accent text-white"
                : "border border-border text-muted hover:text-foreground"
            }`}
          >
            {p === "all" ? "All" : p.toUpperCase()}
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}. Make sure the API server is running.
        </div>
      )}

      {loading ? (
        <div className="mt-10 text-center text-muted">Loading...</div>
      ) : (
        <>
          <div className="mt-6 space-y-3">
            {tools.map((tool) => (
              <ToolCard key={tool.id} tool={tool} />
            ))}
          </div>

          {tools.length === 0 && !error && (
            <p className="mt-10 text-center text-muted">
              No tools indexed yet. Run the crawler first.
            </p>
          )}

          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-3">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-lg border border-border px-4 py-2 text-sm disabled:opacity-30"
              >
                Previous
              </button>
              <span className="text-sm text-muted">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded-lg border border-border px-4 py-2 text-sm disabled:opacity-30"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
