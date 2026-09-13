const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";


async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();

    throw new Error(
      `API request failed: ${response.status} ${text}`
    );
  }

  return response.json() as Promise<T>;
}


export type AppConfigResponse = {
  username: string;
  platform: string;
  mode: string;
};


export type DashboardResponse = {
  total_games: number;
  total_game_logs: number;
  successful_game_logs: number;
  record: {
    wins: number;
    losses: number;
    win_pct: number | null;
  };
  averages: {
    runs_scored: number | null;
    runs_allowed: number | null;
  };
  recent_games: GameSummary[];
};


export type AnalyticsTrendGame = {
  game_id: string;
  display_date: string | null;
  opponent_name: string | null;
  opponent_team_name: string | null;
  user_side: "home" | "away";
  user_walks: number;
  user_strikeouts: number;
  opponent_walks: number;
  opponent_strikeouts: number;
};


export type AnalyticsInningRow = {
  inning: number;
  games_reaching_inning: number;
  user_innings_observed: number;
  opponent_innings_observed: number;
  user_runs: number;
  opponent_runs: number;
  user_runs_per_observed_inning: number | null;
  opponent_runs_per_observed_inning: number | null;
  run_diff_per_observed_inning: number | null;
};


export type AnalyticsInningsResponse = {
  limit: number;
  games_included: number;
  innings: AnalyticsInningRow[];
};


export type AnalyticsTrendsResponse = {
  limit: number;
  plate_discipline: {
    games_included: number;
    summary: {
      user_walks: number;
      user_strikeouts: number;
      opponent_walks: number;
      opponent_strikeouts: number;
      user_walks_per_game: number | null;
      user_strikeouts_per_game: number | null;
      opponent_walks_per_game: number | null;
      opponent_strikeouts_per_game: number | null;
    };
    games: AnalyticsTrendGame[];
  };
  inning_scoring: {
    games_included: number;
    innings: AnalyticsInningRow[];
  };
};


export type AnalyticsTendencyItem = {
  value: string;
  count: number;
  pct: number | null;
};


export type AnalyticsStrikeoutTendencies = {
  with_finishing_pitch: number;
  with_location: number;
  with_style: number;
  finishing_pitches: AnalyticsTendencyItem[];
  locations: AnalyticsTendencyItem[];
  styles: AnalyticsTendencyItem[];
};


export type AnalyticsPlayerRow = {
  player_name: string;
  team_name: string;
  opponent_name?: string | null;
  games: number;
  plate_appearances: number;
  at_bats: number;
  hits: number;
  singles: number;
  doubles: number;
  triples: number;
  home_runs: number;
  walks: number;
  intentional_walks: number;
  hit_by_pitch: number;
  strikeouts: number;
  sacrifice_flies: number;
  sacrifice_bunts: number;
  double_plays: number;
  triple_plays: number;
  runs: number;
  stolen_bases: number;
  caught_stealing: number;
  picked_off: number;
  batting_average: number | null;
  walk_pct: number | null;
  strikeout_pct: number | null;
  home_run_pct: number | null;
  strikeout_tendencies: AnalyticsStrikeoutTendencies;
};


export type AnalyticsPlayersResponse = {
  limit: number;
  games_included: number;
  user_players: AnalyticsPlayerRow[];
  opponent_players: AnalyticsPlayerRow[];
};


export type GameSummary = {
  id: string;
  display_date: string | null;
  game_mode?: string;
  home_full_name: string;
  away_full_name: string;
  home_name?: string;
  away_name?: string;
  home_runs: number;
  away_runs: number;
  home_hits?: number;
  away_hits?: number;
  home_errors?: number;
  away_errors?: number;
  user_result: string | null;
  opponent_name: string | null;
  opponent_team_name: string | null;
};


export type GamesResponse = {
  total: number;
  limit: number;
  offset: number;
  games: GameSummary[];
};


export type GameLogRecord = {
  game_id: string;
  fetched_at: string | null;
  api_status: string | null;
  raw_game_log_json: string | null;
  raw_text_log: string | null;
};


export type GameInning = {
  id: number;
  game_id: string;
  inning: number;
  home_runs: number | null;
  away_runs: number | null;
};


export type GameEvent = {
  id: number;
  game_id: string;
  source_index: number;
  inning: number;
  batting_side: string;
  batting_team_name: string | null;
  event_type: string;
  player_name: string | null;
  related_player_name: string | null;
  raw_text: string;
  is_plate_appearance: number;
  is_hit: number;
  is_out: number;
  hit_bases: number | null;
  outs_recorded: number | null;
  fielding_code: string | null;
  destination_base: string | null;
  cause: string | null;
  strikeout_type: string | null;
  home_run_distance_ft: number | null;
  terminal_pitch_type: string | null;
  terminal_pitch_location: string | null;
  secondary_out: number;
  parser_version: number;
};


