"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  AnalyticsInningRow,
  AnalyticsTrendGame,
  AnalyticsTrendsResponse,
  getAnalyticsTrends,
} from "@/lib/api";
import { formatGameDateTime } from "@/lib/dates";


const LIMIT_OPTIONS = [10, 20, 50, 100];


export default function AnalyticsPage() {
  const [limit, setLimit] = useState(20);
  const [report, setReport] =
    useState<AnalyticsTrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadAnalytics() {
      setLoading(true);
      setError(null);

      try {
        const result = await getAnalyticsTrends(limit);

        if (!cancelled) {
          setReport(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unknown error"
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadAnalytics();

    return () => {
      cancelled = true;
    };
  }, [limit]);

  const plateGames = report?.plate_discipline.games ?? [];
  const inningRows = report?.inning_scoring.innings ?? [];

  const maxPlateValue = Math.max(
    1,
    ...plateGames.flatMap((game) => [
      game.user_walks,
      game.user_strikeouts,
      game.opponent_walks,
      game.opponent_strikeouts,
    ])
  );

  const maxInningRate = Math.max(
    0.25,
    ...inningRows.flatMap((inning) => [
      inning.user_runs_per_observed_inning ?? 0,
      inning.opponent_runs_per_observed_inning ?? 0,
    ])
  );

  return (
    <AppShell>
      <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-3 inline-flex rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-300">
            Derived scouting trends
          </div>

          <h1 className="text-4xl font-black tracking-tight text-white">
            Analytics
          </h1>

          <p className="mt-3 max-w-3xl text-slate-400">
            Explore recent plate-discipline and inning-scoring
            tendencies from your locally stored MLB The Show data.
          </p>
        </div>

        <label className="w-full max-w-[12rem] text-sm font-semibold text-slate-300">
          Recent games
          <select
            className="input mt-2"
            value={limit}
            onChange={(event) =>
              setLimit(Number(event.target.value))
            }
          >
            {LIMIT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                Last {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && (
        <div className="card text-sm text-slate-300">
          Loading analytics...
        </div>
      )}

      {error && (
        <div className="card text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && report && (
        <div className="space-y-6">
          <SummaryGrid report={report} />

          <section className="card">
            <SectionHeader
              title="K / BB trend"
              subtitle={
                `${report.plate_discipline.games_included} `
                + "games with attributable team box scores"
              }
            />

            {plateGames.length === 0 ? (
              <EmptyState text="No K/BB trend data is available yet." />
            ) : (
              <>
                <div className="mt-6 overflow-x-auto pb-2">
                  <div
                    className="flex min-w-max items-end gap-3"
                    style={{ height: "18rem" }}
                  >
                    {plateGames.map((game) => (
                      <PlateGameBars
                        key={game.game_id}
                        game={game}
                        maxValue={maxPlateValue}
                      />
                    ))}
                  </div>
                </div>

                <Legend
                  items={[
                    ["BB For", "bg-blue-500"],
                    ["K For", "bg-cyan-300"],
                    ["BB Against", "bg-amber-400"],
                    ["K Against", "bg-rose-400"],
                  ]}
                />
              </>
            )}
          </section>

          <section className="card">
            <SectionHeader
              title="Scoring by inning"
              subtitle={
                `${report.inning_scoring.games_included} `
                + "games with structured inning data"
              }
            />

            {inningRows.length === 0 ? (
              <EmptyState text="No inning scoring data is available yet." />
            ) : (
              <>
                <div className="mt-6 overflow-x-auto pb-2">
                  <div
                    className="flex min-w-max items-end gap-4"
                    style={{ height: "18rem" }}
                  >
                    {inningRows.map((inning) => (
                      <InningBars
                        key={inning.inning}
                        inning={inning}
                        maxRate={maxInningRate}
                      />
                    ))}
                  </div>
                </div>

                <Legend
                  items={[
                    ["Runs For / observed inning", "bg-blue-500"],
                    ["Runs Against / observed inning", "bg-rose-400"],
                  ]}
                />
              </>
            )}
          </section>

          <section className="card">
            <SectionHeader
              title="Inning detail"
              subtitle="NULL run values are excluded from rate denominators."
            />

            <div className="mlb-table-wrap mt-5">
              <table className="mlb-table min-w-[940px]">
                <thead>
                  <tr>
                    <th>Inning</th>
                    <th className="numeric">Games</th>
                    <th className="numeric">For samples</th>
                    <th className="numeric">Against samples</th>
                    <th className="numeric divider-left">Runs for</th>
                    <th className="numeric">Runs against</th>
                    <th className="numeric divider-left">For / obs.</th>
                    <th className="numeric">Against / obs.</th>
                    <th className="numeric">Diff</th>
                  </tr>
                </thead>

                <tbody>
                  {inningRows.map((inning) => (
                    <tr key={inning.inning}>
                      <td className="primary">
                        {inning.inning}
                      </td>
                      <td className="numeric">
                        {inning.games_reaching_inning}
                      </td>
                      <td className="numeric">
                        {inning.user_innings_observed}
                      </td>
                      <td className="numeric">
                        {inning.opponent_innings_observed}
                      </td>
                      <td className="numeric divider-left">
                        {inning.user_runs}
                      </td>
                      <td className="numeric">
                        {inning.opponent_runs}
                      </td>
                      <td className="numeric divider-left">
                        {formatNumber(
                          inning.user_runs_per_observed_inning
                        )}
                      </td>
                      <td className="numeric">
                        {formatNumber(
                          inning.opponent_runs_per_observed_inning
                        )}
                      </td>
                      <td className="numeric">
                        {formatSigned(
                          inning.run_diff_per_observed_inning
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}


function SummaryGrid({
  report,
}: {
  report: AnalyticsTrendsResponse;
}) {
  const summary = report.plate_discipline.summary;

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <MetricCard
        label="K/BB games"
        value={report.plate_discipline.games_included}
      />
      <MetricCard
        label="BB / game"
        value={formatNumber(summary.user_walks_per_game)}
      />
      <MetricCard
        label="K / game"
        value={formatNumber(summary.user_strikeouts_per_game)}
      />
      <MetricCard
        label="Opp BB / game"
        value={formatNumber(summary.opponent_walks_per_game)}
      />
      <MetricCard
        label="Opp K / game"
        value={formatNumber(summary.opponent_strikeouts_per_game)}
      />
    </div>
  );
}


function PlateGameBars({
  game,
  maxValue,
}: {
  game: AnalyticsTrendGame;
  maxValue: number;
}) {
  const bars = [
    {
      value: game.user_walks,
      className: "bg-blue-500",
    },
    {
      value: game.user_strikeouts,
      className: "bg-cyan-300",
    },
    {
      value: game.opponent_walks,
      className: "bg-amber-400",
    },
    {
      value: game.opponent_strikeouts,
      className: "bg-rose-400",
    },
  ];

  return (
    <div className="flex h-full w-[4.75rem] shrink-0 flex-col justify-end">
      <div className="flex h-[13.5rem] items-end justify-center gap-1">
        {bars.map((bar, index) => (
          <div
            key={index}
            className={`w-3 rounded-t-sm ${bar.className}`}
            style={{
              height: `${Math.max(
                2,
                (bar.value / maxValue) * 100
              )}%`,
            }}
            title={String(bar.value)}
          />
        ))}
      </div>

      <div className="mt-3 truncate text-center text-[10px] font-bold text-slate-300">
        {game.opponent_name || "Unknown"}
      </div>

      <div className="mt-1 text-center text-[9px] text-slate-600">
        {formatGameDateTime(game.display_date)}
      </div>
    </div>
  );
}


function InningBars({
  inning,
  maxRate,
}: {
  inning: AnalyticsInningRow;
  maxRate: number;
}) {
  const userRate =
    inning.user_runs_per_observed_inning ?? 0;
  const opponentRate =
    inning.opponent_runs_per_observed_inning ?? 0;

  return (
    <div className="flex h-full w-[5.5rem] shrink-0 flex-col justify-end">
      <div className="flex h-[13.5rem] items-end justify-center gap-2">
        <RateBar
          value={inning.user_runs_per_observed_inning}
          maxValue={maxRate}
          className="bg-blue-500"
        />
        <RateBar
          value={inning.opponent_runs_per_observed_inning}
          maxValue={maxRate}
          className="bg-rose-400"
        />
      </div>

      <div className="mt-3 text-center text-xs font-black text-white">
        {inning.inning}
      </div>

      <div className="mt-1 text-center text-[9px] text-slate-600">
        {inning.user_innings_observed}/
        {inning.opponent_innings_observed} samples
      </div>

      <div className="sr-only">
        For {userRate}; against {opponentRate}
      </div>
    </div>
  );
}


function RateBar({
  value,
  maxValue,
  className,
}: {
  value: number | null;
  maxValue: number;
  className: string;
}) {
  if (value === null) {
    return (
      <div
        className="w-5 rounded-t-sm border border-dashed border-slate-700"
        style={{ height: "0.5rem" }}
        title="No observed data"
      />
    );
  }

  return (
    <div
      className={`w-5 rounded-t-sm ${className}`}
      style={{
        height: `${Math.max(
          2,
          (value / maxValue) * 100
        )}%`,
      }}
      title={value.toFixed(2)}
    />
  );
}


function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="card">
      <div className="text-[11px] font-black uppercase tracking-[0.14em] text-slate-500">
        {label}
      </div>

      <div className="mt-2 text-3xl font-black tracking-tight text-white">
        {value}
      </div>
    </div>
  );
}


function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div>
      <h2 className="text-xl font-black text-white">
        {title}
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        {subtitle}
      </p>
    </div>
  );
}


function EmptyState({
  text,
}: {
  text: string;
}) {
  return (
    <div className="mt-6 rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-500">
      {text}
    </div>
  );
}


function Legend({
  items,
}: {
  items: Array<[string, string]>;
}) {
  return (
    <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-400">
      {items.map(([label, className]) => (
        <div
          key={label}
          className="flex items-center gap-2"
        >
          <span
            className={`h-2.5 w-2.5 rounded-sm ${className}`}
          />
          {label}
        </div>
      ))}
    </div>
  );
}


function formatNumber(
  value: number | null
): string {
  return value === null
    ? "N/A"
    : value.toFixed(2);
}


function formatSigned(
  value: number | null
): string {
  if (value === null) {
    return "N/A";
  }

  if (value > 0) {
    return `+${value.toFixed(2)}`;
  }

  return value.toFixed(2);
}
