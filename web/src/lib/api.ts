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
    throw new Error(`API request failed: ${response.status} ${text}`);
  }

  return response.json() as Promise<T>;
}

export type DashboardResponse = {
  total_games: number;
  total_game_logs: number;
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
    pitching_ip: number;
    pitching_er: number;
    batting_average: number | null;
    era: number | null;
    worker_count: number;
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

export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>("/dashboard");
}

export async function getGames(params?: {
  limit?: number;
  offset?: number;
  opponent?: string;
  result?: string;
}): Promise<GamesResponse> {
  const searchParams = new URLSearchParams();

  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.opponent) searchParams.set("opponent", params.opponent);
  if (params?.result) searchParams.set("result", params.result);

  const query = searchParams.toString();
  return apiFetch<GamesResponse>(`/games${query ? `?${query}` : ""}`);
}

export async function getOpponents(): Promise<OpponentsResponse> {
  return apiFetch<OpponentsResponse>("/opponents");
}

export async function getLocalOpponent(
  username: string
): Promise<LocalOpponentResponse> {
  return apiFetch<LocalOpponentResponse>(
    `/opponents/${encodeURIComponent(username)}`
  );
}

export async function syncHistory(): Promise<{ status: string; message: string }> {
  return apiFetch("/sync/history", {
    method: "POST",
  });
}

export async function syncLogs(): Promise<{ status: string; message: string }> {
  return apiFetch("/sync/logs", {
    method: "POST",
  });
}

export async function syncAll(): Promise<{ status: string; message: string }> {
  return apiFetch("/sync/all", {
    method: "POST",
  });
}

export async function liveScout(payload: {
  username: string;
  platform: string;
  pages: number;
  max_games: number;
  include_logs: boolean;
  log_workers: number;
}): Promise<LiveScoutResponse> {
  return apiFetch<LiveScoutResponse>("/live-scout", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}