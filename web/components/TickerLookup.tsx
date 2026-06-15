"use client";

import { useState, FormEvent } from "react";
import {
  fetchApi,
  TickerResponse,
  AnalystResponse,
} from "@/lib/api";

function formatNumber(n: number | null | undefined): string {
  if (n == null) return "--";
  return n.toLocaleString("en-US");
}

function formatCurrency(n: number | null | undefined): string {
  if (n == null) return "--";
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatMarketCap(n: number | null | undefined): string {
  if (n == null) return "--";
  if (n >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
  if (n >= 1e9) return "$" + (n / 1e9).toFixed(2) + "B";
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(2) + "M";
  return "$" + formatNumber(n);
}

function formatPercent(n: number | null | undefined): string {
  if (n == null) return "--";
  return (n * 100).toFixed(2) + "%";
}

interface TickerLookupProps {
  onTickerSelect?: (ticker: string) => void;
}

export default function TickerLookup({ onTickerSelect }: TickerLookupProps) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tickerData, setTickerData] = useState<TickerResponse | null>(null);
  const [analystData, setAnalystData] = useState<AnalystResponse | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const symbol = input.trim().toUpperCase();
    if (!symbol) return;

    setLoading(true);
    setError(null);
    setTickerData(null);
    setAnalystData(null);

    try {
      const [ticker, analyst] = await Promise.all([
        fetchApi<TickerResponse>(`/ticker/${symbol}`),
        fetchApi<AnalystResponse>(`/analyst/${symbol}`).catch(() => null),
      ]);

      if (!ticker.valid) {
        setError(`Invalid ticker: ${symbol}`);
        return;
      }

      setTickerData(ticker);
      setAnalystData(analyst);
      onTickerSelect?.(symbol);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch ticker data");
    } finally {
      setLoading(false);
    }
  }

  const data = tickerData?.data;

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
        Ticker Lookup
      </h2>

      <form
        onSubmit={handleSubmit}
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
          placeholder="Enter ticker (e.g. AAPL)"
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
          disabled={loading}
          style={{
            background: "var(--signal-deep)",
            color: "var(--text-primary)",
            border: "none",
            borderRadius: "var(--radius-panel)",
            padding: "var(--space-base) var(--space-gutter)",
            fontFamily: "var(--font-mono)",
            fontSize: "13px",
            cursor: loading ? "wait" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "..." : "Lookup"}
        </button>
      </form>

      {error && (
        <div
          className="mono"
          style={{
            color: "var(--fault)",
            fontSize: "13px",
            padding: "var(--space-base)",
          }}
        >
          {error}
        </div>
      )}

      {data && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-gutter)",
          }}
        >
          {/* Header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
            }}
          >
            <div>
              <span
                className="mono"
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  color: "var(--signal-core)",
                }}
              >
                {data.ticker}
              </span>
              <span
                style={{
                  marginLeft: "var(--space-base)",
                  color: "var(--text-secondary)",
                  fontSize: "14px",
                }}
              >
                {data.name}
              </span>
            </div>
            <span
              className="mono"
              style={{
                fontSize: "18px",
                fontWeight: 600,
                color: "var(--text-primary)",
              }}
            >
              {formatCurrency(data.price)}
            </span>
          </div>

          {/* Sector badge */}
          {data.sector && (
            <div>
              <span
                className="badge"
                style={{
                  background: "var(--bg-panel-raised)",
                  color: "var(--text-secondary)",
                  border: "1px solid var(--border-dim)",
                }}
              >
                {data.sector}
              </span>
              {data.industry && (
                <span
                  className="badge"
                  style={{
                    background: "var(--bg-panel-raised)",
                    color: "var(--text-muted)",
                    border: "1px solid var(--border-dim)",
                    marginLeft: "var(--space-base)",
                  }}
                >
                  {data.industry}
                </span>
              )}
            </div>
          )}

          {/* Key metrics grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: "var(--space-base)",
            }}
          >
            <MetricCell label="Market Cap" value={formatMarketCap(data.market_cap)} />
            <MetricCell label="P/E Ratio" value={data.pe_ratio != null ? data.pe_ratio.toFixed(2) : "--"} />
            <MetricCell label="Fwd P/E" value={data.forward_pe != null ? data.forward_pe.toFixed(2) : "--"} />
            <MetricCell label="52W High" value={formatCurrency(data.fifty_two_week_high)} />
            <MetricCell label="52W Low" value={formatCurrency(data.fifty_two_week_low)} />
            <MetricCell label="Volume" value={formatNumber(data.volume)} />
            <MetricCell label="Avg Volume" value={formatNumber(data.avg_volume)} />
            <MetricCell label="Beta" value={data.beta != null ? data.beta.toFixed(2) : "--"} />
            <MetricCell label="Div Yield" value={formatPercent(data.dividend_yield)} />
          </div>

          {/* Analyst ratings */}
          {analystData && (
            <div
              className="panel-raised"
              style={{
                borderRadius: "var(--radius-panel)",
                padding: "var(--space-gutter)",
                border: "1px solid var(--border-dim)",
              }}
            >
              <h3
                style={{
                  fontSize: "12px",
                  color: "var(--text-muted)",
                  marginBottom: "var(--space-base)",
                  fontWeight: 500,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Analyst Consensus
              </h3>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                  gap: "var(--space-base)",
                }}
              >
                <MetricCell
                  label="Rating"
                  value={analystData.recommendation_key?.toUpperCase() || "--"}
                  color={getRecommendationColor(analystData.recommendation_key)}
                />
                <MetricCell
                  label="Target Mean"
                  value={formatCurrency(analystData.target_mean_price)}
                />
                <MetricCell
                  label="Target High"
                  value={formatCurrency(analystData.target_high_price)}
                />
                <MetricCell
                  label="Target Low"
                  value={formatCurrency(analystData.target_low_price)}
                />
                <MetricCell
                  label="# Analysts"
                  value={analystData.number_of_analyst_opinions != null
                    ? String(analystData.number_of_analyst_opinions)
                    : "--"
                  }
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCell({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "2px",
      }}
    >
      <span
        style={{
          fontSize: "11px",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {label}
      </span>
      <span
        className="mono"
        style={{
          fontSize: "13px",
          color: color || "var(--text-primary)",
          fontWeight: 500,
        }}
      >
        {value}
      </span>
    </div>
  );
}

function getRecommendationColor(key: string | null | undefined): string {
  if (!key) return "var(--text-muted)";
  const lower = key.toLowerCase();
  if (lower === "buy" || lower === "strong_buy" || lower === "strong buy")
    return "var(--signal-core)";
  if (lower === "overweight" || lower === "outperform")
    return "var(--signal-strong)";
  if (lower === "hold" || lower === "neutral" || lower === "equal-weight")
    return "var(--warn)";
  if (lower === "underweight" || lower === "underperform")
    return "var(--fault)";
  if (lower === "sell" || lower === "strong_sell" || lower === "strong sell")
    return "var(--fault)";
  return "var(--text-secondary)";
}
