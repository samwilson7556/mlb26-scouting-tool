"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  GameLogSyncSummary,
  SyncJob,
  SyncType,
  getLatestSyncJob,
  getSyncJob,
  startSyncJob,
} from "@/lib/api";


const POLL_INTERVAL_MS = 1000;


export default function SyncPage() {
  const [job, setJob] =
    useState<SyncJob | null>(null);

  const [starting, setStarting] =
    useState<SyncType | null>(null);

  const [error, setError] =
    useState<string | null>(null);


  useEffect(() => {
    let cancelled = false;

    async function restoreLatestJob() {
      try {
        const response =
          await getLatestSyncJob();

        if (!cancelled) {
          setJob(response.job);
        }
      } catch {
        // The API may not be running yet. The
        // page can still start a new sync later.
      }
    }

    restoreLatestJob();

    return () => {
      cancelled = true;
    };
  }, []);


  useEffect(() => {
    if (
      !job
      || (
        job.status !== "queued"
        && job.status !== "running"
      )
    ) {
      return;
    }

    let cancelled = false;

    const timer = window.setInterval(
      async () => {
        try {
          const response =
            await getSyncJob(job.id);

          if (!cancelled) {
            setJob(response);
          }
        } catch (err) {
          if (!cancelled) {
            setError(
              err instanceof Error
                ? err.message
                : "Failed to refresh sync status."
            );
          }
        }
      },
      POLL_INTERVAL_MS
    );

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [job]);


  async function runSync(
    type: SyncType
  ) {
    setStarting(type);
    setError(null);

    try {
      const response =
        await startSyncJob(type);

      setJob(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unknown error"
      );

      try {
        const latest =
          await getLatestSyncJob();

        if (latest.job) {
          setJob(latest.job);
        }
      } catch {
        // Keep the original error.
      }
    } finally {
      setStarting(null);
    }
  }


  const active =
    job?.status === "queued"
    || job?.status === "running";

  const activeType =
    active
      ? job.type
      : starting;


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
          Start a background sync and keep
          using the app while MLB The Show
          requests are processed.
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
            activeType === "history"
          }
          disabled={
            active || starting !== null
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
            activeType === "logs"
          }
          disabled={
            active || starting !== null
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
            activeType === "all"
          }
          disabled={
            active || starting !== null
          }
          onClick={() =>
            runSync("all")
          }
        />
      </div>


      {job && active && (
        <SyncProgress job={job} />
      )}


      {job?.status === "completed" && (
        <SyncResult job={job} />
      )}


      {job?.status === "failed" && (
        <div className="card mt-6 border-red-500/20 text-red-400">
          <div className="font-bold">
            Sync failed
          </div>

          <div className="mt-2 text-sm">
            {job.error
              || "The background sync failed."}
          </div>
        </div>
      )}


      {error && (
        <div className="card mt-6 border-red-500/20 text-red-400">
          <div className="font-bold">
            Sync request error
          </div>

          <div className="mt-2 text-sm">
            {error}
          </div>
        </div>
      )}
    </AppShell>
  );
}


function SyncProgress({
  job,
}: {
  job: SyncJob;
}) {
  const hasNumericProgress =
    job.phase === "logs"
    && job.progress_total > 0;

  const percent =
    hasNumericProgress
      ? Math.min(
          100,
          Math.round(
            (
              job.progress_current
              / job.progress_total
            ) * 100
          )
        )
      : 0;

  return (
    <div className="card mt-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-sm font-bold text-white">
            Sync in progress
          </div>

          <p className="mt-1 text-sm text-slate-400">
            {job.message}
          </p>
        </div>

        <div className="text-xs font-black uppercase tracking-wide text-blue-300">
          {formatPhase(job.phase)}
        </div>
      </div>

      {hasNumericProgress ? (
        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between text-xs font-bold text-slate-400">
            <span>
              {job.progress_current} of{" "}
              {job.progress_total} logs
            </span>

            <span>{percent}%</span>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-300"
              style={{
                width: `${percent}%`,
              }}
            />
          </div>

          {job.current_game_id && (
            <div className="mt-3 font-mono text-xs text-slate-500">
              Current game:{" "}
              {job.current_game_id}
            </div>
          )}
        </div>
      ) : (
        <p className="mt-4 text-xs leading-relaxed text-slate-500">
          The background job is still
          running. You can navigate away
          from this page and return later;
          the local API continues the sync.
        </p>
      )}

      {job.log_summary && (
        <div className="mt-5 border-t border-slate-800 pt-4">
          <div className="text-xs text-slate-500">
            Successful:{" "}
            {job.log_summary.ok}
            {" • "}Request failures:{" "}
            {job.log_summary.request_failed}
            {" • "}API errors:{" "}
            {job.log_summary.api_error}
          </div>
        </div>
      )}
    </div>
  );
}


function SyncResult({
  job,
}: {
  job: SyncJob;
}) {
  return (
    <div className="mt-6 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <div className="border-b border-slate-800 bg-black px-6 py-5">
        <div className="text-sm font-black uppercase tracking-wide text-green-400">
          Sync Complete
        </div>

        <div className="mt-2 text-xl font-black text-white">
          {job.message}
        </div>
      </div>

      {job.human_games !== null && (
        <div className="border-b border-slate-800 px-6 py-5">
          <div className="text-xs font-black uppercase tracking-wide text-slate-500">
            Human Games
          </div>

          <div className="mt-1 text-3xl font-black text-white">
            {job.human_games}
          </div>

          <p className="mt-2 text-xs text-slate-500">
            CPU games are excluded from
            the local scouting database.
          </p>
        </div>
      )}

      {job.log_summary && (
        <LogSummary
          summary={job.log_summary}
        />
      )}
    </div>
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
        className="button mt-6 disabled:cursor-not-allowed disabled:opacity-50"
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


function formatPhase(
  phase: SyncJob["phase"]
): string {
  if (phase === "history") {
    return "Game History";
  }

  if (phase === "logs") {
    return "Game Logs";
  }

  if (phase === "complete") {
    return "Complete";
  }

  return "Queued";
}
