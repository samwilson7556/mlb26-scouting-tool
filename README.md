# MLB The Show 26 Game History & Scouting Tool

A local Python, SQLite, FastAPI, and Next.js application for collecting, storing, browsing, and analyzing MLB The Show 26 online game data.

The project is designed around human-vs-human game history. It retrieves MLB The Show game-history records, filters CPU games, stores game and box-score data locally, supports opponent scouting, and provides a browser-based frontend.

---

## Current Features

### Data Collection

- Fetch paginated MLB The Show 26 game history
- Automatically read the API-reported page count
- Filter CPU games
- Store human-vs-human games in SQLite
- Export human-only game history
- Fetch individual game logs
- Store raw game-log responses
- Parse team and player box-score statistics
- Preserve previously successful game logs if the MLBTS API later returns an error

### Scouting

- Browse known opponents
- Review previous games against a specific opponent
- Run live scouting against another MLBTS username
- Calculate recent:
  - record
  - win percentage
  - runs scored
  - runs allowed
  - hits
  - errors
- Optionally retrieve game logs for:
  - batting average
  - pitching innings
  - ERA

### Web Application

The Next.js frontend includes:

- Dashboard
- Games
- Opponents
- Scout
- Sync

The Games page loads the complete local game set rather than being limited to a single 500-row API response.

The frontend reads the configured MLBTS identity from the backend rather than duplicating the username and platform in TypeScript.

### Automated Testing

The repository includes automated tests for:

- CPU filtering
- username cleanup
- user-side attribution
- opponent attribution
- baseball innings-pitched conversion
- ERA calculation
- SQLite schema migration
- game-log response classification
- game-log retry behavior
- successful-log preservation
- parsed box-score replacement

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

The current automated suite contains 53 tests.

---

## Project Structure

```text
mlb26-scouting-tool/
├── data/
│   ├── exports/
│   ├── raw_game_logs/
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
├── tests/
│   ├── test_database_collector.py
│   └── test_parser.py
├── web/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   ├── .env.example
│   ├── package.json
│   └── package-lock.json
├── .gitignore
├── README.md
└── requirements.txt
```

Local database files, raw game logs, exports, Python virtual environments, Node dependencies, Next.js build output, and local environment files are excluded from Git.

---

## Requirements

### Backend

- Python 3.11 or newer
- SQLite
- Internet access for MLBTS API operations

Python dependencies are defined in:

```text
requirements.txt
```

Current packages:

```text
requests
rich
fastapi
uvicorn[standard]
pydantic
python-dotenv
```

### Frontend

- Node.js
- npm

The frontend currently uses:

- Next.js
- React
- TypeScript
- Tailwind CSS

---

## Backend Setup

From the project root, create and activate a virtual environment.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Create your local backend configuration:

```bash
cp .env.example .env
```

Then edit `.env` and replace `your_username` with your MLB The Show username. The `.env` file is ignored by Git and must not be committed.

Initialize the local database:

```bash
python -m src.main init
```

---

## Backend Configuration

Application configuration is centralized in:

```text
src/config.py
```

The following environment variables are supported:

```text
MLBTS_USERNAME
MLBTS_PLATFORM
MLBTS_MODE
MLBTS_BASE_URL
MLBTS_REQUEST_DELAY_SECONDS
```

`MLBTS_USERNAME` is required and has no hardcoded fallback. Local development loads it from the repository-root `.env` file via `python-dotenv`. Other configuration values retain safe defaults in `src/config.py`.

Example `.env`:

```text
MLBTS_USERNAME=your_username
MLBTS_PLATFORM=psn
MLBTS_MODE=arena
MLBTS_BASE_URL=https://mlb26.theshow.com
MLBTS_REQUEST_DELAY_SECONDS=0.75
```

Real environment variables take precedence over values loaded from `.env`.

Common platform values used by MLB The Show include:

```text
psn
xbl
mlbts
nsw
```

The backend configuration is also exposed to the local frontend through:

```text
GET /config
```

This keeps the configured username, platform, and game mode in one place.

---

## MLB The Show APIs

The collector currently uses two MLB The Show 26 API endpoints.

### Game History

Base path:

```text
/apis/game_history.json
```

Required query information includes:

