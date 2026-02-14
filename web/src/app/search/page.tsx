"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useState, useEffect, Suspense } from "react";
import { discover, type ToolResult } from "@/lib/api";
import { ToolCard } from "@/components/tool-card";

function SearchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<ToolResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialQuery) {
      doSearch(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  async function doSearch(q: string) {
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await discover(q);
      setResults(data.results);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to connect to API"
      );
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`, {
        scroll: false,
      });
      doSearch(query.trim());
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <form onSubmit={handleSubmit}>
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe what your agent needs..."
            className="w-full rounded-2xl border border-border bg-card px-6 py-4 pr-24 text-lg shadow-sm outline-none placeholder:text-muted/60 focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
            autoFocus
          />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-white hover:bg-accent-dark transition-colors disabled:opacity-50"
          >
            {loading ? "..." : "Search"}
          </button>
        </div>
      </form>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}. Make sure the API server is running at{" "}
          <code className="font-mono">localhost:8000</code>.
        </div>
      )}

      {searched && !loading && !error && (
        <div className="mt-6">
          <p className="text-sm text-muted">
            {results.length} tool{results.length !== 1 ? "s" : ""} found
          </p>
          <div className="mt-4 space-y-3">
            {results.map((tool) => (
              <ToolCard key={tool.id} tool={tool} showScore />
            ))}
          </div>
          {results.length === 0 && (
            <p className="mt-10 text-center text-muted">
              No tools found. Try a different query or make sure the index has
              been crawled.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchContent />
    </Suspense>
  );
}
