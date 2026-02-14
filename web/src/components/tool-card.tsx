import Link from "next/link";
import type { ToolResult } from "@/lib/api";

const protocolColors: Record<string, string> = {
  mcp: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  webmcp:
    "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  a2a: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  openapi:
    "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
};

export function ToolCard({
  tool,
  showScore = false,
}: {
  tool: ToolResult;
  showScore?: boolean;
}) {
  return (
    <Link
      href={`/tools/${tool.id}`}
      className="block rounded-xl border border-border bg-card p-5 hover:bg-card-hover hover:border-accent/40 transition-all"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold truncate">{tool.name}</h3>
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                protocolColors[tool.protocol] || "bg-gray-100 text-gray-600"
              }`}
            >
              {tool.protocol.toUpperCase()}
            </span>
          </div>
          <p className="mt-0.5 text-sm text-muted truncate">
            {tool.provider_name || tool.provider_domain}
          </p>
        </div>
        {showScore && (
          <span className="shrink-0 rounded-lg bg-accent/10 px-2.5 py-1 text-sm font-mono font-medium text-accent">
            {(tool.relevance_score * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <p className="mt-3 text-sm text-muted line-clamp-2">
        {tool.description}
      </p>
    </Link>
  );
}