```text
page
username
platform
mode
```

Conceptually:

```text
/apis/game_history.json?page={page}&username={username}&platform={platform}&mode={mode}
```

The collector reads `total_pages` and continues requesting pages until the available history has been collected.

### Game Log

Base path:

```text
/apis/game_log.json
```

Game-log requests require:

```text
id
username
platform
```

Conceptually:

```text
/apis/game_log.json?id={id}&username={username}&platform={platform}
```

The current implementation requests the API directly.

Game-log retrieval uses the API directly without first visiting the normal game webpage.

The application does not visit the normal MLBTS game webpage before requesting a game log.

---

## Game-Log Error Handling

MLBTS does not always return a usable historical game log.

Responses are classified as:

```text
ok
identity_mismatch
not_found
api_error
```

A known MLBTS response such as:

```text
Username and platform do not match the game record.
```

is stored as:

```text
identity_mismatch
```

Normal sync operations treat successful logs, `identity_mismatch`, and `not_found` as terminal results and do not repeatedly request those games.

Generic `api_error` responses are retryable on a later sync because they may represent a transient MLBTS problem. Network or request failures are also retryable because no API result was successfully received.

### Successful Log Preservation

A previously successful log is never replaced by a later MLBTS error response.

This protection applies to:

- the SQLite `game_logs` row
- the saved raw game-log JSON file

This is important because MLBTS historical API behavior can change over time.

---

## CPU Game Filtering

CPU detection is based on the team-name fields:

```text
home_full_name
away_full_name
```

A game is considered a CPU game when either full team name is `CPU`, case-insensitively.

The application deliberately does not use only `home_name` or `away_name` for CPU filtering.

MLBTS can use `CPU` in those username-style fields as a marker for the searched user's side, even when the actual game was human-vs-human.

---

## User-Side Attribution

The shared parser determines whether the configured or searched user was home or away.

It first compares the cleaned username against:

```text
home_name
away_name
```

MLBTS formatting suffixes such as:

```text
^b53^
```

are removed before comparison.

When necessary, the parser can also use the MLBTS `CPU` username marker as a side-attribution fallback.

This shared logic is used across:

- game collection
- local scouting
- live scouting

That prevents each part of the project from maintaining its own username-attribution rules.

---

## Baseball Innings-Pitched Handling

Baseball innings notation is not decimal arithmetic.

For example:

```text
5.0 = 15 outs
5.1 = 16 outs
5.2 = 17 outs
```

It would be incorrect to treat `5.2` as 5.2 mathematical innings.

The application therefore stores authoritative pitching duration as:

```text
pitching_outs
```

in both:

```text
team_box_scores
player_pitching_stats
```

The older numeric IP fields remain available for compatibility and display purposes, but calculations such as ERA use outs.

ERA is calculated from:

```text
ERA = earned_runs * 27 / pitching_outs
```

Example:

```text
3 ER in 5.2 IP
= 3 ER in 17 outs
= 4.76 ERA
```

Existing databases are automatically migrated to add the `pitching_outs` columns when necessary. On application startup, legacy parsed pitching rows that have innings pitched but no outs value are rebuilt from already-stored successful raw game logs. That backfill does not make MLBTS network requests.

---

## Database

The local SQLite database is:

```text
data/mlb26_games.sqlite3
```

It is intentionally excluded from Git.

### `games`

Stores filtered game-history records including:

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

Stores MLBTS game-log results:

```text
game_id
fetched_at
api_status
raw_game_log_json
raw_text_log
```

### `team_box_scores`

Stores parsed team statistics including:

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
pitching_outs
pitching_h
pitching_r
pitching_er
pitching_bb
pitching_so
```

### `player_batting_stats`

Stores individual batting statistics including:

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

Stores individual pitching statistics including:

```text
game_id
team_id
team_name
player_name
ip
pitching_outs
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

## Backend CLI

Run CLI commands from the repository root using:

```bash
python -m src.main <command>
```

### Initialize

```bash
python -m src.main init
```

### Sync Game History

```bash
python -m src.main sync-history
```

This retrieves available game-history pages, filters CPU games, updates SQLite, and exports the filtered history.

### Sync Game Logs

```bash
python -m src.main sync-logs
```

