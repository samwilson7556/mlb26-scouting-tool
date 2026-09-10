"use client";

import { useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  GameLogSyncSummary,
  syncAll,
  syncHistory,
  syncLogs,
} from "@/lib/api";


type SyncType =
  | "history"
  | "logs"
  | "all";


type SyncResult = {
  type: SyncType;
  message: string;
  humanGames?: number;
  logSummary?: GameLogSyncSummary;
};


export default function SyncPage() {
  const [loading, setLoading] =
    useState<SyncType | null>(null);

  const [result, setResult] =
    useState<SyncResult | null>(null);

  const [error, setError] =
    useState<string | null>(null);


  async function runSync(
    type: SyncType
  ) {
    setLoading(type);
    setResult(null);
    setError(null);

    try {
      if (type === "history") {
        const response =
          await syncHistory();

        setResult({
          type,
          message: response.message,
          humanGames:
            response.human_games,
        });

        return;
      }

      if (type === "logs") {
        const response =
          await syncLogs();

        setResult({
          type,
          message: response.message,
          logSummary:
            response.summary,
        });

        return;
      }

      const response =
        await syncAll();

      setResult({
        type,
        message: response.message,
        humanGames:
          response.human_games,
        logSummary:
          response.log_summary,
      });

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unknown error"
      );
    } finally {
      setLoading(null);
    }
  }


  return (
    <AppShell>
      <div className="mb-8">
        <div className="mb-3 inline-flex rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-300">
          MLB The Show data collection
        </div>

        <h1 className="text-4xl font-black tracking-tight text-white">
          Sync
        </h1>

        <p className="mt-3 max-w-2xl text-slate-400">
          Update the local database with
          your latest MLB The Show 26
          online game history and game
          logs.
        </p>
      </div>


      <div className="grid gap-4 md:grid-cols-3">
        <SyncCard
          title="Sync History"
          description={
            "Fetch every available game-history page, "
            + "remove CPU games, and update the local database."
          }
          buttonLabel="Sync History"
          running={
            loading === "history"
          }
          disabled={
            loading !== null
          }
          onClick={() =>
            runSync("history")
          }
        />

        <SyncCard
          title="Sync Logs"
          description={
            "Fetch game logs only for stored games that "
            + "have never received a game-log API response."
          }
          buttonLabel="Sync Logs"
          running={
            loading === "logs"
          }
          disabled={
            loading !== null
          }
          onClick={() =>
            runSync("logs")
          }
        />

        <SyncCard
          title="Sync All"
          description={
            "Update game history first, then fetch any "
            + "newly discovered game logs."
          }
          buttonLabel="Sync All"
          running={
            loading === "all"
          }
          disabled={
            loading !== null
          }
          onClick={() =>
            runSync("all")
          }
        />
      </div>


      {loading && (
        <div className="card mt-6">
          <div className="text-sm font-bold text-white">
            Sync in progress
          </div>

          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            MLB The Show requests are
            intentionally paced. Keep this
            page open until the operation
            finishes.
          </p>
        </div>
      )}


      {result && (
        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
          <div className="border-b border-slate-800 bg-black px-6 py-5">
            <div className="text-sm font-black uppercase tracking-wide text-green-400">
              Sync Complete
            </div>

            <div className="mt-2 text-xl font-black text-white">
              {result.message}
            </div>
          </div>


          {result.humanGames !==
            undefined && (
            <div className="border-b border-slate-800 px-6 py-5">
              <div className="text-xs font-black uppercase tracking-wide text-slate-500">
                Human Games
              </div>

              <div className="mt-1 text-3xl font-black text-white">
                {result.humanGames}
              </div>

              <p className="mt-2 text-xs text-slate-500">
                CPU games are excluded
                from the local scouting
                database.
              </p>
            </div>
          )}


          {result.logSummary && (
            <LogSummary
              summary={
                result.logSummary
              }
            />
          )}
        </div>
      )}


      {error && (
        <div className="card mt-6 border-red-500/20 text-red-400">
          <div className="font-bold">
            Sync failed
          </div>

          <div className="mt-2 text-sm">
            {error}
          </div>
        </div>
      )}
    </AppShell>
  );
}


function SyncCard({
  title,
  description,
  buttonLabel,
  running,
  disabled,
  onClick,
}: {
  title: string;
  description: string;
  buttonLabel: string;
  running: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <div className="card flex flex-col">
      <h2 className="text-xl font-bold text-white">
        {title}
      </h2>

      <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-400">
        {description}
      </p>

      <button
        className="button mt-6"
        disabled={disabled}
        onClick={onClick}
      >
        {running
          ? "Running..."
          : buttonLabel}
      </button>
    </div>
  );
}


function LogSummary({
  summary,
}: {
  summary: GameLogSyncSummary;
}) {
  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
        <SummaryMetric
          label="Requested"
          value={summary.requested}
        />

        <SummaryMetric
          label="Successful"
          value={summary.ok}
        />

        <SummaryMetric
          label="Identity Mismatch"
          value={
            summary.identity_mismatch
          }
        />

        <SummaryMetric
          label="Not Found"
          value={summary.not_found}
        />

        <SummaryMetric
          label="API Errors"
          value={summary.api_error}
        />

        <SummaryMetric
          label="Request Failures"
          value={
            summary.request_failed
          }
        />
      </div>


      <div className="border-t border-slate-800 px-6 py-4 text-sm text-slate-400">
        {summary.requested === 0 ? (
          <span>
            Every stored game already has
            a recorded game-log result.
            Nothing needed to be fetched.
          </span>
        ) : (
          <span>
            Successful logs are preserved
            permanently. MLBTS identity
            mismatches and other API
            responses are recorded so they
            are not retried automatically
            on every sync.
          </span>
        )}

        {summary.preserved_ok > 0 && (
          <span className="ml-2 text-green-400">
            Existing successful logs
            preserved:{" "}
            {summary.preserved_ok}.
          </span>
        )}
      </div>
    </div>
  );
}


function SummaryMetric({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="border-b border-r border-slate-800 px-5 py-4">
      <div className="text-[10px] font-black uppercase tracking-wide text-slate-500">
        {label}
      </div>

      <div className="mt-1 text-2xl font-black text-white">
        {value}
      </div>
    </div>
  );
}