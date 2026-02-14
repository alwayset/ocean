"use client";

import { useState, useEffect } from "react";
import { getStats, type StatsResponse } from "@/lib/api";

export default function StatsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getStats();
        setStats(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to connect to API"
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10 text-center text-muted">
        Loading...
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error || "Failed to load stats"}. Make sure the API server is
          running.
        </div>
      </div>
    );
  }

  const protocolColors: Record<string, string> = {
    mcp: "text-blue-600 dark:text-blue-400",
    webmcp: "text-purple-600 dark:text-purple-400",
    a2a: "text-green-600 dark:text-green-400",
    openapi: "text-orange-600 dark:text-orange-400",
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-bold">Index Statistics</h1>
      <p className="mt-1 text-muted">
        Real-time overview of the Ocean tool index.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="rounded-xl border border-border p-8 text-center">
          <p className="text-4xl font-bold text-accent">
            {stats.total_tools.toLocaleString()}
          </p>
          <p className="mt-2 text-muted">Tools Indexed</p>
        </div>
        <div className="rounded-xl border border-border p-8 text-center">
          <p className="text-4xl font-bold text-accent">
            {stats.total_providers.toLocaleString()}
          </p>
          <p className="mt-2 text-muted">Providers</p>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold">By Protocol</h2>
        <div className="mt-4 space-y-3">
          {Object.entries(stats.protocols).length === 0 ? (
            <p className="text-muted">No tools indexed yet.</p>
          ) : (
            Object.entries(stats.protocols)
              .sort((a, b) => b[1] - a[1])
              .map(([protocol, count]) => (
                <div
                  key={protocol}
                  className="flex items-center justify-between rounded-xl border border-border p-4"
                >
                  <span
                    className={`font-medium ${protocolColors[protocol] || ""}`}
                  >
                    {protocol.toUpperCase()}
                  </span>
                  <span className="font-mono text-muted">
                    {count.toLocaleString()}
                  </span>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  );
}
