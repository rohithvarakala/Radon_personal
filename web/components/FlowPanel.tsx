"use client";

import { useEffect, useState } from "react";
import { fetchApi, FlowResponse } from "@/lib/api";

function formatPercent(n: number | null | undefined): string {
  if (n == null) return "--";
  return (n * 100).toFixed(2) + "%";
}

function formatNumber(n: number | null | undefined): string {
  if (n == null) return "--";
  return n.toLocaleString("en-US");
}

function getSignalColor(signal: string): string {
  switch (signal) {
    case "BULLISH":
    case "LEAN_BULLISH":
      return "var(--signal-core)";
    case "BEARISH":
    case "LEAN_BEARISH":
      return "var(--fault)";
    case "NEUTRAL":
      return "var(--neutral)";
    default:
      return "var(--text-muted)";
  }
}

function getSignalBg(signal: string): string {
  switch (signal) {
    case "BULLISH":
    case "LEAN_BULLISH":
      return "rgba(5, 173, 152, 0.12)";
    case "BEARISH":
    case "LEAN_BEARISH":
      return "rgba(232, 93, 108, 0.12)";
    case "NEUTRAL":
      return "rgba(148, 163, 184, 0.12)";
    default:
      return "var(--bg-panel-raised)";
  }
}

interface FlowPanelProps {
  symbol: string;
}

