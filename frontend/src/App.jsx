import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const healthUrl = useMemo(() => {
    return `${API_BASE_URL.replace(/\/$/, "")}/health`;
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function fetchHealth() {
      try {
        const response = await fetch(healthUrl);

        if (!response.ok) {
          throw new Error(`Health check failed with ${response.status}`);
        }

        const payload = await response.json();

        if (isMounted) {
          setHealth(payload);
          setError("");
        }
      } catch (caughtError) {
        if (isMounted) {
          setHealth(null);
          setError(
            caughtError instanceof Error
              ? caughtError.message
              : "Unable to reach the backend.",
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchHealth();

    return () => {
      isMounted = false;
    };
  }, [healthUrl]);

  const isConnected = health?.status === "ok";

  return (
    <main className="page-shell">
      <section className="status-panel" aria-labelledby="app-title">
        <p className="eyebrow">Phase 0 deploy check</p>
        <h1 id="app-title">TTB Label Verification</h1>
        <div
          className={isConnected ? "status-pill connected" : "status-pill pending"}
          aria-live="polite"
        >
          {isLoading && "Checking backend"}
          {!isLoading && isConnected && "Backend connected"}
          {!isLoading && !isConnected && "Backend unavailable"}
        </div>
        <pre className="health-output">
          {health ? JSON.stringify(health, null, 2) : error || "Waiting for response..."}
        </pre>
      </section>
    </main>
  );
}

