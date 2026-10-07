#!/usr/bin/env python3
"""Fetch raw ESPN public JSON into data/raw/ and record URL + fetch time in data/manifest.json."""
import json, subprocess, datetime, os, hashlib, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
B = "https://site.api.espn.com/apis"
SOURCES = {
  "standings": f"{B}/v2/sports/soccer/eng.1/standings",
  "standings_2025": f"{B}/v2/sports/soccer/eng.1/standings?season=2025",
  "pl_results": f"{B}/site/v2/sports/soccer/eng.1/teams/363/schedule",
  "pl_fixtures": f"{B}/site/v2/sports/soccer/eng.1/teams/363/schedule?fixture=true",
  "all_results": f"{B}/site/v2/sports/soccer/all/teams/363/schedule",
  "all_fixtures": f"{B}/site/v2/sports/soccer/all/teams/363/schedule?fixture=true",
  "scoreboard_2026": f"{B}/site/v2/sports/soccer/eng.1/scoreboard?dates=2026&limit=1000",
  "scoreboard_2025": f"{B}/site/v2/sports/soccer/eng.1/scoreboard?dates=2025&limit=1000",
  "team": f"{B}/site/v2/sports/soccer/eng.1/teams/363",
}
man = {"fetched_by": "fetch.py (curl)", "sources": {}}
for k, u in SOURCES.items():
    out = f"data/raw/{k}.json"
    t = datetime.datetime.now().astimezone()
    r = subprocess.run(["curl", "-s", "--compressed", "-m", "60", "-o", out, "-w", "%{http_code}", u], capture_output=True, text=True)
    code = r.stdout.strip()
    raw = open(out, "rb").read() if os.path.exists(out) else b""
    ok = code == "200"
    try: json.loads(raw)
    except Exception: ok = False
    man["sources"][k] = {"url": u, "file": out, "http": code, "ok": ok, "bytes": len(raw),
                         "sha256": hashlib.sha256(raw).hexdigest(), "fetched_at": t.isoformat(timespec="seconds")}
    print(k, code, len(raw), "OK" if ok else "FAIL")
# Per-match summaries (goal scorers, cards) for every completed competitive match (not friendlies)
allr = json.load(open("data/raw/all_results.json"))
for e in allr["events"]:
    lg = e.get("league", {}).get("slug")
    if lg == "club.friendly" or not e["competitions"][0]["status"]["type"].get("completed"): continue
    k = f"summary_{e['id']}"; u = f"{B}/site/v2/sports/soccer/{lg}/summary?event={e['id']}"
    out = f"data/raw/{k}.json"; t = datetime.datetime.now().astimezone()
    r = subprocess.run(["curl", "-s", "--compressed", "-m", "60", "-o", out, "-w", "%{http_code}", u], capture_output=True, text=True)
    raw = open(out, "rb").read(); ok = r.stdout.strip() == "200"
    try: json.loads(raw)
    except Exception: ok = False
    man["sources"][k] = {"url": u, "file": out, "http": r.stdout.strip(), "ok": ok, "bytes": len(raw),
                         "sha256": hashlib.sha256(raw).hexdigest(), "fetched_at": t.isoformat(timespec="seconds")}
    print(k, r.stdout.strip(), len(raw), "OK" if ok else "FAIL")
json.dump(man, open("data/manifest.json", "w"), indent=2)
if not all(s["ok"] for s in man["sources"].values()): sys.exit(1)