export default function FlowPanel({ symbol }: FlowPanelProps) {
  const [data, setData] = useState<FlowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadFlow() {
      setLoading(true);
      setError(null);
      setData(null);

      try {
        const result = await fetchApi<FlowResponse>(`/flow/${symbol}`);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to fetch flow data"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadFlow();
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  if (loading) {
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
          Options Flow
        </h2>
        <div
          className="mono"
          style={{ color: "var(--text-muted)", fontSize: "13px" }}
        >
          Loading flow data for {symbol}...
        </div>
      </div>
    );
  }

  if (error) {
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
          Options Flow
        </h2>
        <div
          className="mono"
          style={{ color: "var(--fault)", fontSize: "13px" }}
        >
          {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const pcr = data.options_flow.put_call_ratio;
  const iv = data.options_flow.iv_data;
  const si = data.institutional_signals.short_interest;
  const holders = data.institutional_signals.institutional_holders;

  return (
    <div className="panel" style={{ width: "100%" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "var(--space-gutter)",
        }}
      >
        <h2
          style={{
            fontSize: "14px",
            color: "var(--text-muted)",
            fontWeight: 500,
          }}
        >
          Options Flow{" "}
          <span
            className="mono"
            style={{ color: "var(--signal-core)", fontWeight: 600 }}
          >
            {symbol}
          </span>
        </h2>
        {data.options_flow.nearest_expiry && (
          <span
            className="mono"
            style={{ fontSize: "11px", color: "var(--text-muted)" }}
          >
            Nearest expiry: {data.options_flow.nearest_expiry}
          </span>
        )}
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-gutter)",
        }}
      >
        {/* Put/Call Ratio */}
        {pcr && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-base)",
            }}
          >
            <SectionLabel>Put / Call Ratio</SectionLabel>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-gutter)",
              }}
            >
              <span
                className="mono"
                style={{
                  fontSize: "24px",
                  fontWeight: 600,
                  color: getSignalColor(pcr.signal),
                }}
              >
                {pcr.ratio != null ? pcr.ratio.toFixed(3) : "--"}
              </span>
              <span
                className="badge"
                style={{
                  background: getSignalBg(pcr.signal),
                  color: getSignalColor(pcr.signal),
                  border: `1px solid ${getSignalColor(pcr.signal)}`,
                }}
              >
                {pcr.signal}
              </span>
            </div>
            <div
              className="mono"
              style={{
                display: "flex",
                gap: "var(--space-gutter)",
                fontSize: "12px",
                color: "var(--text-secondary)",
              }}
            >
              <span>
                Call Vol:{" "}
                <span style={{ color: "var(--signal-core)" }}>
                  {formatNumber(pcr.total_call_volume)}
                </span>
              </span>
              <span>
                Put Vol:{" "}
                <span style={{ color: "var(--fault)" }}>
                  {formatNumber(pcr.total_put_volume)}
                </span>
              </span>
            </div>

            {/* Volume bar visualization */}
            {pcr.total_call_volume + pcr.total_put_volume > 0 && (
              <div
                style={{
                  display: "flex",
                  height: "6px",
                  borderRadius: "3px",
                  overflow: "hidden",
                  background: "var(--bg-panel-raised)",
                }}
              >
                <div
                  style={{
                    width: `${(pcr.total_call_volume / (pcr.total_call_volume + pcr.total_put_volume)) * 100}%`,
                    background: "var(--signal-core)",
                    transition: "width 0.3s ease",
                  }}
                />
                <div
                  style={{
                    flex: 1,
                    background: "var(--fault)",
                  }}
                />
              </div>
            )}
          </div>
        )}
        {data.options_flow.put_call_ratio_error && (
          <div
            className="mono"
            style={{ fontSize: "12px", color: "var(--text-muted)" }}
          >
            PCR: {data.options_flow.put_call_ratio_error}
          </div>
        )}

        {/* IV Data */}
        {iv && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-base)",
            }}
          >
            <SectionLabel>Implied Volatility</SectionLabel>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "var(--space-base)",
              }}
            >
              <IVCell label="ATM Call IV" value={formatPercent(iv.atm_call_iv)} />
              <IVCell label="ATM Put IV" value={formatPercent(iv.atm_put_iv)} />
              <IVCell
                label="Avg ATM IV"
                value={formatPercent(iv.avg_atm_iv)}
                highlight
              />
            </div>
          </div>
        )}
        {data.options_flow.iv_error && (
          <div
            className="mono"
            style={{ fontSize: "12px", color: "var(--text-muted)" }}
          >
            IV: {data.options_flow.iv_error}
          </div>
        )}

        {/* Chain summary */}
        {data.options_flow.num_expirations != null && (
          <div
            className="mono"
            style={{
              display: "flex",
              gap: "var(--space-gutter)",
              fontSize: "11px",
              color: "var(--text-muted)",
            }}
          >
            <span>{data.options_flow.num_expirations} expirations</span>
            <span>{formatNumber(data.options_flow.num_calls)} calls</span>
            <span>{formatNumber(data.options_flow.num_puts)} puts</span>
          </div>
        )}

        {/* Short Interest */}
        {si && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-base)",
            }}
          >
            <SectionLabel>Short Interest</SectionLabel>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                gap: "var(--space-base)",
              }}
            >
              <IVCell
                label="Short Ratio"
                value={si.short_ratio != null ? si.short_ratio.toFixed(2) : "--"}
              />
              <IVCell
                label="Short % Float"
                value={formatPercent(si.short_percent_of_float)}
              />
              <IVCell
                label="Shares Short"
                value={formatNumber(si.shares_short)}
              />
              <IVCell
                label="Prior Month"
                value={formatNumber(si.shares_short_prior_month)}
              />
            </div>
          </div>
        )}
        {data.institutional_signals.short_interest_error && (
          <div
            className="mono"
            style={{ fontSize: "12px", color: "var(--text-muted)" }}
          >
            Short Interest: {data.institutional_signals.short_interest_error}
          </div>
        )}

        {/* Institutional Holders */}
        {holders && holders.length > 0 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-base)",
            }}
          >
            <SectionLabel>
              Top Institutional Holders
              {data.institutional_signals.num_institutional_holders != null && (
                <span
                  style={{
                    color: "var(--text-muted)",
                    fontWeight: 400,
                    marginLeft: "var(--space-base)",
                  }}
                >
                  ({data.institutional_signals.num_institutional_holders} total)
                </span>
              )}
            </SectionLabel>
            <table>
              <thead>
                <tr>
                  <th>Holder</th>
                  <th style={{ textAlign: "right" }}>Shares</th>
                  <th style={{ textAlign: "right" }}>% Out</th>
                </tr>
              </thead>
              <tbody>
                {holders.slice(0, 5).map((h, i) => {
                  const name =
                    (h["Holder"] as string) ||
                    (h["holder"] as string) ||
                    `Holder ${i + 1}`;
                  const shares =
                    (h["Shares"] as number) || (h["shares"] as number) || null;
                  const pctOut =
                    (h["pctHeld"] as number) ||
                    (h["% Out"] as number) ||
                    (h["pct_out"] as number) ||
                    null;

                  return (
                    <tr key={i}>
                      <td
                        style={{
                          color: "var(--text-secondary)",
                          fontSize: "12px",
                          fontFamily: "var(--font-sans)",
                          maxWidth: "200px",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {name}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {formatNumber(shares)}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {pctOut != null ? formatPercent(pctOut) : "--"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {data.institutional_signals.holders_error && (
          <div
            className="mono"
            style={{ fontSize: "12px", color: "var(--text-muted)" }}
          >
            Holders: {data.institutional_signals.holders_error}
          </div>
        )}
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3
      style={{
        fontSize: "12px",
        color: "var(--text-muted)",
        fontWeight: 500,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}
    >
      {children}
    </h3>
  );
}

function IVCell({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "2px",
        padding: "var(--space-base)",
        background: highlight
          ? "rgba(5, 173, 152, 0.06)"
          : "var(--bg-panel-raised)",
        borderRadius: "var(--radius-panel)",
        border: highlight
          ? "1px solid rgba(5, 173, 152, 0.2)"
          : "1px solid var(--border-dim)",
      }}
    >
      <span
        style={{
          fontSize: "10px",
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
          fontSize: "14px",
          fontWeight: 500,
          color: highlight ? "var(--signal-core)" : "var(--text-primary)",
        }}
      >
        {value}
      </span>
    </div>
  );
}
