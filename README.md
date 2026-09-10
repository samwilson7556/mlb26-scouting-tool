# MLB The Show 26 Game History & Scouting Tool

A local Python + SQLite + FastAPI + Next.js tool for collecting, filtering, storing, and analyzing MLB The Show 26 online game history and game logs.

The project pulls game history from the MLB The Show 26 API, removes games played against the CPU, stores only human-vs-human online games, fetches full game logs, provides local opponent scouting, supports live opponent scouting by username, and includes a browser-based user interface.

---

## Current Scope

This README reflects the project after the following features were added:

- Python collector
- SQLite database
- CPU-game filtering
- Individual game-log retrieval
- Automatic web-page priming for missing game logs
- Local opponent scouting
- Live opponent scouting
- Concurrent game-log fetching for faster live scouting
- FastAPI backend
- Next.js + TypeScript + Tailwind frontend
- Sync controls in the UI
- Git/GitHub-ready project structure

---

## Included Features

### Data Collection

- Fetch paginated game history from MLB The Show 26
- Read `total_pages` from the API response and request each page
- Combine game history results
- Remove games played against CPU
- Store only human-vs-human online games
- Export filtered human-only game history as JSON
- Store game history in SQLite

### Game Log Retrieval

- Fetch individual game logs by game ID
- Automatically prime missing game logs by visiting the web game page
- Retry game-log API requests after priming
- Store raw game-log JSON files locally
- Store raw game-log JSON in SQLite
- Parse box score data into structured SQLite tables

### Scouting

- View known opponents from your local game history
- Scout opponents you have already played
- Run live scouting by entering a username
- Fetch live game history for another player
- Remove that player's CPU games
- Calculate recent record, runs/game, hits/game, and errors/game
- Optionally include game logs for batting average and ERA estimates
- Use concurrent game-log workers to speed up live scouting

### Web UI

- Dashboard page
- Games page
- Opponents page
- Scout page
- Sync page
- Local scouting from the browser
- Live scouting from the browser
- Configurable live-scout pages, max games, and game-log workers

---

## Not Yet Included

These are good candidates for future work:

- Deep play-by-play parsing
- Pitching tendency analysis
- Hitting tendency analysis
- Strikeout/walk trend analysis
- Perfect-perfect hit tracking
- Inning-by-inning scoring trends
- Player-card level trends
- Advanced charts
- Authentication
- Deployment as a hosted web app
- Background jobs for sync operations
- Persistent live-scout caching

---

## Project Purpose

The goal of this tool is to help analyze MLB The Show 26 online performance and build a foundation for player-improvement insights.

The tool collects online game history, filters out CPU games, downloads detailed logs for each real-player match, and stores everything in a structured format so you can later analyze:

- Win/loss trends
- Opponent history
- Runs scored and allowed
- Batting performance
- Pitching performance
- Player-specific box score data
- Common opponents
- Games where you struggled
- Games where you performed well
- Opponent scouting before a matchup

---

## API Endpoints Used

### Game History API

```text
https://mlb26.theshow.com/apis/game_history.json?page={page}&username={username}&platform={platform}&mode=arena
```

Example:

```text
https://mlb26.theshow.com/apis/game_history.json?page=1&username=poopoopee155&platform=psn&mode=arena
```

The response includes:

- `page`
- `per_page`
- `total_pages`
- `game_history`

Each game in `game_history` includes fields such as:

```json
{
  "id": "887003117",
  "game_mode": "ARENA",
  "home_full_name": "Hoosiers",
  "away_full_name": "Red Strikers",
  "home_display_result": "L",
  "away_display_result": "W",
  "home_runs": "0",
  "away_runs": "2",
  "home_hits": "2",
  "away_hits": "5",
  "home_errors": "1",
  "away_errors": "0",
  "home_name": "poopoopee155 ^b53^",
  "away_name": "Dbmotter15 ^b54^",
  "display_date": "05/27/2026 20:29:02"
}
```

### Game Log API

