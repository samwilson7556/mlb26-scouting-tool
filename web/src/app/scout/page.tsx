"use client";

import { formatGameDateTime } from "@/lib/dates";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import {
  getLocalOpponent,
  liveScout,
  LiveScoutResponse,
  LocalOpponentResponse,
} from "@/lib/api";

export default function ScoutPage() {
  const [username, setUsername] = useState("");
  const [platform, setPlatform] = useState("psn");
  const [pages, setPages] = useState(1);
  const [maxGames, setMaxGames] = useState(25);
  const [includeLogs, setIncludeLogs] = useState(false);
  const [logWorkers, setLogWorkers] = useState(5);
  const [loading, setLoading] = useState(false);
  const [localReport, setLocalReport] = useState<LocalOpponentResponse | null>(
    null
  );
  const [liveReport, setLiveReport] = useState<LiveScoutResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runLocalScout() {
    setLoading(true);
    setError(null);
    setLocalReport(null);
    setLiveReport(null);

    try {
      const result = await getLocalOpponent(username);
      setLocalReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function runLiveScout() {
    setLoading(true);
    setError(null);
    setLocalReport(null);
    setLiveReport(null);

    try {
      const result = await liveScout({
        username,
        platform,
        pages,
        max_games: maxGames,
        include_logs: includeLogs,
        log_workers: logWorkers,
      });

      setLiveReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="mb-8">
        <div className="mb-3 inline-flex rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-300">
          Local + live opponent scouting
        </div>

        <h1 className="text-4xl font-black tracking-tight text-white">Scout</h1>

        <p className="mt-3 max-w-2xl text-slate-400">
          Look up local opponent history or run live scouting directly from MLB
          The Show.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-4">
        <div className="card lg:col-span-1">
          <label className="text-sm font-semibold text-slate-300">
            Username
          </label>
          <input
            className="input mt-2"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Opponent username"
          />

          <label className="mt-4 block text-sm font-semibold text-slate-300">
            Platform
          </label>
          <select
            className="input mt-2"
            value={platform}
            onChange={(event) => setPlatform(event.target.value)}
          >
            <option value="psn">PSN</option>
            <option value="xbl">Xbox</option>
            <option value="mlbts">MLB The Show</option>
            <option value="nsw">Nintendo Switch</option>
          </select>

          <label className="mt-4 block text-sm font-semibold text-slate-300">
            Pages
          </label>
          <input
            className="input mt-2"
            type="number"
            min={1}
            max={25}
            value={pages}
            onChange={(event) => setPages(Number(event.target.value))}
          />

          <label className="mt-4 block text-sm font-semibold text-slate-300">
            Max Games
          </label>
          <input
            className="input mt-2"
            type="number"
            min={1}
            max={250}
            value={maxGames}
            onChange={(event) => setMaxGames(Number(event.target.value))}
          />

          <label className="mt-4 block text-sm font-semibold text-slate-300">
            Game Log Workers
          </label>
          <input
            className="input mt-2"
            type="number"
            min={1}
            max={10}
            value={logWorkers}
            onChange={(event) => setLogWorkers(Number(event.target.value))}
          />

          <p className="mt-2 text-xs leading-relaxed text-slate-500">
            Used only when Include game logs is enabled. Start with 5. Use 8-10
            only if the site handles it well.
          </p>

          <label className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-300">
            <input
              type="checkbox"
              checked={includeLogs}
              onChange={(event) => setIncludeLogs(event.target.checked)}
            />
            Include game logs
          </label>

          <div className="mt-6 grid gap-3">
            <button
              className="button-secondary"
              disabled={!username || loading}
              onClick={runLocalScout}
            >
              {loading ? "Working..." : "Local Scout"}
            </button>

            <button
              className="button"
              disabled={!username || loading}
              onClick={runLiveScout}
            >
              {loading ? "Working..." : "Live Scout"}
            </button>
          </div>
        </div>

        <div className="space-y-5 lg:col-span-3">
          {loading && (
            <div className="card text-sm text-slate-300">
              Running scout report. If game logs are included, this may take a
              bit while game pages are primed and logs are fetched.
            </div>
          )}

          {error && <div className="card text-red-400">{error}</div>}

          {localReport && (
            <div className="card">
              <h2 className="text-xl font-bold text-white">
                Local Scout Report
              </h2>

              {!localReport.found ? (
                <p className="mt-4 text-yellow-400">{localReport.message}</p>
              ) : (
                <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <Stat label="Opponent" value={localReport.opponent} />
                  <Stat label="Games" value={localReport.games_played} />
                  <Stat label="Record" value={localReport.your_record} />
                  <Stat
                    label="Avg Runs For"
                    value={localReport.avg_runs_scored}
                  />
                  <Stat
                    label="Avg Runs Allowed"
                    value={localReport.avg_runs_allowed}
                  />
                  <Stat label="Last Played" value={localReport.last_played} />
                </div>
              )}
            </div>
          )}

          {liveReport && (
            <div className="space-y-5">
              <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl shadow-black/30">
                <div className="border-b border-slate-800 bg-black px-6 py-5">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                    <div>
                      <h2 className="text-2xl font-black tracking-tight text-white">
                        Live Scout Report: {liveReport.username}
                      </h2>

                      <p className="mt-2 text-sm text-slate-400">
                        Platform:{" "}
                        <span className="font-bold text-white">
                          {liveReport.platform}
                        </span>{" "}
                        <span className="text-slate-700">|</span> Mode:{" "}
                        <span className="font-bold text-white">
                          {liveReport.mode}
                        </span>
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <MiniStat
                        label="Games"
                        value={liveReport.recent_games_analyzed}
                      />
                      <MiniStat
                        label="Record"
                        value={`${liveReport.record.wins}-${liveReport.record.losses}`}
                      />
                      <MiniStat label="Win%" value={liveReport.record.win_pct} />
                      <MiniStat
                        label="Logs"
                        value={`${liveReport.advanced_from_game_logs.logs_fetched}/${liveReport.advanced_from_game_logs.logs_failed}`}
                      />
                    </div>
                  </div>
                </div>

                <div className="grid gap-0 xl:grid-cols-3">
                  <ReportSection title="Performance">
                    <LargeMetric
                      label="Recent Record"
                      value={`${liveReport.record.wins}-${liveReport.record.losses}`}
                    />
                    <LargeMetric label="Win%" value={liveReport.record.win_pct} />
                  </ReportSection>

                  <ReportSection title="Offense">
                    <LargeMetric
                      label="Runs/Game"
                      value={
                        liveReport.averages_from_game_history
                          .runs_scored_per_game
                      }
                    />
                    <LargeMetric
                      label="Hits/Game"
                      value={
                        liveReport.averages_from_game_history.hits_for_per_game
                      }
                    />
                    <LargeMetric
                      label="Batting Avg"
                      value={
                        liveReport.advanced_from_game_logs.batting_average ??
                        "Use logs"
                      }
                    />
                  </ReportSection>

                  <ReportSection title="Run Prevention">
                    <LargeMetric
                      label="Runs Allowed/Game"
                      value={
                        liveReport.averages_from_game_history
                          .runs_allowed_per_game
                      }
                    />
                    <LargeMetric
                      label="Hits Allowed/Game"
                      value={
                        liveReport.averages_from_game_history
                          .hits_allowed_per_game
                      }
                    />
                    <LargeMetric
                      label="ERA"
                      value={
                        liveReport.advanced_from_game_logs.era ?? "Use logs"
                      }
                    />
                  </ReportSection>
                </div>

                <div className="grid border-t border-slate-800 bg-slate-950/70 md:grid-cols-2 xl:grid-cols-4">
                  <InfoMetric
                    label="Human Games Found"
                    value={liveReport.human_games_found}
                  />
                  <InfoMetric
                    label="CPU Games Removed"
                    value={liveReport.cpu_games_removed}
                  />
                  <InfoMetric
                    label="Skipped Unattributable"
                    value={liveReport.skipped_unattributable_games}
                  />
                  <InfoMetric
                    label="Game Log Workers"
                    value={liveReport.advanced_from_game_logs.worker_count}
                  />
                </div>
              </div>

              <div className="overflow-hidden rounded-2xl border border-slate-800 bg-black shadow-2xl shadow-black/30">
                <div className="border-b border-slate-800 bg-black px-5 py-4">
                  <h3 className="text-sm font-black uppercase tracking-wide text-white">
                    Recent Games
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Game IDs open the MLB The Show game page in a new tab.
                  </p>
                </div>

                <div className="mlb-table-wrap">
                  <table className="mlb-table min-w-[920px]">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th className="center">Result</th>
                        <th>Opponent</th>
                        <th className="numeric divider-left">Score</th>
                        <th className="numeric">Hits</th>
                        <th className="numeric divider-left">Game ID</th>
                      </tr>
                    </thead>

                    <tbody>
                      {liveReport.games.map((game) => (
                        <tr key={game.id}>
                          <td className="whitespace-nowrap">
                            {formatGameDateTime(game.display_date)}
                          </td>

                          <td className="center">
                            <ResultBadge result={game.result} />
                          </td>

                          <td>
                            <OpponentCell
                              username={game.opponent_name}
                              team={game.opponent_team}
                            />
                          </td>

                          <td className="numeric divider-left primary">
                            {game.runs_for}-{game.runs_against}
                          </td>

                          <td className="numeric">
                            {game.hits_for}-{game.hits_against}
                          </td>

                          <td className="numeric divider-left font-mono text-xs">
                            <a
                              href={buildLiveGameUrl(
                                game.id,
                                liveReport.platform,
                                liveReport.username
                              )}
                              target="_blank"
                              rel="noreferrer"
                              className="mlb-link"
                              title="Open game page in a new tab"
                            >
                              {game.id}
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {liveReport.games.length === 0 && (
                    <div className="p-8 text-center text-sm text-slate-400">
                      No recent games found.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

function ReportSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-slate-800 p-6 xl:border-b-0 xl:border-r">
      <h3 className="mb-5 text-xs font-black uppercase tracking-[0.16em] text-slate-500">
        {title}
      </h3>

      <div className="grid gap-4">{children}</div>
    </section>
  );
}

function LargeMetric({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="rounded-xl bg-black/45 px-4 py-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-3xl font-black tracking-tight text-white">
        {value ?? "N/A"}
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="rounded-xl bg-slate-950 px-4 py-3 text-center">
      <div className="text-[10px] font-black uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-lg font-black text-white">{value ?? "N/A"}</div>
    </div>
  );
}

function InfoMetric({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="border-b border-slate-800 px-6 py-4 md:border-r xl:border-b-0">
      <div className="text-[11px] font-black uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-xl font-black text-white">{value ?? "N/A"}</div>
    </div>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div
      className="rounded-2xl bg-slate-950/70 p-4 shadow-sm"
      style={{
        border: "none",
        outline: "none",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)",
      }}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-2xl font-black text-white">{value ?? "N/A"}</div>
    </div>
  );
}

function OpponentCell({
  username,
  team,
}: {
  username: string | null | undefined;
  team: string | null | undefined;
}) {
  return (
    <div className="min-w-[12rem]">
      <div className="primary leading-tight">{username || "Unknown"}</div>
      <div className="secondary mt-1 leading-tight">
        {team || "Unknown team"}
      </div>
    </div>
  );
}

function ResultBadge({ result }: { result: string | null }) {
  if (result === "W") {
    return <span className="result-win">WIN</span>;
  }

  if (result === "L") {
    return <span className="result-loss">LOSS</span>;
  }

  return <span className="result-na">N/A</span>;
}




function buildLiveGameUrl(
  gameId: string,
  platform: string,
  username: string
): string {
  const params = new URLSearchParams({
    platform,
    username,
  });

  return `https://mlb26.theshow.com/games/${gameId}?${params.toString()}`;
}