export type TeamBoxScore = {
  id: number;
  game_id: string;
  team_id: string | null;
  team_name: string | null;
  runs: number | null;
  hits: number | null;
  errors: number | null;
  batting_ab: number | null;
  batting_r: number | null;
  batting_h: number | null;
  batting_rbi: number | null;
  batting_bb: number | null;
  batting_so: number | null;
  pitching_ip: number | null;
  pitching_outs: number | null;
  pitching_h: number | null;
  pitching_r: number | null;
  pitching_er: number | null;
  pitching_bb: number | null;
  pitching_so: number | null;
};


export type PlayerBattingStat = {
  id: number;
  game_id: string;
  team_id: string | null;
  team_name: string | null;
  player_name: string | null;
  ab: number | null;
  r: number | null;
  h: number | null;
  rbi: number | null;
  bb: number | null;
  so: number | null;
  doubles: number | null;
  triples: number | null;
  hr: number | null;
  sb: number | null;
  cs: number | null;
};


export type PlayerPitchingStat = {
  id: number;
  game_id: string;
  team_id: string | null;
  team_name: string | null;
  player_name: string | null;
  ip: number | null;
  pitching_outs: number | null;
  h: number | null;
  r: number | null;
  er: number | null;
  bb: number | null;
  so: number | null;
  win: number | null;
  loss: number | null;
  save: number | null;
};


export type GameDetailResponse = {
  game: GameSummary & {
    raw_game_history_json?: string | null;
  };
  game_log: GameLogRecord | null;
  team_box_scores: TeamBoxScore[];
  batting_stats: PlayerBattingStat[];
  pitching_stats: PlayerPitchingStat[];
  innings: GameInning[];
  events: GameEvent[];
};


export type OpponentSummary = {
  opponent_name: string;
  opponent_team_name: string | null;
  games_played: number;
  your_wins: number;
  your_losses: number;
  last_played: string | null;
  avg_runs_scored: number | null;
  avg_runs_allowed: number | null;
};


export type OpponentsResponse = {
  total: number;
  opponents: OpponentSummary[];
};


export type LocalOpponentResponse = {
  opponent: string;
  found: boolean;
  message?: string;
  games_played?: number;
  your_record?: string;
  avg_runs_scored?: number;
  avg_runs_allowed?: number;
  last_played?: string;
  games?: GameSummary[];
};


export type GameLogSyncSummary = {
  requested: number;
  ok: number;
  identity_mismatch: number;
  not_found: number;
  api_error: number;
  request_failed: number;
  preserved_ok: number;
};


export type SyncType =
  | "history"
  | "logs"
  | "all";


export type SyncJob = {
  id: string;
  type: SyncType;
  status:
    | "queued"
    | "running"
    | "completed"
    | "failed";
  phase:
    | "queued"
    | "history"
    | "logs"
    | "complete";
  message: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  human_games: number | null;
  progress_current: number;
  progress_total: number;
  current_game_id: string | null;
  log_summary: GameLogSyncSummary | null;
  error: string | null;
};


export type SyncJobEnvelope = {
  job: SyncJob | null;
};


export type SyncHistoryResponse = {
  status: string;
  message: string;
  human_games: number;
};


export type SyncLogsResponse = {
  status: string;
  message: string;
  summary: GameLogSyncSummary;
};


export type SyncAllResponse = {
  status: string;
  message: string;
  human_games: number;
  log_summary: GameLogSyncSummary;
};


export type LiveHitterProfile = Omit<
  AnalyticsPlayerRow,
  "team_name" | "opponent_name"
>;


export type LiveScoutResponse = {
  username: string;
  platform: string;
  mode: string;
  pages_fetched: number;
  games_found_total: number;
  non_cpu_games_found: number;
  human_games_found: number;
  cpu_games_removed: number;
  skipped_unattributable_games: number;
  recent_games_analyzed: number;

  record: {
    wins: number;
    losses: number;
    unknown_results: number;
    win_pct: number | null;
  };

  averages_from_game_history: {
    runs_scored_per_game: number | null;
    runs_allowed_per_game: number | null;
    hits_for_per_game: number | null;
    hits_allowed_per_game: number | null;
    errors_per_game: number | null;
  };

  advanced_from_game_logs: {
    logs_requested: boolean;
    logs_fetched: number;
    logs_failed: number;
    batting_ab: number;
    batting_h: number;
    pitching_outs: number;
    pitching_ip: string;
    pitching_er: number;
    batting_average: number | null;
    era: number | null;
    worker_count: number;
    game_log_platform: string;
    hitter_profiles: {
      games_included: number;
      players: LiveHitterProfile[];
    };
  };

  games: Array<{
    id: string;
    display_date: string;
    result: string | null;
    runs_for: number | null;
    runs_against: number | null;
    hits_for: number | null;
    hits_against: number | null;
    errors_for: number | null;
    opponent_name: string;
    opponent_team: string;
  }>;
};


export async function getAppConfig(): Promise<AppConfigResponse> {
  return apiFetch<AppConfigResponse>("/config");
}


