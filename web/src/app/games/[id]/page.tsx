"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  AppConfigResponse,
  GameDetailResponse,
  GameEvent,
  GameInning,
  PlayerBattingStat,
  PlayerPitchingStat,
  TeamBoxScore,
  getAppConfig,
  getGameDetail,
} from "@/lib/api";
import { formatGameDateTime } from "@/lib/dates";


export default function GameDetailPage() {
  const params = useParams<{ id: string }>();
  const gameId = decodeURIComponent(params.id);

  const [detail, setDetail] =
    useState<GameDetailResponse | null>(null);

  const [config, setConfig] =
    useState<AppConfigResponse | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);

      try {
        const [
          detailResult,
          configResult,
        ] = await Promise.all([
          getGameDetail(gameId),
          getAppConfig(),
        ]);

        setDetail(detailResult);
        setConfig(configResult);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load game details."
        );
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [gameId]);

  const rawGameHistory = useMemo(
    () =>
      prettyJson(
        detail?.game
          .raw_game_history_json
      ),
    [
      detail?.game
        .raw_game_history_json,
    ]
  );

  const rawGameLog = useMemo(
    () =>
      prettyJson(
        detail?.game_log
          ?.raw_game_log_json
      ),
    [
      detail?.game_log
        ?.raw_game_log_json,
    ]
  );

  return (
    <AppShell>
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <Link
            href="/games"
            className="text-sm font-bold text-blue-300 hover:text-blue-200"
          >
            ← Back to Games
          </Link>

          <div className="mt-4 text-xs font-black uppercase tracking-[0.18em] text-slate-500">
            Game {gameId}
          </div>

          <h1 className="mt-2 text-4xl font-black tracking-tight text-white">
            Game Detail
          </h1>

          <p className="mt-3 max-w-2xl text-slate-400">
            Local game history, parsed box
            score, player statistics, and
            stored MLBTS game-log data.
          </p>
        </div>

        {config && (
          <a
            href={buildGameUrl(
              gameId,
              config
            )}
            target="_blank"
            rel="noreferrer"
            className="button-secondary inline-flex items-center justify-center"
          >
            Open on MLBTS ↗
          </a>
        )}
      </div>

      {loading && (
        <div className="card text-sm text-slate-400">
          Loading game details...
        </div>
      )}

      {error && (
        <div className="card border-red-900/60 text-sm text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && detail && (
        <div className="space-y-6">
          <GameSummaryCard detail={detail} />
          <TeamBoxScoreTable rows={detail.team_box_scores} />
          <BattingTable rows={detail.batting_stats} />
          <PitchingTable rows={detail.pitching_stats} />

          <StoredGameLog
            status={detail.game_log?.api_status}
            fetchedAt={detail.game_log?.fetched_at}
            text={detail.game_log?.raw_text_log}
            innings={detail.innings}
            events={detail.events}
            awayTeam={detail.game.away_full_name}
            homeTeam={detail.game.home_full_name}
          />

          <RawDataSection
            title="Raw Game History JSON"
            content={rawGameHistory}
          />

          <RawDataSection
            title="Raw Game Log JSON"
            content={rawGameLog}
          />
        </div>
      )}
    </AppShell>
  );
}


function GameSummaryCard({
  detail,
}: {
  detail: GameDetailResponse;
}) {
  const { game } = detail;

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70">
      <div className="border-b border-slate-800 px-5 py-4">
        <div className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">
          Final
        </div>

        <div className="mt-1 text-sm text-slate-400">
          {formatGameDateTime(game.display_date)}
        </div>
      </div>

      <div className="grid gap-px bg-slate-800 md:grid-cols-[1fr_auto_1fr]">
        <TeamSummary
          label="Away"
          team={game.away_full_name}
          username={game.away_name}
          runs={game.away_runs}
          hits={game.away_hits}
          errors={game.away_errors}
        />

        <div className="flex min-w-28 flex-col items-center justify-center bg-slate-950 px-6 py-8">
          <div className="text-4xl font-black tabular-nums text-white">
            {game.away_runs}
            <span className="mx-3 text-slate-600">–</span>
            {game.home_runs}
          </div>

          <div className="mt-3">
            <ResultBadge result={game.user_result} />
          </div>
        </div>

        <TeamSummary
          label="Home"
          team={game.home_full_name}
          username={game.home_name}
          runs={game.home_runs}
          hits={game.home_hits}
          errors={game.home_errors}
        />
      </div>
    </section>
  );
}


