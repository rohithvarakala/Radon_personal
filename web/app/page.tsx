"use client";

import { useEffect, useState } from "react";

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
          // If API is up, check broker
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

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-section)",
        padding: "var(--space-section)",
      }}
    >
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

      <div
        className="panel"
        style={{
          maxWidth: 600,
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
            flexDirection: "column",
            gap: "var(--space-base)",
            fontSize: "13px",
          }}
        >
          <StatusRow label="Next.js" port="3000" status="active" />
          <StatusRow label="FastAPI" port="8321" status={apiStatus} />
          <StatusRow label="Alpaca" port="paper" status={brokerStatus} />
        </div>
      </div>

      <div
        className="panel"
        style={{
          maxWidth: 600,
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
          Quick Start
        </h2>
        <div
          className="mono"
          style={{
            fontSize: "13px",
            color: "var(--text-secondary)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-micro)",
          }}
        >
          <code>1. Create .env files with API keys</code>
          <code>2. bash start.sh</code>
        </div>
      </div>
    </main>
  );
}

function StatusRow({
  label,
  port,
  status,
}: {
  label: string;
  port: string;
  status: "active" | "pending" | "disconnected";
}) {
  const colors = {
    active: "var(--signal-core)",
    pending: "var(--warn)",
    disconnected: "var(--fault)",
  };

  return (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      <span>
        {label}{" "}
        <span style={{ color: "var(--text-muted)" }}>:{port}</span>
      </span>
      <span style={{ color: colors[status] }}>{status}</span>
    </div>
  );
}
