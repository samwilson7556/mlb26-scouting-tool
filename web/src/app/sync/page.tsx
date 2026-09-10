"use client";

import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { syncAll, syncHistory, syncLogs } from "@/lib/api";

export default function SyncPage() {
  const [loading, setLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runSync(type: "history" | "logs" | "all") {
    setLoading(type);
    setMessage(null);
    setError(null);

    try {
      const result =
        type === "history"
          ? await syncHistory()
          : type === "logs"
          ? await syncLogs()
          : await syncAll();

      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(null);
    }
  }

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Sync</h1>
        <p className="mt-2 text-slate-400">
          Pull game history and game logs from MLB The Show 26.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="card">
          <h2 className="text-xl font-bold">Sync History</h2>
          <p className="mt-2 text-sm text-slate-400">
            Fetch all game history pages and remove CPU games.
          </p>
          <button
            className="button mt-6"
            disabled={loading !== null}
            onClick={() => runSync("history")}
          >
            {loading === "history" ? "Running..." : "Sync History"}
          </button>
        </div>

        <div className="card">
          <h2 className="text-xl font-bold">Sync Logs</h2>
          <p className="mt-2 text-sm text-slate-400">
            Fetch individual game logs for stored human-only games.
          </p>
          <button
            className="button mt-6"
            disabled={loading !== null}
            onClick={() => runSync("logs")}
          >
            {loading === "logs" ? "Running..." : "Sync Logs"}
          </button>
        </div>

        <div className="card">
          <h2 className="text-xl font-bold">Sync All</h2>
          <p className="mt-2 text-sm text-slate-400">
            Run history sync followed by game-log sync.
          </p>
          <button
            className="button mt-6"
            disabled={loading !== null}
            onClick={() => runSync("all")}
          >
            {loading === "all" ? "Running..." : "Sync All"}
          </button>
        </div>
      </div>

      {message && <div className="card mt-6 text-green-400">{message}</div>}
      {error && <div className="card mt-6 text-red-400">{error}</div>}
    </AppShell>
  );
}