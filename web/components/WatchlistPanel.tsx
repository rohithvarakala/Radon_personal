"use client";

import { useEffect, useState, FormEvent } from "react";
import { fetchApi, WatchlistItem, WatchlistMutationResponse } from "@/lib/api";

interface WatchlistPanelProps {
  onTickerSelect?: (ticker: string) => void;
  activeTicker?: string | null;
}

export default function WatchlistPanel({
  onTickerSelect,
  activeTicker,
}: WatchlistPanelProps) {
  const [tickers, setTickers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [mutating, setMutating] = useState(false);

  async function loadWatchlist() {
    try {
      const data = await fetchApi<WatchlistItem[]>("/watchlist");
      setTickers(data.map((item) => item.ticker));
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load watchlist"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadWatchlist();
  }, []);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const symbol = input.trim().toUpperCase();
    if (!symbol || mutating) return;

    setMutating(true);
    try {
      await fetchApi<WatchlistMutationResponse>(`/watchlist/${symbol}`, {
        method: "POST",
      });
      setInput("");
      await loadWatchlist();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to add ticker"
      );
    } finally {
      setMutating(false);
    }
  }

  async function handleRemove(symbol: string) {
    if (mutating) return;
    setMutating(true);
    try {
      await fetchApi<WatchlistMutationResponse>(`/watchlist/${symbol}`, {
        method: "DELETE",
      });
      await loadWatchlist();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to remove ticker"
      );
    } finally {
      setMutating(false);
    }
  }

  return (
    <div className="panel" style={{ width: "100%" }}>
      <h2
        style={{
          fontSize: "14px",
          color: "var(--text-muted)",
          marginBottom: "var(--space-gutter)",
          fontWeight: 500,
        }}
      >
        Watchlist
      </h2>

      {/* Add ticker form */}
      <form
        onSubmit={handleAdd}
        style={{
          display: "flex",
          gap: "var(--space-base)",
          marginBottom: "var(--space-gutter)",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Add ticker"
          className="mono"
          style={{
            flex: 1,
            background: "var(--bg-panel-raised)",
            border: "1px solid var(--border-dim)",
            borderRadius: "var(--radius-panel)",
            padding: "var(--space-base) var(--space-gutter)",
            color: "var(--text-primary)",
            fontSize: "13px",
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={mutating}
          style={{
            background: "var(--signal-deep)",
            color: "var(--text-primary)",
            border: "none",
            borderRadius: "var(--radius-panel)",
            padding: "var(--space-base) var(--space-gutter)",
            fontFamily: "var(--font-mono)",
            fontSize: "13px",
            cursor: mutating ? "wait" : "pointer",
            opacity: mutating ? 0.6 : 1,
            whiteSpace: "nowrap",
          }}
        >
          + Add
        </button>
      </form>

      {error && (
        <div
          className="mono"
          style={{
            color: "var(--fault)",
            fontSize: "12px",
            marginBottom: "var(--space-base)",
          }}
        >
          {error}
        </div>
      )}

      {/* Ticker list */}
      {loading ? (
        <div
          className="mono"
          style={{ color: "var(--text-muted)", fontSize: "13px" }}
        >
          Loading watchlist...
        </div>
      ) : tickers.length === 0 ? (
        <div
          className="mono"
          style={{ color: "var(--text-muted)", fontSize: "13px" }}
        >
          No tickers in watchlist
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "2px",
          }}
        >
          {tickers.map((ticker) => (
            <div
              key={ticker}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "var(--space-base) var(--space-base)",
                borderRadius: "var(--radius-panel)",
                background:
                  activeTicker === ticker
                    ? "rgba(5, 173, 152, 0.1)"
                    : "transparent",
                border:
                  activeTicker === ticker
                    ? "1px solid rgba(5, 173, 152, 0.25)"
                    : "1px solid transparent",
                cursor: "pointer",
                transition: "background 0.15s ease",
              }}
              onClick={() => onTickerSelect?.(ticker)}
              onMouseEnter={(e) => {
                if (activeTicker !== ticker) {
                  e.currentTarget.style.background = "var(--bg-hover)";
                }
              }}
              onMouseLeave={(e) => {
                if (activeTicker !== ticker) {
                  e.currentTarget.style.background = "transparent";
                }
              }}
            >
              <span
                className="mono"
                style={{
                  fontSize: "13px",
                  fontWeight: 500,
                  color:
                    activeTicker === ticker
                      ? "var(--signal-core)"
                      : "var(--text-primary)",
                }}
              >
                {ticker}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemove(ticker);
                }}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  fontFamily: "var(--font-mono)",
                  fontSize: "14px",
                  padding: "0 4px",
                  lineHeight: 1,
                  opacity: 0.6,
                  transition: "opacity 0.15s ease, color 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.opacity = "1";
                  e.currentTarget.style.color = "var(--fault)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.opacity = "0.6";
                  e.currentTarget.style.color = "var(--text-muted)";
                }}
                title={`Remove ${ticker}`}
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
