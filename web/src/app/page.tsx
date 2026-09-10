import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { getDashboard } from "@/lib/api";
import { formatGameDateTime } from "@/lib/dates";

export default async function DashboardPage() {
  const dashboard = await getDashboard();

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="mt-2 text-slate-400">
          Local MLB The Show 26 game history and scouting summary.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="card">
          <div className="text-sm text-slate-400">Human Games</div>
          <div className="mt-2 text-3xl font-bold">{dashboard.total_games}</div>
        </div>

        <div className="card">
          <div className="text-sm text-slate-400">Game Logs</div>
          <div className="mt-2 text-3xl font-bold">
            {dashboard.total_game_logs}
          </div>
        </div>

        <div className="card">
          <div className="text-sm text-slate-400">Record</div>
          <div className="mt-2 text-3xl font-bold">
            {dashboard.record.wins}-{dashboard.record.losses}
          </div>
          <div className="mt-1 text-sm text-slate-400">
            Win%: {dashboard.record.win_pct ?? "N/A"}
          </div>
        </div>

        <div className="card">
          <div className="text-sm text-slate-400">Runs / Game</div>
          <div className="mt-2 text-3xl font-bold">
            {dashboard.averages.runs_scored ?? "N/A"}
          </div>
          <div className="mt-1 text-sm text-slate-400">
            Allowed: {dashboard.averages.runs_allowed ?? "N/A"}
          </div>
        </div>
      </div>

      <div className="mt-8 card">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold">Recent Games</h2>
          <Link href="/games" className="text-sm text-blue-400 hover:underline">
            View all
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-700 text-slate-400">
              <tr>
                <th className="py-2">Date</th>
                <th className="py-2">Opponent</th>
                <th className="py-2">Result</th>
                <th className="py-2">Matchup</th>
                <th className="py-2">Score</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.recent_games.map((game) => (
                <tr key={game.id} className="border-b border-slate-800">
                  <td className="py-3">{formatGameDateTime(game.display_date)}</td>
                  <td className="py-3">{game.opponent_name}</td>
                  <td className="py-3 font-bold">{game.user_result}</td>
                  <td className="py-3">
                    {game.home_full_name} vs {game.away_full_name}
                  </td>
                  <td className="py-3">
                    {game.home_runs}-{game.away_runs}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}