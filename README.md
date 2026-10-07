# Chelsea Season Tracker 2026-27

A broadcast-style, single-page tracker of Chelsea's 2026-27 season, built for Boyd by TokenMax. It covers the current Premier League position, results so far, upcoming fixtures in Eastern time, and form charts. Every number comes from ESPN's free public JSON. Nothing is typed in by hand.

- **Live (box only):** http://127.0.0.1:4271/ (`nohup ./run.sh`), with `/healthz` and `/api/tracker`
- **Offline snapshot:** `dist/chelsea-tracker-2026-27.html` is one 749 KB file. Data, fonts (Oswald and Space Grotesk, OFL) and club crests are all inlined, and it makes no network calls.
- **Screenshots:** `screenshots/00-best-desktop-hero.png` (best), `01-desktop-full.png`, `02-phone-top.png`, `03-phone-full.png`

## Why this and not Orioles
`orioles-2026/` already holds a completed **Orioles 2026 Season in Review**: final record, game-by-game chart, AL East race, leaders, streaks. Building another one would have been a duplicate, so this is the fallback the brief named. `terps-preview/` is Maryland basketball and doesn't overlap.

Overlap with the other Chelsea projects is small:
- `chelsea-matchday/` is a one-match programme for Bournemouth on Oct 10.
- `chelsea-time-machine/` covers history from 1990 to 2026.
- Neither has a season-long position-by-matchweek chart, a points-pace comparison, all-competitions results with scorers, a full fixture list in ET, or a scorer chart.

## What's on the page
1. **Scorebug hero and ticker:** league position, points, W-D-L, GD, GF/GA, points per match, form strips (PL and all competitions).
2. **Next up:** opponent, date and kick-off in ET, venue, US TV (as ESPN lists it), and a live countdown. Also the gaps to 1st, to 4th and to the drop zone.
3. **Points pace:** Chelsea 2026-27 against Chelsea 2025-26 at the same stage, the league leader and 4th place. Toggles between "So far" and "Full season".
4. **Table race:** a bump chart of all 20 clubs by matchweek. Chelsea is highlighted, and hovering any club shows its path.
5. **Goals for and against:** a chart of every competitive match (PL and Carabao Cup) with W/D/L chips.
6. **Goals and assists:** the top 10 Chelsea contributors in all competitive matches.
7. **Results so far:** a card for each match with scorers and minutes, shots, shots on target, possession and attendance. Pre-season friendlies are listed separately (collapsed).
8. **Fixtures:** all 34 remaining (33 PL plus the Carabao Cup 4th round at Liverpool), grouped by month, with ET times, venue, TV where listed, and each opponent's current position. Filters: All, PL, Cups, Home, Away, Next 5.
9. **Full PL table:** with ESPN's zone markings.
10. **Sources footer:** every URL with its fetch time in ET.

## Headline facts (ESPN, fetched Oct 7, 2026, 7:47 PM ET)
- **10th, 7 pts after 5 matches** (W2 D1 L2, GF 10, GA 12, GD −2). That's 8 pts behind leaders Man City (15), 2 behind 4th-placed Brentford, and 4 above 18th-placed Coventry (drop zone).
- **Position by matchweek:** 6th → 4th → 4th → 6th → 10th. **PL form:** W W L D L. The last PL match was the 3–0 loss at Brentford on Fri Sep 18.
- **All competitions:** 4W 1D 2L, 18 scored and 15 conceded, including Carabao Cup wins over Luton (2–0) and Leeds (6–3).
- **Pace:** 7 pts vs 8 at the same stage of 2025-26, which finished 10th on 52 pts.
- **Top contributors (all comps):** Cole Palmer 4 goals and 2 assists, Morgan Rogers 3+4, João Pedro 3+3, Danny Welbeck 3+0.
- **Next match:** vs AFC Bournemouth (17th), **Sat Oct 10, 10:00 AM ET**, Stamford Bridge, Peacock. After that: at Everton Sat Oct 17 (7:30 AM ET), vs Tottenham Sat Oct 24 (12:30 PM ET), and at Liverpool in the Carabao Cup on Wed Oct 28 (4:00 PM ET).

