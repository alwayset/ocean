"use client";

import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
import Link from "next/link";
import { getToolDetail, type ToolDetail } from "@/lib/api";

export default function ToolDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [tool, setTool] = useState<ToolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getToolDetail(id);
        setTool(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load tool"
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10 text-center text-muted">
        Loading...
      </div>
    );
  }

  if (error || !tool) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error || "Tool not found"}
        </div>
        <Link href="/tools" className="mt-4 inline-block text-sm text-accent">
          Back to tools
        </Link>
      </div>
    );
  }

  const protocolColors: Record<string, string> = {
    mcp: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    webmcp: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    a2a: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    openapi: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <Link
        href="/tools"
        className="text-sm text-muted hover:text-foreground transition-colors"
      >
        &larr; Back to tools
      </Link>

      <div className="mt-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{tool.name}</h1>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
              protocolColors[tool.protocol] || "bg-gray-100 text-gray-600"
            }`}
          >
            {tool.protocol.toUpperCase()}
          </span>
        </div>
        <p className="mt-1 text-muted">
          {tool.provider_name || tool.provider_domain}
        </p>
      </div>

      <p className="mt-6 leading-relaxed">{tool.description}</p>

      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs uppercase tracking-wider text-muted">
            Provider
          </p>
          <p className="mt-1 font-medium truncate">{tool.provider_domain}</p>
        </div>
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs uppercase tracking-wider text-muted">
            Endpoint
          </p>
          <p className="mt-1 font-mono text-sm truncate">
            {tool.endpoint || "N/A"}
          </p>
        </div>
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs uppercase tracking-wider text-muted">
            Calls
          </p>
          <p className="mt-1 font-medium">{tool.call_count}</p>
        </div>
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs uppercase tracking-wider text-muted">
            Last Seen
          </p>
          <p className="mt-1 text-sm">
            {new Date(tool.last_seen).toLocaleDateString()}
          </p>
        </div>
      </div>

      {tool.input_schema && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold">Input Schema</h2>
          <pre className="mt-3 overflow-x-auto rounded-xl border border-border bg-card p-5 font-mono text-sm leading-relaxed">
            {JSON.stringify(tool.input_schema, null, 2)}
          </pre>
        </div>
      )}

      {tool.output_schema && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold">Output Schema</h2>
          <pre className="mt-3 overflow-x-auto rounded-xl border border-border bg-card p-5 font-mono text-sm leading-relaxed">
            {JSON.stringify(tool.output_schema, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