export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>("/dashboard");
}


export async function getAnalyticsTrends(
  limit = 20
): Promise<AnalyticsTrendsResponse> {
  const searchParams = new URLSearchParams({
    limit: String(limit),
  });

  return apiFetch<AnalyticsTrendsResponse>(
    `/analytics/trends?${searchParams.toString()}`
  );
}


export async function getAnalyticsInnings(
  limit = 20,
  opponent?: string
): Promise<AnalyticsInningsResponse> {
  const searchParams = new URLSearchParams({
    limit: String(limit),
  });

  const normalizedOpponent =
    opponent?.trim();

  if (normalizedOpponent) {
    searchParams.set(
      "opponent",
      normalizedOpponent
    );
  }

  return apiFetch<AnalyticsInningsResponse>(
    `/analytics/innings?${searchParams.toString()}`
  );
}


export async function getAnalyticsPlayers(
  limit = 20,
  opponent?: string
): Promise<AnalyticsPlayersResponse> {
  const searchParams = new URLSearchParams({
    limit: String(limit),
  });

  const normalizedOpponent =
    opponent?.trim();

  if (normalizedOpponent) {
    searchParams.set(
      "opponent",
      normalizedOpponent
    );
  }

  return apiFetch<AnalyticsPlayersResponse>(
    `/analytics/players?${searchParams.toString()}`
  );
}


export async function getGames(params?: {
  limit?: number;
  offset?: number;
  opponent?: string;
  result?: string;
}): Promise<GamesResponse> {
  const searchParams = new URLSearchParams();

  if (params?.limit !== undefined) {
    searchParams.set(
      "limit",
      String(params.limit)
    );
  }

  if (params?.offset !== undefined) {
    searchParams.set(
      "offset",
      String(params.offset)
    );
  }

  if (params?.opponent) {
    searchParams.set(
      "opponent",
      params.opponent
    );
  }

  if (params?.result) {
    searchParams.set(
      "result",
      params.result
    );
  }

  const query = searchParams.toString();

  return apiFetch<GamesResponse>(
    `/games${query ? `?${query}` : ""}`
  );
}


export async function getGameDetail(
  gameId: string
): Promise<GameDetailResponse> {
  return apiFetch<GameDetailResponse>(
    `/games/${encodeURIComponent(gameId)}`
  );
}


export async function getAllGames(params?: {
  opponent?: string;
  result?: string;
}): Promise<GamesResponse> {
  const pageSize = 500;

  const firstPage = await getGames({
    limit: pageSize,
    offset: 0,
    opponent: params?.opponent,
    result: params?.result,
  });

  const allGames = [...firstPage.games];

  let offset = allGames.length;

  while (offset < firstPage.total) {
    const page = await getGames({
      limit: pageSize,
      offset,
      opponent: params?.opponent,
      result: params?.result,
    });

    if (page.games.length === 0) {
      break;
    }

    allGames.push(...page.games);

    offset += page.games.length;
  }

  return {
    total: firstPage.total,
    limit: allGames.length,
    offset: 0,
    games: allGames,
  };
}


export async function getOpponents(): Promise<OpponentsResponse> {
  return apiFetch<OpponentsResponse>(
    "/opponents"
  );
}


export async function getLocalOpponent(
  username: string
): Promise<LocalOpponentResponse> {
  return apiFetch<LocalOpponentResponse>(
    `/opponents/${encodeURIComponent(username)}`
  );
}


export async function startSyncJob(
  type: SyncType
): Promise<SyncJob> {
  return apiFetch<SyncJob>(
    "/sync/jobs",
    {
      method: "POST",
      body: JSON.stringify({ type }),
    }
  );
}


export async function getSyncJob(
  jobId: string
): Promise<SyncJob> {
  return apiFetch<SyncJob>(
    `/sync/jobs/${encodeURIComponent(jobId)}`
  );
}


export async function getLatestSyncJob(
): Promise<SyncJobEnvelope> {
  return apiFetch<SyncJobEnvelope>(
    "/sync/jobs/latest"
  );
}


export async function syncHistory(): Promise<SyncHistoryResponse> {
  return apiFetch<SyncHistoryResponse>(
    "/sync/history",
    {
      method: "POST",
    }
  );
}


export async function syncLogs(): Promise<SyncLogsResponse> {
  return apiFetch<SyncLogsResponse>(
    "/sync/logs",
    {
      method: "POST",
    }
  );
}


export async function syncAll(): Promise<SyncAllResponse> {
  return apiFetch<SyncAllResponse>(
    "/sync/all",
    {
      method: "POST",
    }
  );
}


export async function liveScout(payload: {
  username: string;
  platform: string;
  pages: number;
  max_games: number;
  include_logs: boolean;
  log_workers: number;
}): Promise<LiveScoutResponse> {
  return apiFetch<LiveScoutResponse>(
    "/live-scout",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}