"use client";

import { useEffect, useState } from "react";
import TickerLookup from "@/components/TickerLookup";
import FlowPanel from "@/components/FlowPanel";
import WatchlistPanel from "@/components/WatchlistPanel";

type ServiceStatus = "active" | "pending" | "disconnected";

function useServiceHealth() {
  const [apiStatus, setApiStatus] = useState<ServiceStatus>("pending");
  const [brokerStatus, setBrokerStatus] = useState<ServiceStatus>("pending");

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch("http://localhost:8321/health", {
          signal: AbortSignal.timeout(3000),
        });
        if (res.ok) {
          setApiStatus("active");
          try {
            const brokerRes = await fetch(
              "http://localhost:8321/broker/status",
              { signal: AbortSignal.timeout(3000) }
            );
            if (brokerRes.ok) {
              const data = await brokerRes.json();
              setBrokerStatus(data.connected ? "active" : "disconnected");
            } else {
              setBrokerStatus("disconnected");
            }
          } catch {
            setBrokerStatus("disconnected");
          }
        } else {
          setApiStatus("disconnected");
          setBrokerStatus("disconnected");
        }
      } catch {
        setApiStatus("disconnected");
        setBrokerStatus("disconnected");
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return { apiStatus, brokerStatus };
}

export default function Home() {
  const { apiStatus, brokerStatus } = useServiceHealth();
  const [activeTicker, setActiveTicker] = useState<string | null>(null);

  function handleTickerSelect(ticker: string) {
    setActiveTicker(ticker);
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "var(--space-section)",
        gap: "var(--space-section)",
      }}
    >
      {/* Header */}
      <div style={{ textAlign: "center" }}>
        <h1
          style={{
            fontSize: "2rem",
            fontWeight: 600,
            color: "var(--signal-core)",
            marginBottom: "var(--space-base)",
          }}
        >
          Radon Terminal
        </h1>
        <p
          className="mono"
          style={{
            color: "var(--text-secondary)",
            fontSize: "14px",
          }}
        >
          Market structure reconstruction system
        </p>
      </div>

      {/* System Status */}
      <div
        className="panel"
        style={{
          maxWidth: 960,
          width: "100%",
        }}
      >
        <h2
          style={{
            fontSize: "14px",
            color: "var(--text-muted)",
            marginBottom: "var(--space-gutter)",
            fontWeight: 500,
          }}
        >
          System Status
        </h2>
        <div
          className="mono"
          style={{
            display: "flex",
            gap: "var(--space-section)",
            fontSize: "13px",
            flexWrap: "wrap",
          }}
        >
          <StatusIndicator label="Next.js" port="3000" status="active" />
          <StatusIndicator label="FastAPI" port="8321" status={apiStatus} />
          <StatusIndicator label="Alpaca" port="paper" status={brokerStatus} />
        </div>
      </div>

      {/* Dashboard Grid */}
      <div
        style={{
          maxWidth: 960,
          width: "100%",
          display: "grid",
          gridTemplateColumns: "1fr 260px",
          gap: "var(--space-gutter)",
          alignItems: "start",
        }}
      >
        {/* Main Column */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-gutter)",
            minWidth: 0,
          }}
        >
          <TickerLookup onTickerSelect={handleTickerSelect} />

          {activeTicker && <FlowPanel symbol={activeTicker} />}
        </div>

        {/* Sidebar */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-gutter)",
          }}
        >
          <WatchlistPanel
            onTickerSelect={handleTickerSelect}
            activeTicker={activeTicker}
          />
        </div>
      </div>

      {/* Responsive: stack columns on narrow viewports */}
      <style>{`
        @media (max-width: 720px) {
          main > div:last-of-type {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </main>
  );
}

function StatusIndicator({
  label,
  port,
  status,
}: {
  label: string;
  port: string;
  status: ServiceStatus;
}) {
  const colors = {
    active: "var(--signal-core)",
    pending: "var(--warn)",
    disconnected: "var(--fault)",
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-base)" }}>
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: colors[status],
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span>
        {label}{" "}
        <span style={{ color: "var(--text-muted)" }}>:{port}</span>
      </span>
      <span style={{ color: colors[status], fontSize: "12px" }}>{status}</span>
    </div>
  );
}