function TeamSummary({
  label,
  team,
  username,
  runs,
  hits,
  errors,
}: {
  label: string;
  team: string | null | undefined;
  username: string | null | undefined;
  runs: number | null | undefined;
  hits: number | null | undefined;
  errors: number | null | undefined;
}) {
  return (
    <div className="bg-slate-900 px-6 py-8">
      <div className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">
        {label}
      </div>

      <div className="mt-2 text-2xl font-black text-white">
        {team || "Unknown Team"}
      </div>

      <div className="mt-1 text-sm text-slate-400">
        {username || "Unknown user"}
      </div>

      <div className="mt-5 flex gap-6 text-sm">
        <StatPair label="R" value={runs} />
        <StatPair label="H" value={hits} />
        <StatPair label="E" value={errors} />
      </div>
    </div>
  );
}


function StatPair({
  label,
  value,
}: {
  label: string;
  value: number | null | undefined;
}) {
  return (
    <div>
      <div className="text-[10px] font-black uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-lg font-black tabular-nums text-white">
        {value ?? "-"}
      </div>
    </div>
  );
}


function SectionHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="border-b border-slate-800 bg-slate-950 px-5 py-4">
      <h2 className="text-sm font-black uppercase tracking-[0.14em] text-white">
        {title}
      </h2>

      {description && (
        <p className="mt-1 text-xs text-slate-500">
          {description}
        </p>
      )}
    </div>
  );
}


