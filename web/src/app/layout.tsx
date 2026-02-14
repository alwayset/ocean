import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Ocean — Discover AI Agent Tools",
  description:
    "Semantic discovery engine for AI agent tools. Find the right MCP, WebMCP, A2A, and OpenAPI tools instantly.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <nav className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-sm">
          <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
            <Link href="/" className="text-xl font-bold tracking-tight">
              Ocean
            </Link>
            <div className="flex items-center gap-6 text-sm">
              <Link
                href="/search"
                className="text-muted hover:text-foreground transition-colors"
              >
                Search
              </Link>
              <Link
                href="/tools"
                className="text-muted hover:text-foreground transition-colors"
              >
                Browse
              </Link>
              <Link
                href="/stats"
                className="text-muted hover:text-foreground transition-colors"
              >
                Stats
              </Link>
              <a
                href="https://ocean-api-production.up.railway.app/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full border border-border px-4 py-1.5 text-sm text-muted hover:border-accent hover:text-accent transition-colors"
              >
                API Docs
              </a>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
