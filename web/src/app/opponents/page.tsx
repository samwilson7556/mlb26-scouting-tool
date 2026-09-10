import { AppShell } from "@/components/app-shell";
import { getOpponents } from "@/lib/api";
import { formatGameDateTime } from "@/lib/dates";

export default async function OpponentsPage() {
  const data = await getOpponents();

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Opponents</h1>
        <p className="mt-2 text-slate-400">
          Opponents from your local human-only game history.
        </p>
      </div>

      <div className="card">
        <div className="mb-4 text-sm text-slate-400">
          {data.total} known opponents
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-700 text-slate-400">
              <tr>
                <th className="py-2">Opponent</th>
                <th className="py-2">Team</th>
                <th className="py-2">Games</th>
                <th className="py-2">Your Record</th>
                <th className="py-2">Avg Runs For</th>
                <th className="py-2">Avg Runs Against</th>
                <th className="py-2">Last Played</th>
              </tr>
            </thead>

            <tbody>
              {data.opponents.map((opponent) => (
                <tr
                  key={`${opponent.opponent_name}-${opponent.opponent_team_name}`}
                  className="border-b border-slate-800"
                >
                  <td className="py-3 font-semibold">
                    {opponent.opponent_name}
                  </td>
                  <td className="py-3">{opponent.opponent_team_name}</td>
                  <td className="py-3">{opponent.games_played}</td>
                  <td className="py-3">
                    {opponent.your_wins}-{opponent.your_losses}
                  </td>
                  <td className="py-3">{opponent.avg_runs_scored ?? "N/A"}</td>
                  <td className="py-3">{opponent.avg_runs_allowed ?? "N/A"}</td>
                  <td className="py-3">{formatGameDateTime(opponent.last_played)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