function TeamBoxScoreTable({
  rows,
}: {
  rows: TeamBoxScore[];
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <SectionHeader
        title="Team Box Score"
        description={
          rows.length
            ? "Parsed from the stored MLBTS game log."
            : "No parsed team box score is stored for this game."
        }
      />

      {rows.length > 0 && (
        <div className="mlb-table-wrap rounded-none">
          <table className="mlb-table min-w-[900px]">
            <thead>
              <tr>
                <th>Team</th>
                <th className="numeric">R</th>
                <th className="numeric">H</th>
                <th className="numeric">E</th>
                <th className="numeric divider-left">AB</th>
                <th className="numeric">BB</th>
                <th className="numeric">SO</th>
                <th className="numeric divider-left">IP</th>
                <th className="numeric">H</th>
                <th className="numeric">ER</th>
                <th className="numeric">BB</th>
                <th className="numeric">SO</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.game_id}-${row.team_id}`}>
                  <td className="primary">{row.team_name || "Unknown"}</td>
                  <td className="numeric">{show(row.runs)}</td>
                  <td className="numeric">{show(row.hits)}</td>
                  <td className="numeric">{show(row.errors)}</td>
                  <td className="numeric divider-left">{show(row.batting_ab)}</td>
                  <td className="numeric">{show(row.batting_bb)}</td>
                  <td className="numeric">{show(row.batting_so)}</td>
                  <td className="numeric divider-left">{show(row.pitching_ip)}</td>
                  <td className="numeric">{show(row.pitching_h)}</td>
                  <td className="numeric">{show(row.pitching_er)}</td>
                  <td className="numeric">{show(row.pitching_bb)}</td>
                  <td className="numeric">{show(row.pitching_so)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}


function BattingTable({
  rows,
}: {
  rows: PlayerBattingStat[];
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <SectionHeader
        title="Batting"
        description={
          rows.length
            ? `${rows.length} player batting line${rows.length === 1 ? "" : "s"}`
            : "No parsed batting statistics are stored for this game."
        }
      />

      {rows.length > 0 && (
        <div className="mlb-table-wrap rounded-none">
          <table className="mlb-table min-w-[900px]">
            <thead>
              <tr>
                <th>Player</th>
                <th>Team</th>
                <th className="numeric divider-left">AB</th>
                <th className="numeric">R</th>
                <th className="numeric">H</th>
                <th className="numeric">RBI</th>
                <th className="numeric">BB</th>
                <th className="numeric">SO</th>
                <th className="numeric">2B</th>
                <th className="numeric">3B</th>
                <th className="numeric">HR</th>
                <th className="numeric">SB</th>
                <th className="numeric">CS</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.game_id}-${row.team_id}-${row.player_name}`}>
                  <td className="primary">{row.player_name || "Unknown"}</td>
                  <td>{row.team_name || "-"}</td>
                  <td className="numeric divider-left">{show(row.ab)}</td>
                  <td className="numeric">{show(row.r)}</td>
                  <td className="numeric">{show(row.h)}</td>
                  <td className="numeric">{show(row.rbi)}</td>
                  <td className="numeric">{show(row.bb)}</td>
                  <td className="numeric">{show(row.so)}</td>
                  <td className="numeric">{show(row.doubles)}</td>
                  <td className="numeric">{show(row.triples)}</td>
                  <td className="numeric">{show(row.hr)}</td>
                  <td className="numeric">{show(row.sb)}</td>
                  <td className="numeric">{show(row.cs)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}


function PitchingTable({
  rows,
}: {
  rows: PlayerPitchingStat[];
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <SectionHeader
        title="Pitching"
        description={
          rows.length
            ? `${rows.length} player pitching line${rows.length === 1 ? "" : "s"}`
            : "No parsed pitching statistics are stored for this game."
        }
      />

      {rows.length > 0 && (
        <div className="mlb-table-wrap rounded-none">
          <table className="mlb-table min-w-[850px]">
            <thead>
              <tr>
                <th>Player</th>
                <th>Team</th>
                <th className="numeric divider-left">IP</th>
                <th className="numeric">H</th>
                <th className="numeric">R</th>
                <th className="numeric">ER</th>
                <th className="numeric">BB</th>
                <th className="numeric">SO</th>
                <th className="numeric divider-left">W</th>
                <th className="numeric">L</th>
                <th className="numeric">SV</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.game_id}-${row.team_id}-${row.player_name}`}>
                  <td className="primary">{row.player_name || "Unknown"}</td>
                  <td>{row.team_name || "-"}</td>
                  <td className="numeric divider-left">{show(row.ip)}</td>
                  <td className="numeric">{show(row.h)}</td>
                  <td className="numeric">{show(row.r)}</td>
                  <td className="numeric">{show(row.er)}</td>
                  <td className="numeric">{show(row.bb)}</td>
                  <td className="numeric">{show(row.so)}</td>
                  <td className="numeric divider-left">{show(row.win)}</td>
                  <td className="numeric">{show(row.loss)}</td>
                  <td className="numeric">{show(row.save)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}


type PlayByPlayGroup = {
  key: string;
  inning: number;
  battingSide: string;
  battingTeamName: string | null;
  events: GameEvent[];
};


function StoredGameLog({
  status,
  fetchedAt,
  text,
  innings,
  events,
  awayTeam,
  homeTeam,
}: {
  status: string | null | undefined;
  fetchedAt: string | null | undefined;
  text: string | null | undefined;
  innings: GameInning[];
  events: GameEvent[];
  awayTeam: string | null | undefined;
  homeTeam: string | null | undefined;
}) {
  const groups =
    groupPlayByPlayEvents(events);

  const sourceDescription = status
    ? [
        `API status: ${status}`,
        fetchedAt
          ? `fetched ${formatGameDateTime(fetchedAt)}`
          : null,
        events.length
          ? `${events.length} normalized events`
          : null,
      ]
        .filter(Boolean)
        .join(" • ")
    : "No game-log API response is stored for this game.";

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <SectionHeader
        title="Play-by-Play"
        description={sourceDescription}
      />

      {groups.length > 0 ? (
        <div className="divide-y divide-slate-800">
          {groups.map((group) => {
            const inningLine = innings.find(
              (inning) =>
                inning.inning === group.inning
            );

            return (
              <div
                key={group.key}
                className="px-5 py-5"
              >
                <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg border border-blue-500/25 bg-blue-500/10 px-3 py-2 text-xs font-black uppercase tracking-[0.12em] text-blue-300">
                      {formatHalfInning(
                        group.inning,
                        group.battingSide
                      )}
                    </div>

                    <div>
                      <div className="font-black text-white">
                        {group.battingTeamName ||
                          "Unknown team"}{" "}
                        batting
                      </div>
                      <div className="mt-0.5 text-xs text-slate-500">
                        {group.events.length}{" "}
                        {group.events.length === 1
                          ? "event"
                          : "events"}
                      </div>
                    </div>
                  </div>

                  <InningRunSummary
                    inning={inningLine}
                    awayTeam={awayTeam}
                    homeTeam={homeTeam}
                  />
                </div>

                <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/45">
                  {group.events.map(
                    (event, index) => (
                      <div
                        key={`${event.id}-${event.source_index}`}
                        className={[
                          "flex gap-3 px-4 py-3",
                          index > 0
                            ? "border-t border-slate-800/80"
                            : "",
                          event.event_type ===
                          "pitcher_marker"
                            ? "bg-slate-950/45"
                            : "",
                        ].join(" ")}
                      >
                        <div className="w-24 shrink-0 pt-0.5">
                          <span
                            className={[
                              "inline-flex rounded-md px-2 py-1 text-[10px] font-black uppercase tracking-[0.08em]",
                              eventBadgeClass(
                                event.event_type
                              ),
                            ].join(" ")}
                          >
                            {eventLabel(
                              event.event_type
                            )}
                          </span>
                        </div>

                        <div
                          className={
                            event.event_type ===
                            "pitcher_marker"
                              ? "text-sm text-slate-400"
                              : "text-sm leading-6 text-slate-200"
                          }
                        >
                          {cleanMlbtsText(
                            event.raw_text
                          )}
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : text ? (
        <div className="p-5">
          <div className="mb-3 text-xs font-black uppercase tracking-[0.12em] text-amber-300">
            Formatted source text
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/45 p-4 text-sm leading-7 text-slate-300">
            {cleanMlbtsText(text)}
          </div>
        </div>
      ) : (
        <div className="p-5 text-sm text-slate-500">
          No play-by-play data is available.
        </div>
      )}

      {text && (
        <details className="border-t border-slate-800">
          <summary className="cursor-pointer px-5 py-4 text-xs font-black uppercase tracking-[0.12em] text-slate-500 transition hover:text-slate-300">
            Raw stored game log
          </summary>

          <div className="border-t border-slate-800 p-5">
            <p className="mb-3 text-xs text-slate-500">
              Original MLBTS text, including source formatting codes.
              Kept here for debugging and verification.
            </p>

            <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-800 bg-black p-4 font-mono text-xs leading-6 text-slate-400">
              {text}
            </pre>
          </div>
        </details>
      )}
    </section>
  );
}


function InningRunSummary({
  inning,
  awayTeam,
  homeTeam,
}: {
  inning: GameInning | undefined;
  awayTeam: string | null | undefined;
  homeTeam: string | null | undefined;
}) {
  if (
    !inning ||
    (
      inning.away_runs === null &&
      inning.home_runs === null
    )
  ) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 text-xs font-bold text-slate-400">
      <span className="rounded-md bg-slate-900 px-2.5 py-1.5">
        Inning runs
      </span>
      <span className="rounded-md bg-slate-900 px-2.5 py-1.5">
        {awayTeam || "Away"}{" "}
        <span className="text-white">
          {inning.away_runs ?? "—"}
        </span>
      </span>
      <span className="rounded-md bg-slate-900 px-2.5 py-1.5">
        {homeTeam || "Home"}{" "}
        <span className="text-white">
          {inning.home_runs ?? "—"}
        </span>
      </span>
    </div>
  );
}


function groupPlayByPlayEvents(
  events: GameEvent[]
): PlayByPlayGroup[] {
  const groups: PlayByPlayGroup[] = [];

  for (const event of events) {
    if (
      event.event_type === "batter_marker" ||
      event.event_type === "fielding_code_marker"
    ) {
      continue;
    }

    const previous =
      groups[groups.length - 1];

    const teamName =
      event.batting_team_name || null;

    if (
      previous &&
      previous.inning === event.inning &&
      previous.battingSide ===
        event.batting_side &&
      previous.battingTeamName === teamName
    ) {
      previous.events.push(event);
      continue;
    }

    groups.push({
      key: [
        event.inning,
        event.batting_side,
        teamName || "unknown",
        event.source_index,
      ].join("-"),
      inning: event.inning,
      battingSide: event.batting_side,
      battingTeamName: teamName,
      events: [event],
    });
  }

  const sideOrder: Record<string, number> = {
    away: 0,
    home: 1,
    unknown: 2,
  };

  return groups.sort(
    (left, right) =>
      left.inning - right.inning ||
      (sideOrder[left.battingSide] ?? 3) -
        (sideOrder[right.battingSide] ?? 3) ||
      left.events[0].source_index -
        right.events[0].source_index
  );
}


function formatHalfInning(
  inning: number,
  battingSide: string
): string {
  const ordinal = formatOrdinal(inning);

  if (battingSide === "away") {
    return `Top ${ordinal}`;
  }

  if (battingSide === "home") {
    return `Bottom ${ordinal}`;
  }

  return ordinal;
}


function formatOrdinal(
  value: number
): string {
  const remainder100 = value % 100;

  if (
    remainder100 >= 11 &&
    remainder100 <= 13
  ) {
    return `${value}th`;
  }

  switch (value % 10) {
    case 1:
      return `${value}st`;
    case 2:
      return `${value}nd`;
    case 3:
      return `${value}rd`;
    default:
      return `${value}th`;
  }
}


function eventLabel(
  eventType: string
): string {
  const labels: Record<string, string> = {
    home_run: "Home run",
    single: "Single",
    double: "Double",
    triple: "Triple",
    walk: "Walk",
    hit_by_pitch: "HBP",
    strikeout: "Strikeout",
    fly_out: "Fly out",
    ground_out: "Ground out",
    line_out: "Line out",
    pop_out: "Pop out",
    bunt_out: "Bunt out",
    double_play: "Double play",
    triple_play: "Triple play",
    sacrifice_fly: "Sac fly",
    sacrifice_bunt: "Sac bunt",
    fielders_choice: "Fielder's choice",
    reached_error: "Error",
    throwing_error: "Throwing error",
    stolen_base: "Stolen base",
    caught_stealing: "Caught stealing",
    picked_off: "Picked off",
    runner_scored: "Run scored",
    runner_advanced: "Advance",
    runner_out: "Runner out",
    balk: "Balk",
    pinch_hit: "Pinch hit",
    pinch_runner: "Pinch runner",
    substitution: "Substitution",
    pitcher_marker: "Pitching",
    bullpen_marker: "Bullpen",
  };

  if (labels[eventType]) {
    return labels[eventType];
  }

  return eventType
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase()
    );
}


function eventBadgeClass(
  eventType: string
): string {
  if (
    [
      "home_run",
      "runner_scored",
    ].includes(eventType)
  ) {
    return "bg-amber-500/15 text-amber-300";
  }

  if (
    [
      "single",
      "double",
      "triple",
    ].includes(eventType)
  ) {
    return "bg-emerald-500/15 text-emerald-300";
  }

  if (
    [
      "walk",
      "hit_by_pitch",
      "stolen_base",
      "runner_advanced",
    ].includes(eventType)
  ) {
    return "bg-blue-500/15 text-blue-300";
  }

  if (
    [
      "reached_error",
      "throwing_error",
      "fielders_choice",
    ].includes(eventType)
  ) {
    return "bg-violet-500/15 text-violet-300";
  }

  if (
    [
      "strikeout",
      "fly_out",
      "ground_out",
      "line_out",
      "pop_out",
      "bunt_out",
      "double_play",
      "triple_play",
      "sacrifice_fly",
      "sacrifice_bunt",
      "runner_out",
      "caught_stealing",
      "picked_off",
    ].includes(eventType)
  ) {
    return "bg-rose-500/10 text-rose-300";
  }

  return "bg-slate-800 text-slate-300";
}


function cleanMlbtsText(
  value: string
): string {
  return value
    .replace(/\^[a-z]\d*\^/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}


function RawDataSection({
  title,
  content,
}: {
  title: string;
  content: string | null;
}) {
  return (
    <details className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <summary className="cursor-pointer px-5 py-4 text-sm font-black uppercase tracking-[0.14em] text-slate-300 hover:text-white">
        {title}
      </summary>

      <div className="border-t border-slate-800 p-5">
        {content ? (
          <pre className="max-h-[40rem] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-800 bg-black p-4 font-mono text-xs leading-6 text-slate-300">
            {content}
          </pre>
        ) : (
          <div className="text-sm text-slate-500">
            No raw JSON is stored.
          </div>
        )}
      </div>
    </details>
  );
}


function ResultBadge({
  result,
}: {
  result: string | null;
}) {
  if (result === "W") {
    return <span className="result-win">WIN</span>;
  }

  if (result === "L") {
    return <span className="result-loss">LOSS</span>;
  }

  return <span className="result-na">N/A</span>;
}


function show(
  value: number | null | undefined
): number | string {
  return value ?? "-";
}


function prettyJson(
  value: string | null | undefined
): string | null {
  if (!value) {
    return null;
  }

  try {
    return JSON.stringify(
      JSON.parse(value),
      null,
      2
    );
  } catch {
    return value;
  }
}


function buildGameUrl(
  gameId: string,
  config: AppConfigResponse
): string {
  const params =
    new URLSearchParams({
      platform: config.platform,
      username: config.username,
    });

  return (
    `https://mlb26.theshow.com/` +
    `games/${gameId}?` +
    params.toString()
  );
}