```text
https://mlb26.theshow.com/apis/game_log.json?id={id}
```

Example:

```text
https://mlb26.theshow.com/apis/game_log.json?id=887003117
```

The response can include:

- `line_score`
- `game_log`
- `box_score`

Some game IDs may initially return:

```json
{
  "error": "game not found"
}
```

When that happens, the tool visits the web page version first:

```text
https://mlb26.theshow.com/games/{id}?platform=psn&username=poopoopee155
```

Then it retries the API request.

This "prime then retry" behavior is built into both local game-log sync and live scouting with game logs.

---

## CPU Game Filtering Rule

Games are removed if either team is listed as `CPU`.

A game is considered a CPU game when:

```text
home_full_name == "CPU"
```

or:

```text
away_full_name == "CPU"
```

Only games where both sides are human-controlled are stored or analyzed.

---

## Live Scouting Attribution Rule

Live scouting applies a second filter after CPU games are removed.

A game is only included in a live scout report if the searched username can be identified as either:

```text
home_name
```

or:

```text
away_name
```

This prevents rows with blank values for:

- Result
- Opponent
- Score
- Hits

The report also tracks:

```text
skipped_unattributable_games
```

This value represents non-CPU games that were skipped because the searched username could not be confidently matched to either side of the game.

---

## Recommended Project Structure

```text
mlb26-scouting-tool/
├── data/
│   ├── raw_game_logs/
│   ├── exports/
│   └── mlb26_games.sqlite3
├── src/
│   ├── __init__.py
│   ├── api.py
│   ├── collector.py
│   ├── config.py
│   ├── database.py
│   ├── live_scout.py
│   ├── main.py
│   ├── parser.py
│   └── scout.py
├── web/
│   ├── src/
│   │   ├── app/
│   │   │   ├── games/
│   │   │   ├── opponents/
│   │   │   ├── scout/
│   │   │   ├── sync/
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   └── app-shell.tsx
│   │   └── lib/
│   │       └── api.ts
│   ├── .env.example
│   ├── package.json
│   └── ...
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Requirements

### Backend

- Python 3.11 or newer
- Internet access
- SQLite, included with Python

Python packages:

```text
requests
rich
fastapi
uvicorn[standard]
pydantic
```

### Frontend

- Node.js
- npm
- Next.js
- TypeScript
- Tailwind CSS

---

## Setup Instructions

### 1. Create the Python virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

### 2. Install backend dependencies

Create or update `requirements.txt`:

```txt
requests
rich
fastapi
uvicorn[standard]
pydantic
```

Install:

```bash
pip install -r requirements.txt
```

### 3. Configure the frontend environment

Create:

```text
web/.env.local
```

Add:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

An example file can also be committed as:

```text
web/.env.example
```

with:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Configuration

Project settings are stored in:

```text
src/config.py
```

Example configuration:

```python
from pathlib import Path

USERNAME = "poopoopee155"
PLATFORM = "psn"
MODE = "arena"

BASE_URL = "https://mlb26.theshow.com"

GAME_HISTORY_URL = f"{BASE_URL}/apis/game_history.json"
GAME_LOG_URL = f"{BASE_URL}/apis/game_log.json"