This retrieves game logs for stored games that do not yet have a recorded game-log API result.

### Reparse Stored Game Logs

```bash
python -m src.main reparse-logs
```

This rebuilds parsed box-score data from all successful raw game logs already stored in SQLite. It performs no MLBTS network requests and is useful after parser or schema changes.

### Sync Everything

```bash
python -m src.main sync-all
```

This runs game-history sync followed by game-log sync and exports the opponent summary.

### List Opponents

```bash
python -m src.main opponents
```

### Scout a Previously Played Opponent

```bash
python -m src.main scout --username OpponentName
```

### Live Scout an MLBTS User

```bash
python -m src.main live-scout --username OpponentName
```

The platform defaults to the centralized `PLATFORM` value from `src/config.py`.

Specify one explicitly if needed:

```bash
python -m src.main live-scout --username OpponentName --platform xbl
```

### Live Scout with Game Logs

```bash
python -m src.main live-scout --username OpponentName --include-logs
```

Game logs are fetched concurrently.

The default worker count is:

```text
5
```

It can be changed with:

```bash
python -m src.main live-scout --username OpponentName --include-logs --log-workers 3
```

### Limit History Pages and Analyzed Games

```bash
python -m src.main live-scout --username OpponentName --pages 2 --max-games 25
```

### Export Local Opponent Summary

```bash
python -m src.main export-opponents
```

---

## FastAPI Backend

Start FastAPI from the project root:

```bash
uvicorn src.api:app --reload --port 8000
```

Useful local addresses:

```text
Backend: localhost:8000
Health:  localhost:8000/health
Docs:    localhost:8000/docs
```

---

## Backend API Routes

The backend currently exposes:

```text
GET  /health
GET  /config
GET  /dashboard
GET  /games
GET  /games/{game_id}
GET  /opponents
GET  /opponents/{username}

POST /sync/history
POST /sync/logs
POST /sync/all
POST /live-scout
```

### `GET /health`

Returns basic backend status.

### `GET /config`

Returns the currently configured:

```text
username
platform
mode
```

The frontend uses this route so application identity settings do not need to be duplicated in TypeScript.

### `GET /dashboard`

Returns:

- total stored games
- total game-log records
- successful game-log count
- win/loss record
- win percentage
- average runs scored
- average runs allowed
- recent games

### `GET /games`

Supported query parameters:

```text
limit
offset
opponent
result
```

The backend limits an individual request to 500 rows.

The frontend Games page handles this by requesting additional pages until all available rows have been loaded.

### `GET /games/{game_id}`

Returns stored information for a specific game, including related game-log and parsed box-score information when available.

### `GET /opponents`

Returns locally known opponents derived from stored game history.

### `GET /opponents/{username}`

Returns a local scouting report for a previously played opponent.

### `POST /sync/history`

Runs game-history synchronization.

### `POST /sync/logs`

Runs game-log synchronization.

The response includes a detailed summary containing:

```text
requested
ok
identity_mismatch
not_found
api_error
request_failed
preserved_ok
```

The Sync page displays this result rather than only showing a generic completion message.

### `POST /sync/all`

Runs game-history sync followed by game-log sync.

### `POST /live-scout`

Example request body:

```json
{
  "username": "OpponentName",
  "platform": "psn",
  "pages": 1,
  "max_games": 25,
  "include_logs": true,
  "log_workers": 5
}
```

A live scout report includes:

- searched username
- platform
- mode
- pages fetched
- total games discovered
- CPU games removed
- unattributable games skipped
- recent games analyzed
- wins
- losses
- win percentage
- runs per game
- runs allowed per game
- hits per game
- hits allowed per game
- optional batting average
- optional pitching innings
- optional ERA
- recent game details

Live scouting does not write the opponent's history into the main local games database.

---

## Frontend Setup

Install frontend dependencies:

```bash
cd web
npm install
```

Create the local frontend environment file:

```text
web/.env.local
```

Use:

```text
web/.env.example
```

as the template.

The environment setting identifies the FastAPI backend used by the browser.

The example file contains:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Then run:

```bash
npm run dev
```

The frontend is available at:

```text
localhost:3000
```

---

## Running the Full Application

Use two terminals.

