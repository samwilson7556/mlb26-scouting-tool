"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  AppConfigResponse,
  GameSummary,
  getAllGames,
  getAppConfig,
} from "@/lib/api";
import {
  formatGameDateTime,
  getGameDateSortValue,
} from "@/lib/dates";


type SortKey =
  | "display_date"
  | "opponent_name"
  | "user_result"
  | "home_full_name"
  | "away_full_name"
  | "score"
  | "hits"
  | "id";

type SortDirection = "asc" | "desc";

type PageSizeOption =
  | "all"
  | "10"
  | "25"
  | "50"
  | "100";


export default function GamesPage() {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [config, setConfig] =
    useState<AppConfigResponse | null>(null);

  const [total, setTotal] = useState(0);

  const [pageSize, setPageSize] =
    useState<PageSizeOption>("all");

  const [sortKey, setSortKey] =
    useState<SortKey>("display_date");

  const [sortDirection, setSortDirection] =
    useState<SortDirection>("desc");

  const [loading, setLoading] = useState(true);

  const [error, setError] =
    useState<string | null>(null);


  useEffect(() => {
    async function loadGames() {
      setLoading(true);
      setError(null);

      try {
        const [
          gamesResult,
          configResult,
        ] = await Promise.all([
          getAllGames(),
          getAppConfig(),
        ]);

        setGames(gamesResult.games);
        setTotal(gamesResult.total);
        setConfig(configResult);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load games."
        );
      } finally {
        setLoading(false);
      }
    }

    loadGames();
  }, []);


  const sortedGames = useMemo(() => {
    const sorted = [...games];

    sorted.sort((a, b) => {
      const aValue =
        getSortValue(a, sortKey);

      const bValue =
        getSortValue(b, sortKey);

      if (
        typeof aValue === "number"
        && typeof bValue === "number"
      ) {
        return sortDirection === "asc"
          ? aValue - bValue
          : bValue - aValue;
      }

      return sortDirection === "asc"
        ? String(aValue).localeCompare(
            String(bValue)
          )
        : String(bValue).localeCompare(
            String(aValue)
          );
    });

    return sorted;
  }, [
    games,
    sortKey,
    sortDirection,
  ]);


  const visibleGames = useMemo(() => {
    if (pageSize === "all") {
      return sortedGames;
    }

    return sortedGames.slice(
      0,
      Number(pageSize)
    );
  }, [
    sortedGames,
    pageSize,
  ]);


  function handleSort(
    nextSortKey: SortKey
  ) {
    if (nextSortKey === sortKey) {
      setSortDirection(
        (current) =>
          current === "asc"
            ? "desc"
            : "asc"
      );

      return;
    }

    setSortKey(nextSortKey);

    setSortDirection(
      nextSortKey === "display_date"
        ? "desc"
        : "asc"
    );
  }


  return (
    <AppShell>
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-3 inline-flex rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-300">
            Human-only online games
          </div>

          <h1 className="text-4xl font-black tracking-tight text-white">
            Games
          </h1>

          <p className="mt-3 max-w-2xl text-slate-400">
            Browse your filtered online
            game history, sort by any
            column, and open individual
            MLB The Show game pages.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-300">
          <span className="text-slate-500">
            Total loaded:
          </span>{" "}

          <span className="font-bold text-white">
            {games.length}
          </span>
        </div>
      </div>


      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-black shadow-2xl shadow-black/30">
        <div className="flex flex-col gap-4 border-b border-slate-800 bg-black px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-black uppercase tracking-wide text-white">
              Showing {visibleGames.length} of{" "}
              {total} games
            </div>

            <div className="mt-1 text-xs text-slate-500">
              MLB-style compact table.
              Click any column header to
              sort.
            </div>
          </div>

          <label className="flex items-center gap-3 text-sm text-slate-300">
            <span className="font-bold uppercase tracking-wide">
              Rows
            </span>

            <select
              className="rounded-md border border-slate-700 bg-black px-3 py-2 text-xs font-black uppercase tracking-wide text-white outline-none transition focus:border-blue-500"
              value={pageSize}
              onChange={(event) =>
                setPageSize(
                  event.target
                    .value as PageSizeOption
                )
              }
            >
              <option value="all">
                All
              </option>

              <option value="10">
                10
              </option>

              <option value="25">
                25
              </option>

              <option value="50">
                50
              </option>

              <option value="100">
                100
              </option>
            </select>
          </label>
        </div>


        {loading && (
          <div className="p-8 text-center text-sm text-slate-400">
            Loading games...
          </div>
        )}


        {error && (
          <div className="p-8 text-center text-sm text-red-400">
            {error}
          </div>
        )}


        {!loading && !error && (
          <div className="mlb-table-wrap">
            <table className="mlb-table min-w-[1050px]">
              <thead>
                <tr>
                  <SortableHeader
                    label="Date"
                    sortKey="display_date"
                    activeSortKey={sortKey}
                    direction={
                      sortDirection
                    }
                    onSort={handleSort}
                  />

                  <SortableHeader
                    label="Opponent"
                    sortKey="opponent_name"
                    activeSortKey={sortKey}
                    direction={
                      sortDirection
                    }
                    onSort={handleSort}
                  />

                  <SortableHeader
                    label="Result"
                    sortKey="user_result"
                    activeSortKey={sortKey}
                    direction={
                      sortDirection
                    }
                    onSort={handleSort}
                    align="center"
                  />

                  <SortableHeader
                    label="Home"
                    sortKey="home_full_name"
                    activeSortKey={sortKey}
                    direction={
                      sortDirection
                    }
                    onSort={handleSort}
                  />

                  <SortableHeader
                    label="Away"
                    sortKey="away_full_name"
                    activeSortKey={sortKey}
                    direction={
                      sortDirection
                    }
                    onSort={handleSort}
                  />

                  <SortableHeader
                    label="Score"
                    sortKey="score"
                    activeSortKey={sortKey}
                    direction={
                      sortDirection
                    }
                    onSort={handleSort}
                    align="right"
                    divider
                  />

                  <SortableHeader
                    label="Hits"
                    sortKey="hits"
                    activeSortKey={sortKey}
                    direction={
                      sortDirection
                    }
                    onSort={handleSort}
                    align="right"
                  />

                  <SortableHeader
                    label="Game ID"
                    sortKey="id"
                    activeSortKey={sortKey}
                    direction={
                      sortDirection
                    }
                    onSort={handleSort}
                    align="right"
                    divider
                  />
                </tr>
              </thead>

              <tbody>
                {visibleGames.map(
                  (game) => (
                    <tr key={game.id}>
                      <td className="whitespace-nowrap">
                        {formatGameDateTime(
                          game.display_date
                        )}
                      </td>

                      <td>
                        <OpponentCell
                          username={
                            game.opponent_name
                          }
                          team={
                            game.opponent_team_name
                          }
                        />
                      </td>

                      <td className="center">
                        <ResultBadge
                          result={
                            game.user_result
                          }
                        />
                      </td>

                      <td className="primary">
                        {
                          game.home_full_name
                        }
                      </td>

                      <td className="primary">
                        {
                          game.away_full_name
                        }
                      </td>

                      <td className="numeric divider-left primary">
                        {game.home_runs}-
                        {game.away_runs}
                      </td>

                      <td className="numeric">
                        {game.home_hits ?? "-"}-
                        {game.away_hits ?? "-"}
                      </td>

                      <td className="numeric divider-left font-mono text-xs">
                        {config ? (
                          <a
                            href={buildGameUrl(
                              game.id,
                              config
                            )}
                            target="_blank"
                            rel="noreferrer"
                            className="mlb-link"
                            title="Open game page in a new tab"
                          >
                            {game.id}
                          </a>
                        ) : (
                          game.id
                        )}
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>

            {visibleGames.length ===
              0 && (
              <div className="p-8 text-center text-sm text-slate-400">
                No games found.
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}


function SortableHeader({
  label,
  sortKey,
  activeSortKey,
  direction,
  onSort,
  align = "left",
  divider = false,
}: {
  label: string;
  sortKey: SortKey;
  activeSortKey: SortKey;
  direction: SortDirection;
  onSort: (
    sortKey: SortKey
  ) => void;
  align?:
    | "left"
    | "right"
    | "center";
  divider?: boolean;
}) {
  const isActive =
    sortKey === activeSortKey;

  const arrow = isActive
    ? direction === "asc"
      ? "▲"
      : "▼"
    : "↕";

  return (
    <th
      className={`${
        align === "right"
          ? "numeric"
          : ""
      } ${
        align === "center"
          ? "center"
          : ""
      } ${
        divider
          ? "divider-left"
          : ""
      }`}
    >
      <button
        type="button"
        onClick={() =>
          onSort(sortKey)
        }
        className={`mlb-sort-button ${
          isActive
            ? "mlb-sort-active"
            : ""
        }`}
      >
        <span>{label}</span>
        <span>{arrow}</span>
      </button>
    </th>
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


function getSortValue(
  game: GameSummary,
  sortKey: SortKey
): string | number {
  switch (sortKey) {
    case "display_date":
      return getGameDateSortValue(
        game.display_date
      );

    case "opponent_name":
      return (
        game.opponent_name || ""
      );

    case "user_result":
      return (
        game.user_result || ""
      );

    case "home_full_name":
      return (
        game.home_full_name || ""
      );

    case "away_full_name":
      return (
        game.away_full_name || ""
      );

    case "score":
      return (
        Number(
          game.home_runs || 0
        )
        + Number(
          game.away_runs || 0
        )
      );

    case "hits":
      return (
        Number(
          game.home_hits || 0
        )
        + Number(
          game.away_hits || 0
        )
      );

    case "id":
      return Number(
        game.id || 0
      );

    default:
      return "";
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