GAME_WEB_URL_TEMPLATE = (
    f"{BASE_URL}/games/{{game_id}}?platform={PLATFORM}&username={USERNAME}"
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_GAME_LOG_DIR = DATA_DIR / "raw_game_logs"
EXPORT_DIR = DATA_DIR / "exports"

DB_PATH = DATA_DIR / "mlb26_games.sqlite3"

REQUEST_DELAY_SECONDS = 0.75
RETRY_DELAY_SECONDS = 2.0
```

Update these values as needed:

```python
USERNAME = "poopoopee155"
PLATFORM = "psn"
MODE = "arena"
```

Common platform values may include:

```text
psn
xbl
mlbts
nsw
```

---

## Database Design

The project uses SQLite.

Database file:

```text
data/mlb26_games.sqlite3
```

### `games`

Stores filtered human-only game history.

```text
id
display_date
game_mode
home_full_name
away_full_name
home_name
away_name
home_runs
away_runs
home_hits
away_hits
home_errors
away_errors
user_result
opponent_name
opponent_team_name
raw_game_history_json
```

### `game_logs`

Stores full raw game-log API responses and text logs.

```text
game_id
fetched_at
api_status
raw_game_log_json
raw_text_log
```

### `team_box_scores`

Stores parsed team-level box score data.

```text
game_id
team_id
team_name
runs
hits
errors
batting_ab
batting_r
batting_h
batting_rbi
batting_bb
batting_so
pitching_ip
pitching_h
pitching_r
pitching_er
pitching_bb
pitching_so
```

### `player_batting_stats`

Stores parsed player batting stats.

```text
game_id
team_id
team_name
player_name
ab
r
h
rbi
bb
so
doubles
triples
hr
sb
cs
```

### `player_pitching_stats`

Stores parsed player pitching stats.

```text
game_id
team_id
team_name
player_name
ip
h
r
er
bb
so
win
loss
save
```

---

## Backend CLI Commands

All commands should be run from the project root.

Because this project uses package-style imports, use:

```bash
python -m src.main <command>
```

### Initialize the database

```bash
python -m src.main init
```

### Sync game history only

```bash
python -m src.main sync-history
```

This command requests all game-history pages, removes CPU games, stores human-only games in SQLite, and exports filtered game history to:

```text
data/exports/human_only_game_history.json
```

### Sync game logs only

```bash
python -m src.main sync-logs
```

This command fetches individual game logs for stored human-only games, primes missing logs when needed, and parses box score data.

### Sync everything

```bash
python -m src.main sync-all
```

### View known opponents

```bash
python -m src.main opponents
```

### Scout a local opponent

```bash
python -m src.main scout --username Dbmotter15
```

### Live scout an opponent

```bash
python -m src.main live-scout --username DCBeenNice --platform psn
```

### Live scout with game logs

```bash
python -m src.main live-scout --username DCBeenNice --platform psn --include-logs
```

### Live scout with concurrent game-log workers

```bash
python -m src.main live-scout --username DCBeenNice --platform psn --include-logs --log-workers 5
```

`--log-workers` controls how many game logs are fetched/primed concurrently.

Recommended values:

```text
5   safe starting point
8   faster, usually still reasonable
10  upper limit currently allowed by the API model
```

### Limit pages and max games

```bash
python -m src.main live-scout --username DCBeenNice --platform psn --pages 2 --max-games 25
```

### Export opponent summary

```bash
python -m src.main export-opponents
```

Output file:

```text
data/exports/opponent_summary.json
```

---

## FastAPI Backend

The backend API is defined in:

```text
src/api.py
```

Start the backend from the project root:

```bash
uvicorn src.api:app --reload --port 8000
```

Health check:

```text
http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

FastAPI docs:

```text
http://localhost:8000/docs
```

---

## Backend API Routes

### `GET /health`

Returns backend status.

### `GET /dashboard`

Returns total human games, total game logs, record, averages, and recent games.

### `GET /games`

Query parameters:

```text
limit
offset
opponent
result
```

Example:

```text
http://localhost:8000/games?limit=100
```

### `GET /games/{game_id}`

Returns game detail, game log, team box scores, batting stats, and pitching stats.

### `GET /opponents`

Returns locally known opponents.

### `GET /opponents/{username}`

Returns local scouting information for an opponent you have already played.

### `POST /sync/history`

Runs game-history sync.

### `POST /sync/logs`

Runs game-log sync.

### `POST /sync/all`

Runs game-history sync and game-log sync.

### `POST /live-scout`

Request body:

```json
{
  "username": "DCBeenNice",
  "platform": "psn",
  "pages": 1,
  "max_games": 25,
  "include_logs": true,
  "log_workers": 5
}
```

Returns a live scout report including recent record, win percentage, run averages, hit averages, CPU games removed, skipped unattributable games, recent games, and optional advanced stats from game logs.

---

## Frontend UI

The frontend is located in:

```text
web/
```

Start the frontend in a second terminal:

```bash
cd web
npm run dev
```

Open:

```text
http://localhost:3000
```

---

## Running the Full App

Use two terminals.

### Terminal 1 — backend

```bash
uvicorn src.api:app --reload --port 8000
```

### Terminal 2 — frontend

```bash
cd web
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

## UI Pages

### Dashboard

```text
/
```

Shows total human games, total game logs, record, runs/game, and recent games.

### Games

```text
/games
```

Shows human-only online game history.

### Opponents

```text
/opponents
```

Shows opponents from the local database.

### Scout

```text
/scout
```

Supports local scout, live scout, platform selection, page count, max games, include game logs, and game-log worker count.

### Sync

```text
/sync
```

Supports Sync History, Sync Logs, and Sync All.

---

## Live Scouting Performance

Originally, live scouting with game logs processed game IDs serially:

```text
game 1 → prime → retry → parse
game 2 → prime → retry → parse
game 3 → prime → retry → parse
```

This was slow because each missing game log could spend 10–30 seconds priming the web page.

The current implementation uses concurrent workers:

```text
game 1 ┐
game 2 ├── concurrent workers
game 3 ┤
game 4 ┘
```

The worker count is configurable in:

- CLI: `--log-workers`
- API: `log_workers`
- UI: `Game Log Workers`

Recommended starting value:

```text
5
```

---

## Expected Output Files

After running a full sync, you should have:

```text
data/
├── mlb26_games.sqlite3
├── raw_game_logs/
│   ├── 887003117.json
│   ├── 887685664.json
│   └── ...
└── exports/
    ├── human_only_game_history.json
    ├── opponent_summary.json
    └── live_scout_<username>_<timestamp>.json
```

---

## Useful SQL Queries

Database path:

```text
data/mlb26_games.sqlite3
```

### Count stored games

```sql
SELECT COUNT(*) FROM games;
```

### Count fetched game logs

```sql
SELECT COUNT(*) FROM game_logs;
```

### View most recent games

```sql
SELECT
    display_date,
    opponent_name,
    user_result,
    home_full_name,
    away_full_name,
    home_runs,
    away_runs
FROM games
ORDER BY display_date DESC
LIMIT 10;
```

### Record by opponent

```sql
SELECT
    opponent_name,
    COUNT(*) AS games,
    SUM(CASE WHEN user_result = 'W' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN user_result = 'L' THEN 1 ELSE 0 END) AS losses
FROM games
GROUP BY opponent_name
ORDER BY games DESC;
```

### Average runs scored and allowed

```sql
SELECT
    AVG(
        CASE
            WHEN home_name = 'poopoopee155' THEN home_runs
            WHEN away_name = 'poopoopee155' THEN away_runs
        END
    ) AS avg_runs_scored,
    AVG(
        CASE
            WHEN home_name = 'poopoopee155' THEN away_runs
            WHEN away_name = 'poopoopee155' THEN home_runs
        END
    ) AS avg_runs_allowed
FROM games;
```

---

## GitHub / Repository Notes

Recommended `.gitignore` entries:

```gitignore
# Python
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Environment files
.env
.env.*
!.env.example
web/.env.local
web/.env.*.local

# Local data/database/log exports
data/mlb26_games.sqlite3
data/*.sqlite3
data/raw_game_logs/
data/exports/
*.db
*.sqlite
*.sqlite3

# Node / Next.js
web/node_modules/
web/.next/
web/out/
web/dist/
web/.turbo/

# OS/editor
.DS_Store
Thumbs.db
.vscode/
.idea/
```

Push to GitHub:

```bash
git init
git remote add origin https://github.com/samwilson7556/mlb26-scouting-tool.git
git add .
git commit -m "Initial commit for MLB26 scouting tool"
git branch -M main
git push -u origin main
```

If the remote already exists:

```bash
git remote set-url origin https://github.com/samwilson7556/mlb26-scouting-tool.git
```

---

## Troubleshooting

### PowerShell cannot activate the virtual environment

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

### `ModuleNotFoundError`

Run commands from the project root with:

```bash
python -m src.main sync-all
```

Do not run:

```bash
python src/main.py
```

### Backend cannot import packages

Make sure your virtual environment is active and dependencies are installed:

```bash
pip install -r requirements.txt
```

### Frontend cannot reach backend

Confirm the backend is running:

```bash
uvicorn src.api:app --reload --port 8000
```

Confirm this URL works:

```text
http://localhost:8000/health
```

Confirm `web/.env.local` contains:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Restart the frontend after changing `.env.local`.

### Game logs still return `game not found`

The tool already tries to prime the web page first.

If some still fail, possible reasons include:

- The site needs more time to generate the game log
- The game is no longer available
- The game ID is invalid
- The site temporarily blocked or throttled the request

### Live Scout shows blank rows

This was addressed by filtering out unattributable games.

If blanks still appear, check:

- The searched username spelling
- The selected platform
- Whether the API returns decorated or unexpected username values
- Whether the returned game belongs to a linked account name rather than the searched username

The report includes:

```text
skipped_unattributable_games
```

to help diagnose this.

### Include Game Logs is slow

Use concurrent game-log workers.

Recommended UI settings:

```text
Pages: 1
Max Games: 25
Include game logs: checked
Game Log Workers: 5
```

Try increasing to:

```text
8
```

Avoid going above:

```text
10
```

unless you intentionally modify the backend validation and are comfortable testing rate limits.

### CPU games are still appearing

Confirm the API response uses exactly:

```text
CPU
```

in either:

```text
home_full_name
away_full_name
```

The filtering logic checks both fields case-insensitively.

### Usernames have suffixes like `^b53^`

The MLB The Show API may return usernames like:

```text
poopoopee155 ^b53^
```

The parser strips those suffixes and stores:

```text
poopoopee155
```

---

## Development Order

Recommended build order:

```text
1. Create project folder
2. Create Python virtual environment
3. Install backend dependencies
4. Add config.py
5. Add database.py
6. Add parser.py
7. Add collector.py
8. Add scout.py
9. Add live_scout.py
10. Add main.py
11. Run init
12. Run sync-history
13. Confirm human_only_game_history.json looks correct
14. Run sync-logs
15. Confirm raw_game_logs are created
16. Open SQLite database and inspect tables
17. Run opponents
18. Run scout --username SomeOpponent
19. Run live-scout --username SomeOpponent
20. Add api.py
21. Start FastAPI backend
22. Create Next.js frontend
23. Add API helper
24. Add AppShell
25. Add Dashboard, Games, Opponents, Scout, and Sync pages
26. Run backend and frontend together
27. Add .gitignore
28. Push to GitHub
```

---

## Current Limitations

- Live scouting depends on public MLB The Show API behavior.
- Some game logs may still fail even after priming.
- Batting average and ERA require game-log fetching.
- Live game-log fetching can still take time if many logs require priming.
- Advanced play-by-play analysis is not yet implemented.
- Sync operations currently run inline through the API and UI.
- Large sync operations may make the UI wait until the backend request finishes.
- No background job queue is currently implemented.
- No authentication is currently implemented.
- No production deployment configuration is currently included.

---

## Next Planned Improvements

Potential next steps:

- Add background sync jobs
- Add progress status for sync and live scout operations
- Cache live scout reports
- Store live scout reports in SQLite
- Add game detail page in the frontend
- Add charts for runs scored and runs allowed over time
- Add opponent-specific trend pages
- Parse play-by-play text for tendencies
- Add pitch-count and strikeout tendency analysis
- Add batting/pitching split views
- Add README screenshots
- Add automated setup script

---

## License

Personal-use project.

Use responsibly and avoid excessive API requests.
