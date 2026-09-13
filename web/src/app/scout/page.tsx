"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { formatGameDateTime } from "@/lib/dates";
import {
  AnalyticsInningsResponse,
  AnalyticsPlayersResponse,
  AnalyticsTendencyItem,
  getAnalyticsInnings,
  getAnalyticsPlayers,
  getAppConfig,
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

  const [localReport, setLocalReport] =
    useState<LocalOpponentResponse | null>(null);

  const [liveReport, setLiveReport] =
    useState<LiveScoutResponse | null>(null);

  const [
    opponentPlayerReport,
    setOpponentPlayerReport,
  ] = useState<AnalyticsPlayersResponse | null>(
    null
  );

  const [
    opponentInningReport,
    setOpponentInningReport,
  ] = useState<AnalyticsInningsResponse | null>(
    null
  );

  const [error, setError] =
    useState<string | null>(null);


  useEffect(() => {
    async function loadDefaultConfig() {
      try {
        const config = await getAppConfig();

        if (config.platform) {
          setPlatform(config.platform);
        }
      } catch {
        // Keep the normal PSN fallback if the API
        // is not yet available when the page loads.
      }
    }

    loadDefaultConfig();
  }, []);


  async function runLocalScout() {
    const trimmedUsername =
      username.trim();

    if (!trimmedUsername) {
      return;
    }

    setLoading(true);
    setError(null);
    setLocalReport(null);
    setLiveReport(null);
    setOpponentPlayerReport(null);
    setOpponentInningReport(null);

    try {
      const result =
        await getLocalOpponent(
          trimmedUsername
        );

      setLocalReport(result);

      if (result.found) {
        const [
          playerResult,
          inningResult,
        ] = await Promise.all([
          getAnalyticsPlayers(
            200,
            trimmedUsername
          ),
          getAnalyticsInnings(
            200,
            trimmedUsername
          ),
        ]);

        setOpponentPlayerReport(
          playerResult
        );

        setOpponentInningReport(
          inningResult
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unknown error"
      );
    } finally {
      setLoading(false);
    }
  }


  async function runLiveScout() {
    const trimmedUsername =
      username.trim();

    if (!trimmedUsername) {
      return;
    }

    setLoading(true);
    setError(null);
    setLocalReport(null);
    setLiveReport(null);
    setOpponentPlayerReport(null);
    setOpponentInningReport(null);

    try {
      const result = await liveScout({
        username: trimmedUsername,
        platform,
        pages,
        max_games: maxGames,
        include_logs: includeLogs,
        log_workers: logWorkers,
      });

      setLiveReport(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unknown error"
      );
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

        <h1 className="text-4xl font-black tracking-tight text-white">
          Scout
        </h1>

        <p className="mt-3 max-w-2xl text-slate-400">
          Look up local opponent history
          or run live scouting directly
          from MLB The Show.
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
            onChange={(event) =>
              setUsername(
                event.target.value
              )
            }
            placeholder="Opponent username"
          />


          <label className="mt-4 block text-sm font-semibold text-slate-300">
            Platform
          </label>

          <select
            className="input mt-2"
            value={platform}
            onChange={(event) =>
              setPlatform(
                event.target.value
              )
            }
          >
            <option value="psn">
              PSN
            </option>

            <option value="xbl">
              Xbox
            </option>

            <option value="mlbts">
              MLB The Show
            </option>

            <option value="nsw">
              Nintendo Switch
            </option>
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
            onChange={(event) =>
              setPages(
                Number(
                  event.target.value
                )
              )
            }
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
            onChange={(event) =>
              setMaxGames(
                Number(
                  event.target.value
                )
              )
            }
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
            disabled={!includeLogs}
            onChange={(event) =>
              setLogWorkers(
                Number(
                  event.target.value
                )
              )
            }
          />

          <p className="mt-2 text-xs leading-relaxed text-slate-500">
            Used only when game logs are
            included. Five workers is the
            normal default; lower this if
            you want more conservative API
            request concurrency.
          </p>


          <label className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-300">
            <input
              type="checkbox"
              checked={includeLogs}
              onChange={(event) =>
                setIncludeLogs(
                  event.target.checked
                )
              }
            />

            Include game logs
          </label>


          <div className="mt-6 grid gap-3">
            <button
              className="button-secondary"
              disabled={
                !username.trim()
                || loading
              }
              onClick={runLocalScout}
            >
              {loading
                ? "Working..."
                : "Local Scout"}
            </button>

            <button
              className="button"
              disabled={
                !username.trim()
                || !platform
                || loading
              }
              onClick={runLiveScout}
            >
              {loading
                ? "Working..."
                : "Live Scout"}
            </button>
          </div>
        </div>


        <div className="space-y-5 lg:col-span-3">
          {loading && (
            <div className="card text-sm text-slate-300">
              Running scout report. If
              game logs are included,
              additional MLB The Show API
              requests are required, so
              the report may take a little
              longer.
            </div>
          )}


          {error && (
            <div className="card text-red-400">
              {error}
            </div>
          )}


          {localReport && (
            <div className="space-y-5">
              <div className="card">
                <h2 className="text-xl font-bold text-white">
                  Local Scout Report
                </h2>

                {!localReport.found ? (
                  <p className="mt-4 text-yellow-400">
                    {localReport.message}
                  </p>
                ) : (
                  <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    <Stat
                      label="Opponent"
                      value={
                        localReport.opponent
                      }
                    />

                    <Stat
                      label="Games"
                      value={
                        localReport.games_played
                      }
                    />

                    <Stat
                      label="Record"
                      value={
                        localReport.your_record
                      }
                    />

                    <Stat
                      label="Avg Runs For"
                      value={
                        localReport.avg_runs_scored
                      }
                    />

                    <Stat
                      label="Avg Runs Allowed"
                      value={
                        localReport.avg_runs_allowed
                      }
                    />

                    <Stat
                      label="Last Played"
                      value={
                        localReport.last_played
                      }
                    />
                  </div>
                )}
              </div>

              {localReport.found
                && opponentInningReport && (
                <div className="card">
                  <div>
                    <h2 className="text-xl font-bold text-white">
                      Scoring by Inning
                    </h2>

                    <p className="mt-1 text-sm text-slate-500">
                      {
                        opponentInningReport
                          .games_included
                      }{" "}
                      {opponentInningReport.games_included === 1
                        ? "game"
                        : "games"}{" "}
                      with inning scoring
                      available
                      {opponentInningReport.games_included > 1
                        ? "; values are averages per observed inning."
                        : "."}
                    </p>
                  </div>

                  {opponentInningReport
                    .innings.length === 0 ? (
                    <div className="mt-6 rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-500">
                      No inning scoring data
                      is available for this
                      opponent yet.
                    </div>
                  ) : (
                    <div className="mlb-table-wrap mt-5">
                      <table className="mlb-table min-w-[620px]">
                        <thead>
                          <tr>
                            <th>Inning</th>

                            <th className="numeric">
                              You
                            </th>

                            <th className="numeric">
                              Opponent
                            </th>

                            <th className="numeric divider-left">
                              Diff
                            </th>

                            <th className="numeric">
                              Games
                            </th>
                          </tr>
                        </thead>

                        <tbody>
                          {opponentInningReport
                            .innings
                            .map((inning) => {
                              const diff =
                                inning
                                  .run_diff_per_observed_inning;

                              const diffClass =
                                diff === null
                                  ? "text-slate-500"
                                  : diff > 0
                                    ? "text-emerald-400"
                                    : diff < 0
                                      ? "text-red-400"
                                      : "text-slate-300";

                              return (
                                <tr
                                  key={
                                    inning.inning
                                  }
                                >
                                  <td className="primary">
                                    {
                                      inning
                                        .inning
                                    }
                                  </td>

                                  <td className="numeric">
                                    {formatRunValue(
                                      inning
                                        .user_runs_per_observed_inning
                                    )}
                                  </td>

                                  <td className="numeric">
                                    {formatRunValue(
                                      inning
                                        .opponent_runs_per_observed_inning
                                    )}
                                  </td>

                                  <td
                                    className={
                                      `numeric divider-left font-bold ${diffClass}`
                                    }
                                  >
                                    {formatRunDiff(
                                      diff
                                    )}
                                  </td>

                                  <td className="numeric">
                                    {
                                      inning
                                        .games_reaching_inning
                                    }
                                  </td>
                                </tr>
                              );
                            })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {localReport.found
                && opponentPlayerReport && (
                <div className="card">
                  <div>
                    <h2 className="text-xl font-bold text-white">
                      Opponent hitters
                    </h2>

                    <p className="mt-1 text-sm text-slate-500">
                      {
                        opponentPlayerReport
                          .games_included
                      }{" "}
                      {opponentPlayerReport.games_included === 1
                        ? "game"
                        : "games"}{" "}
                      with normalized
                      play-by-play
                    </p>
                  </div>

                  {opponentPlayerReport
                    .opponent_players
                    .length === 0 ? (
                    <div className="mt-6 rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-500">
                      No normalized hitter
                      data is available for
                      this opponent yet.
                    </div>
                  ) : (
                    <div className="mlb-table-wrap mt-5">
                      <table className="mlb-table min-w-[1120px]">
                        <thead>
                          <tr>
                            <th>Player</th>
                            <th className="numeric">
                              G
                            </th>
                            <th className="numeric">
                              PA
                            </th>
                            <th className="numeric">
                              AB
                            </th>
                            <th className="numeric divider-left">
                              H
                            </th>
                            <th className="numeric">
                              2B
                            </th>
                            <th className="numeric">
                              3B
                            </th>
                            <th className="numeric">
                              HR
                            </th>
                            <th className="numeric divider-left">
                              AVG
                            </th>
                            <th className="numeric">
                              BB
                            </th>
                            <th className="numeric">
                              K
                            </th>
                            <th className="numeric divider-left">
                              BB%
                            </th>
                            <th className="numeric">
                              K%
                            </th>
                            <th className="numeric">
                              HR%
                            </th>
                          </tr>
                        </thead>

                        <tbody>
                          {opponentPlayerReport
                            .opponent_players
                            .map((player) => (
                            <tr
                              key={
                                player
                                  .player_name
                                  .toLowerCase()
                              }
                            >
                              <td className="primary">
                                {
                                  player
                                    .player_name
                                }
                              </td>

                              <td className="numeric">
                                {player.games}
                              </td>

                              <td className="numeric">
                                {
                                  player
                                    .plate_appearances
                                }
                              </td>

                              <td className="numeric">
                                {player.at_bats}
                              </td>

                              <td className="numeric divider-left">
                                {player.hits}
                              </td>

                              <td className="numeric">
                                {player.doubles}
                              </td>

                              <td className="numeric">
                                {player.triples}
                              </td>

                              <td className="numeric">
                                {
                                  player
                                    .home_runs
                                }
                              </td>

                              <td className="numeric divider-left">
                                {formatAverage(
                                  player
                                    .batting_average
                                )}
                              </td>

                              <td className="numeric">
                                {player.walks}
                              </td>

                              <td className="numeric">
                                {
                                  player
                                    .strikeouts
                                }
                              </td>

                              <td className="numeric divider-left">
                                {formatPercent(
                                  player.walk_pct
                                )}
                              </td>

                              <td className="numeric">
                                {formatPercent(
                                  player
                                    .strikeout_pct
                                )}
                              </td>

                              <td className="numeric">
                                {formatPercent(
                                  player
                                    .home_run_pct
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {opponentPlayerReport
                    .opponent_players
                    .some(
                      (player) =>
                        player.strikeouts > 0
                    ) && (
                    <div className="mt-6 border-t border-slate-800 pt-5">
                      <div>
                        <h3 className="text-base font-bold text-white">
                          Strikeout Profiles
                        </h3>

                        <p className="mt-1 text-sm text-slate-500">
                          Recorded finishing
                          pitch, location, and
                          strikeout style.
                        </p>
                      </div>

                      <div className="mt-4 grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
                        {opponentPlayerReport
                          .opponent_players
                          .filter(
                            (player) =>
                              player.strikeouts
                              > 0
                          )
                          .map((player) => (
                          <div
                            key={
                              `strikeout-${player.player_name.toLowerCase()}`
                            }
                            className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
                          >
                            <div className="flex items-center justify-between gap-4">
                              <div className="font-bold text-white">
                                {
                                  player
                                    .player_name
                                }
                              </div>

                              <div className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs font-bold text-slate-300">
                                {
                                  player
                                    .strikeouts
                                }{" "}
                                {player.strikeouts === 1
                                  ? "K"
                                  : "Ks"}
                              </div>
                            </div>

                            <div className="mt-4 space-y-2 text-sm">
                              <div className="grid grid-cols-[52px_1fr] gap-3">
                                <span className="font-semibold text-slate-500">
                                  Pitch
                                </span>

                                <span className="text-slate-300">
                                  {formatStrikeoutTendency(
                                    player
                                      .strikeout_tendencies
                                      .finishing_pitches,
                                    player
                                      .strikeout_tendencies
                                      .with_finishing_pitch
                                  )}
                                </span>
                              </div>

                              <div className="grid grid-cols-[52px_1fr] gap-3">
                                <span className="font-semibold text-slate-500">
                                  Zone
                                </span>

                                <span className="text-slate-300">
                                  {formatStrikeoutTendency(
                                    player
                                      .strikeout_tendencies
                                      .locations,
                                    player
                                      .strikeout_tendencies
                                      .with_location
                                  )}
                                </span>
                              </div>

                              <div className="grid grid-cols-[52px_1fr] gap-3">
                                <span className="font-semibold text-slate-500">
                                  Style
                                </span>

                                <span className="text-slate-300">
                                  {formatStrikeoutTendency(
                                    player
                                      .strikeout_tendencies
                                      .styles,
                                    player
                                      .strikeout_tendencies
                                      .with_style
                                  )}
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
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
                        Live Scout Report:{" "}
                        {liveReport.username}
                      </h2>

                      <p className="mt-2 text-sm text-slate-400">
                        Requested:{" "}
                        <span className="font-bold text-white">
                          {
                            liveReport.platform
                          }
                        </span>{" "}
                        <span className="text-slate-700">
                          |
                        </span>{" "}
                        History:{" "}
                        <span className="font-bold text-white">
                          {
                            liveReport
                              .history_platform
                          }
                        </span>{" "}
                        <span className="text-slate-700">
                          |
                        </span>{" "}
                        Game Logs:{" "}
                        <span className="font-bold text-white">
                          {liveReport
                            .advanced_from_game_logs
                            .logs_requested
                            ? liveReport
                                .advanced_from_game_logs
                                .game_log_platform
                            : "Not requested"}
                        </span>{" "}
                        <span className="text-slate-700">
                          |
                        </span>{" "}
                        Mode:{" "}
                        <span className="font-bold text-white">
                          {liveReport.mode}
                        </span>
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <MiniStat
                        label="Games"
                        value={
                          liveReport.recent_games_analyzed
                        }
                      />

                      <MiniStat
                        label="Record"
                        value={
                          `${liveReport.record.wins}-`
                          + `${liveReport.record.losses}`
                        }
                      />

                      <MiniStat
                        label="Win%"
                        value={
                          liveReport.record.win_pct
                        }
                      />

                      <MiniStat
                        label="Logs"
                        value={
                          `${liveReport.advanced_from_game_logs.logs_fetched}/`
                          + `${liveReport.advanced_from_game_logs.logs_failed}`
                        }
                      />
                    </div>
                  </div>
                </div>


                <div className="grid gap-0 xl:grid-cols-3">
                  <ReportSection title="Performance">
                    <LargeMetric
                      label="Recent Record"
                      value={
                        `${liveReport.record.wins}-`
                        + `${liveReport.record.losses}`
                      }
                    />

                    <LargeMetric
                      label="Win%"
                      value={
                        liveReport.record.win_pct
                      }
                    />
                  </ReportSection>


                  <ReportSection title="Offense">
                    <LargeMetric
                      label="Runs/Game"
                      value={
                        liveReport
                          .averages_from_game_history
                          .runs_scored_per_game
                      }
                    />

                    <LargeMetric
                      label="Hits/Game"
                      value={
                        liveReport
                          .averages_from_game_history
                          .hits_for_per_game
                      }
                    />

                    <LargeMetric
                      label="Batting Avg"
                      value={
                        liveReport
                          .advanced_from_game_logs
                          .batting_average
                        ?? "Use logs"
                      }
                    />
                  </ReportSection>


                  <ReportSection title="Run Prevention">
                    <LargeMetric
                      label="Runs Allowed/Game"
                      value={
                        liveReport
                          .averages_from_game_history
                          .runs_allowed_per_game
                      }
                    />

                    <LargeMetric
                      label="Hits Allowed/Game"
                      value={
                        liveReport
                          .averages_from_game_history
                          .hits_allowed_per_game
                      }
                    />

                    <LargeMetric
                      label="Pitching IP"
                      value={
                        liveReport
                          .advanced_from_game_logs
                          .logs_requested
                          ? liveReport
                              .advanced_from_game_logs
                              .pitching_ip
                          : "Use logs"
                      }
                    />

                    <LargeMetric
                      label="ERA"
                      value={
                        liveReport
                          .advanced_from_game_logs
                          .era
                        ?? "Use logs"
                      }
                    />
                  </ReportSection>
                </div>


                <div className="grid border-t border-slate-800 bg-slate-950/70 md:grid-cols-2 xl:grid-cols-4">
                  <InfoMetric
                    label="Human Games Found"
                    value={
                      liveReport.human_games_found
                    }
                  />

                  <InfoMetric
                    label="CPU Games Removed"
                    value={
                      liveReport.cpu_games_removed
                    }
                  />

                  <InfoMetric
                    label="Skipped Unattributable"
                    value={
                      liveReport.skipped_unattributable_games
                    }
                  />

                  <InfoMetric
                    label="Game Log Workers"
                    value={
                      liveReport
                        .advanced_from_game_logs
                        .worker_count
                    }
                  />
                </div>
              </div>


              {liveReport
                .advanced_from_game_logs
                .logs_requested && (
                <div className="card">
                  <div>
                    <h2 className="text-xl font-bold text-white">
                      Live Hitter Profiles
                    </h2>

                    <p className="mt-1 text-sm text-slate-500">
                      {
                        liveReport
                          .advanced_from_game_logs
                          .hitter_profiles
                          .games_included
                      }{" "}
                      {liveReport
                        .advanced_from_game_logs
                        .hitter_profiles
                        .games_included === 1
                        ? "game"
                        : "games"}{" "}
                      with normalized
                      play-by-play
                      {" "}
                      <span className="text-slate-600">
                        •
                      </span>{" "}
                      game-log platform:{" "}
                      <span className="font-semibold text-slate-400">
                        {
                          liveReport
                            .advanced_from_game_logs
                            .game_log_platform
                        }
                      </span>
                    </p>
                  </div>

                  {liveReport
                    .advanced_from_game_logs
                    .hitter_profiles
                    .players.length === 0 ? (
                    <div className="mt-6 rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-500">
                      No normalized hitter
                      data was available from
                      the fetched game logs.
                    </div>
                  ) : (
                    <div className="mlb-table-wrap mt-5">
                      <table className="mlb-table min-w-[1120px]">
                        <thead>
                          <tr>
                            <th>Player</th>

                            <th className="numeric">
                              G
                            </th>

                            <th className="numeric">
                              PA
                            </th>

                            <th className="numeric">
                              AB
                            </th>

                            <th className="numeric divider-left">
                              H
                            </th>

                            <th className="numeric">
                              2B
                            </th>

                            <th className="numeric">
                              3B
                            </th>

                            <th className="numeric">
                              HR
                            </th>

                            <th className="numeric divider-left">
                              AVG
                            </th>

                            <th className="numeric">
                              BB
                            </th>

                            <th className="numeric">
                              K
                            </th>

                            <th className="numeric divider-left">
                              BB%
                            </th>

                            <th className="numeric">
                              K%
                            </th>

                            <th className="numeric">
                              HR%
                            </th>
                          </tr>
                        </thead>

                        <tbody>
                          {liveReport
                            .advanced_from_game_logs
                            .hitter_profiles
                            .players
                            .map((player) => (
                            <tr
                              key={
                                player
                                  .player_name
                                  .toLowerCase()
                              }
                            >
                              <td className="primary">
                                {
                                  player
                                    .player_name
                                }
                              </td>

                              <td className="numeric">
                                {player.games}
                              </td>

                              <td className="numeric">
                                {
                                  player
                                    .plate_appearances
                                }
                              </td>

                              <td className="numeric">
                                {player.at_bats}
                              </td>

                              <td className="numeric divider-left">
                                {player.hits}
                              </td>

                              <td className="numeric">
                                {player.doubles}
                              </td>

                              <td className="numeric">
                                {player.triples}
                              </td>

                              <td className="numeric">
                                {
                                  player
                                    .home_runs
                                }
                              </td>

                              <td className="numeric divider-left">
                                {formatAverage(
                                  player
                                    .batting_average
                                )}
                              </td>

                              <td className="numeric">
                                {player.walks}
                              </td>

                              <td className="numeric">
                                {
                                  player
                                    .strikeouts
                                }
                              </td>

                              <td className="numeric divider-left">
                                {formatPercent(
                                  player.walk_pct
                                )}
                              </td>

                              <td className="numeric">
                                {formatPercent(
                                  player
                                    .strikeout_pct
                                )}
                              </td>

                              <td className="numeric">
                                {formatPercent(
                                  player
                                    .home_run_pct
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {liveReport
                    .advanced_from_game_logs
                    .hitter_profiles
                    .players.some(
                      (player) =>
                        player.strikeouts > 0
                    ) && (
                    <div className="mt-6 border-t border-slate-800 pt-5">
                      <div>
                        <h3 className="text-base font-bold text-white">
                          Strikeout Profiles
                        </h3>

                        <p className="mt-1 text-sm text-slate-500">
                          Recorded finishing
                          pitch, location, and
                          strikeout style from
                          the fetched live
                          game logs.
                        </p>
                      </div>

                      <div className="mt-4 grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
                        {liveReport
                          .advanced_from_game_logs
                          .hitter_profiles
                          .players
                          .filter(
                            (player) =>
                              player.strikeouts
                              > 0
                          )
                          .map((player) => (
                          <div
                            key={
                              `live-strikeout-${player.player_name.toLowerCase()}`
                            }
                            className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
                          >
                            <div className="flex items-center justify-between gap-4">
                              <div className="font-bold text-white">
                                {
                                  player
                                    .player_name
                                }
                              </div>

                              <div className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs font-bold text-slate-300">
                                {
                                  player
                                    .strikeouts
                                }{" "}
                                {player.strikeouts === 1
                                  ? "K"
                                  : "Ks"}
                              </div>
                            </div>

                            <div className="mt-4 space-y-2 text-sm">
                              <div className="grid grid-cols-[52px_1fr] gap-3">
                                <span className="font-semibold text-slate-500">
                                  Pitch
                                </span>

                                <span className="text-slate-300">
                                  {formatStrikeoutTendency(
                                    player
                                      .strikeout_tendencies
                                      .finishing_pitches,
                                    player
                                      .strikeout_tendencies
                                      .with_finishing_pitch
                                  )}
                                </span>
                              </div>

                              <div className="grid grid-cols-[52px_1fr] gap-3">
                                <span className="font-semibold text-slate-500">
                                  Zone
                                </span>

                                <span className="text-slate-300">
                                  {formatStrikeoutTendency(
                                    player
                                      .strikeout_tendencies
                                      .locations,
                                    player
                                      .strikeout_tendencies
                                      .with_location
                                  )}
                                </span>
                              </div>

                              <div className="grid grid-cols-[52px_1fr] gap-3">
                                <span className="font-semibold text-slate-500">
                                  Style
                                </span>

                                <span className="text-slate-300">
                                  {formatStrikeoutTendency(
                                    player
                                      .strikeout_tendencies
                                      .styles,
                                    player
                                      .strikeout_tendencies
                                      .with_style
                                  )}
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}


              <div className="overflow-hidden rounded-2xl border border-slate-800 bg-black shadow-2xl shadow-black/30">
                <div className="border-b border-slate-800 bg-black px-5 py-4">
                  <h3 className="text-sm font-black uppercase tracking-wide text-white">
                    Recent Games
                  </h3>

                  <p className="mt-1 text-xs text-slate-500">
                    Game IDs open the MLB
                    The Show game page in a
                    new tab.
                  </p>
                </div>


                <div className="mlb-table-wrap">
                  <table className="mlb-table min-w-[920px]">
                    <thead>
                      <tr>
                        <th>
                          Date
                        </th>

                        <th className="center">
                          Result
                        </th>

                        <th>
                          Opponent
                        </th>

                        <th className="numeric divider-left">
                          Score
                        </th>

                        <th className="numeric">
                          Hits
                        </th>

                        <th className="numeric divider-left">
                          Game ID
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {liveReport.games.map(
                        (game) => (
                          <tr key={game.id}>
                            <td className="whitespace-nowrap">
                              {formatGameDateTime(
                                game.display_date
                              )}
                            </td>

                            <td className="center">
                              <ResultBadge
                                result={
                                  game.result
                                }
                              />
                            </td>

                            <td>
                              <OpponentCell
                                username={
                                  game.opponent_name
                                }
                                team={
                                  game.opponent_team
                                }
                              />
                            </td>

                            <td className="numeric divider-left primary">
                              {game.runs_for}-
                              {game.runs_against}
                            </td>

                            <td className="numeric">
                              {game.hits_for}-
                              {game.hits_against}
                            </td>

                            <td className="numeric divider-left font-mono text-xs">
                              <a
                                href={
                                  buildLiveGameUrl(
                                    game.id,
                                    liveReport.platform,
                                    liveReport.username
                                  )
                                }
                                target="_blank"
                                rel="noreferrer"
                                className="mlb-link"
                                title="Open game page in a new tab"
                              >
                                {game.id}
                              </a>
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>

                  {liveReport.games.length ===
                    0 && (
                    <div className="p-8 text-center text-sm text-slate-400">
                      No recent games
                      found.
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

      <div className="grid gap-4">
        {children}
      </div>
    </section>
  );
}


function LargeMetric({
  label,
  value,
}: {
  label: string;
  value:
    | string
    | number
    | null
    | undefined;
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
  value:
    | string
    | number
    | null
    | undefined;
}) {
  return (
    <div className="rounded-xl bg-slate-950 px-4 py-3 text-center">
      <div className="text-[10px] font-black uppercase tracking-wide text-slate-500">
        {label}
      </div>

      <div className="mt-1 text-lg font-black text-white">
        {value ?? "N/A"}
      </div>
    </div>
  );
}


function InfoMetric({
  label,
  value,
}: {
  label: string;
  value:
    | string
    | number
    | null
    | undefined;
}) {
  return (
    <div className="border-b border-slate-800 px-6 py-4 md:border-r xl:border-b-0">
      <div className="text-[11px] font-black uppercase tracking-wide text-slate-500">
        {label}
      </div>

      <div className="mt-1 text-xl font-black text-white">
        {value ?? "N/A"}
      </div>
    </div>
  );
}


function Stat({
  label,
  value,
}: {
  label: string;
  value:
    | string
    | number
    | null
    | undefined;
}) {
  return (
    <div
      className="rounded-2xl bg-slate-950/70 p-4 shadow-sm"
      style={{
        border: "none",
        outline: "none",
        boxShadow:
          "inset 0 1px 0 rgba(255,255,255,0.03)",
      }}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>

      <div className="mt-2 text-2xl font-black text-white">
        {value ?? "N/A"}
      </div>
    </div>
  );
}


function OpponentCell({
  username,
  team,
}: {
  username:
    | string
    | null
    | undefined;
  team:
    | string
    | null
    | undefined;
}) {
  return (
    <div className="min-w-[12rem]">
      <div className="primary leading-tight">
        {username || "Unknown"}
      </div>

      <div className="secondary mt-1 leading-tight">
        {team || "Unknown team"}
      </div>
    </div>
  );
}


function ResultBadge({
  result,
}: {
  result: string | null;
}) {
  if (result === "W") {
    return (
      <span className="result-win">
        WIN
      </span>
    );
  }

  if (result === "L") {
    return (
      <span className="result-loss">
        LOSS
      </span>
    );
  }

  return (
    <span className="result-na">
      N/A
    </span>
  );
}


function formatAverage(
  value: number | null
): string {
  if (value === null) {
    return "N/A";
  }

  return value
    .toFixed(3)
    .replace(/^0/, "");
}


function formatPercent(
  value: number | null
): string {
  return value === null
    ? "N/A"
    : `${value.toFixed(1)}%`;
}


function formatRunValue(
  value: number | null
): string {
  if (value === null) {
    return "N/A";
  }

  if (Number.isInteger(value)) {
    return String(value);
  }

  return value
    .toFixed(2)
    .replace(/0+$/, "")
    .replace(/\.$/, "");
}


function formatRunDiff(
  value: number | null
): string {
  if (value === null) {
    return "N/A";
  }

  const formatted =
    formatRunValue(value);

  return value > 0
    ? `+${formatted}`
    : formatted;
}


function formatTendencyValue(
  value: string
): string {
  return value
    .split("_")
    .map((part) => (
      part.length === 0
        ? part
        : (
          part.charAt(0).toUpperCase()
          + part.slice(1)
        )
    ))
    .join(" ");
}


function formatStrikeoutTendency(
  items: AnalyticsTendencyItem[],
  knownCount: number
): string {
  if (
    knownCount <= 0
    || items.length === 0
  ) {
    return "N/A";
  }

  return items
    .slice(0, 2)
    .map((item) => (
      `${formatTendencyValue(item.value)} `
      + `${item.count}/${knownCount}`
    ))
    .join(" · ");
}


function buildLiveGameUrl(
  gameId: string,
  platform: string,
  username: string
): string {
  const params =
    new URLSearchParams({
      platform,
      username,
    });

  return (
    `https://mlb26.theshow.com/`
    + `games/${gameId}?`
    + params.toString()
  );
}