## Data (all cached in `data/raw/`; URL, HTTP code, bytes, sha256 and fetch time are in `data/manifest.json`)
| Key | Endpoint |
|---|---|
| standings | `site.api.espn.com/apis/v2/sports/soccer/eng.1/standings` |
| standings_2025 | same, `?season=2025` (2025-26 final) |
| pl_results / pl_fixtures | `.../soccer/eng.1/teams/363/schedule` (`?fixture=true`) |
| all_results / all_fixtures | `.../soccer/all/teams/363/schedule` (`?fixture=true`) |
| scoreboard_2026 / scoreboard_2025 | `.../soccer/eng.1/scoreboard?dates=2026` / `?dates=2025` (every PL result, both seasons) |
| summary_<id> | `.../soccer/<league>/summary?event=<id>` for each completed competitive Chelsea match |
| crests | ESPN CDN combiner, 96 px (`data/logos/`, with their own manifest) |

## Run
```bash
nohup ./run.sh &        # build from cache → snapshot → (re)start :4271 → smoke test
./run.sh --fetch        # re-fetch ESPN + crests first
./run.sh stop
./screenshot.sh         # headless Chrome desktop + phone shots of the snapshot
python3 tests/smoke_test.py
```

## Smoke test: 263 checks, 0 failures
- **Totals cross-check across endpoints.** All 20 clubs' P/W/D/L/GF/GA are recomputed from the **scoreboard** endpoint and must equal the **standings** endpoint. Points = 3W+D, GD = GF−GA, and league GF = GA. The recomputed sort order must equal the official ranks.
- **Chelsea's season.** Each Chelsea match on the **team-schedule** endpoint must have the same score as on the scoreboard. Summed GF/GA/points must equal the standings, and the page headline, pace line and form string must agree.
- **Every competitive match.** The **summary** endpoint's final score must equal the schedule. Goal events must add up to the score for both sides, and scorers plus own goals must equal Chelsea's total.
- **Fixtures.** PL fixtures from the all-competitions endpoint must equal the PL-only endpoint, and played plus remaining must equal 38. Every ET kick-off time is re-derived from UTC with an independent US-DST rule. Opponent positions must match the table.
- **Last season.** The 2025-26 pace line, built from the scoreboard, must have 38 matches and end at ESPN's 2025-26 final points (52).
- **Integrity and serving.** Manifest sha256 values must match the cached files. The bump chart's last column must equal the official table. The snapshot must load nothing external, and the server on :4271 must serve healthz, the page (byte-identical to the snapshot) and the API.

## Notes and limits
- ESPN shows no PL match for Chelsea between Sep 18 and Oct 10, so the table is as of 5 matches.
- Positions after each matchweek use points, then GD, then goals scored. That's enough here, because the recomputed final order matches ESPN exactly. Every matchweek so far was complete, with all 20 clubs playing once.
- Kick-off times and TV are as ESPN lists them on the fetch date. Later PL dates can still move for TV selection. A blank TV slot means ESPN doesn't list one.
- Assists and own goals are as ESPN records them.

## Files
`fetch.py`, `fetch_logos.py` → `data/raw/`, `data/logos/` → `build.py` → `data/tracker.json` → `src/template.html` + `export_snapshot.py` → `dist/index.html`, `dist/chelsea-tracker-2026-27.html` · `server.py` · `run.sh` · `screenshot.sh` · `tests/smoke_test.py`


---
## Repo notes
- **Built:** Oct 7, 2026, by TokenMax (Boyd's Grok Bot) on the Grok Bot box.
- **Run:** `./run.sh` (then open the localhost URL it prints).
- Imported from `/workspace/tokenmax/chelsea-tracker` on Oct 23, 2026. node_modules, virtualenvs, logs and files over 20 MB were left out.
- Personal details (emails, phone numbers, home street address) were replaced with `[redacted-…]` placeholders.