### Terminal 1 — Backend

From the repository root:

```bash
source .venv/bin/activate
uvicorn src.api:app --reload --port 8000
```

### Terminal 2 — Frontend

From the repository root:

```bash
cd web
npm run dev
```

Then open:

```text
localhost:3000
```

---

## Frontend Pages

### Dashboard

Displays a summary of the locally stored game database, including record, averages, successful log count, and recent games.

### Games

Displays the complete local human-vs-human game history.

Features include:

- sortable columns
- configurable row count
- opponent names
- results
- scores
- hits
- game IDs
- links to MLB The Show game pages

Selecting `All` loads all available games by paging through the backend API rather than assuming the database contains fewer than 500 records.

### Opponents

Displays opponents found in the local database and their aggregate history against the configured user.

### Scout

Provides two scouting modes.

#### Local Scout

Uses only the local SQLite database to analyze an opponent already present in stored history.

#### Live Scout

Requests another user's current MLBTS history directly.

Options include:

- username
- platform
- history pages
- maximum games
- optional game logs
- configurable game-log worker count

If game logs are enabled, the tool performs additional MLBTS API requests and can calculate batting average, pitching innings, and ERA.

### Sync

Provides controls for:

- history-only sync
- game-log-only sync
- full sync

The page also displays detailed game-log synchronization results.

---

## Testing

### Python

From the project root:

```bash
python -m compileall src tests
python -m unittest discover -s tests -v
```

The current automated suite contains:

```text
43 tests
```

The tests use temporary SQLite databases and temporary directories where needed.

They do not require the production database and do not make MLBTS network requests.

Current test coverage includes:

- username style-suffix removal
- case-insensitive username normalization
- CPU team filtering
- MLBTS CPU side-marker handling
- home/away user attribution
- opponent attribution
- baseball IP-to-outs conversion
- outs-to-IP conversion
- ERA calculation
- safe numeric conversion
- CSV integer parsing
- creation of pitching-out columns
- migration of older databases
- MLBTS game-log status classification
- unfetched-game selection
- prevention of automatic retries for recorded API errors
- preservation of successful database logs
- preservation of successful raw log files
- team pitching-out parsing
- player pitching-out parsing
- replacement of previously parsed box-score rows

### Frontend

From the `web` directory:

```bash
npm run lint
npm run build
```

A successful production build also performs TypeScript validation.

---

## Local Data

The following are intentionally local-only:

```text
data/mlb26_games.sqlite3
data/raw_game_logs/
data/exports/
web/.env.local
.venv/
```

Do not commit the production SQLite database or downloaded game logs.

---

## Current Limitations

The project currently does not include:

- background job processing for long-running sync operations
- persistent live-scout caching
- hosted authentication
- production deployment configuration
- deep play-by-play analysis
- pitch-selection tendency analysis
- hitting tendency analysis
- advanced charting
- player-card trend analysis

Sync operations currently run synchronously through the FastAPI request that triggered them.

The browser must wait for the operation to finish.

---

## Development Notes

When modifying parsing, attribution, database migration, or game-log handling, run the Python tests before committing:

```bash
python -m unittest discover -s tests -v
```

When modifying the frontend, also run:

```bash
cd web
npm run lint
npm run build
```

The most important invariants in the current implementation are:

1. CPU filtering uses the full team-name fields.
2. Username attribution uses shared parser logic.
3. Game-log requests include game ID, username, and platform.
4. Game-log retrieval uses the MLBTS API directly.
5. Known MLBTS API results are not repeatedly retried.
6. Successful stored game logs are never downgraded by later API errors.
7. Pitching calculations use outs rather than decimal interpretation of baseball innings notation.
8. The configured MLBTS identity is centralized in the backend.
9. SQLite connections are closed after CLI and API request use.
10. The frontend production build and automated Python tests should pass before changes are committed.

---

## Future Development

Potential future improvements include:

- asynchronous background sync jobs
- sync progress reporting
- persistent live-scout caching
- deeper play-by-play parsing
- pitch-selection analysis
- plate-discipline trends
- strikeout and walk trends
- inning-by-inning scoring analysis
- player-card performance analysis
- charts and visual trend reporting
- deployment configuration
- authentication for hosted use
