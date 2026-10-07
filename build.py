#!/usr/bin/env python3
"""Build data/tracker.json from cached ESPN raw JSON (no network). Nothing typed in by hand."""
import json, os, glob, datetime
from collections import defaultdict
from zoneinfo import ZoneInfo
os.chdir(os.path.dirname(os.path.abspath(__file__)))
ET = ZoneInfo("America/New_York")
CHE = "363"
R = lambda k: json.load(open(f"data/raw/{k}.json"))
man = json.load(open("data/manifest.json"))

def et(iso):
    d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ET)
    return {"iso_et": d.isoformat(), "date": d.strftime("%a %b %-d, %Y"), "short": d.strftime("%a %b %-d"),
            "time": d.strftime("%-I:%M %p ET"), "tz": d.tzname()}

def sval(x):
    s = x.get("score")
    if isinstance(s, dict): return int(s["value"]) if s.get("value") is not None else None
    return int(s) if s not in (None, "") else None

# ---------- official table (ESPN standings endpoint) ----------
st = R("standings")
season_name = st["children"][0]["name"]
table = []
for e in st["children"][0]["standings"]["entries"]:
    s = {x["name"]: x.get("value") for x in e["stats"]}
    table.append({"rank": int(s["rank"]), "id": e["team"]["id"], "name": e["team"]["displayName"],
                  "short": e["team"].get("shortDisplayName", e["team"]["displayName"]), "abbr": e["team"]["abbreviation"],
                  "gp": int(s["gamesPlayed"]), "w": int(s["wins"]), "d": int(s["ties"]), "l": int(s["losses"]),
                  "gf": int(s["pointsFor"]), "ga": int(s["pointsAgainst"]), "gd": int(s["pointDifferential"]),
                  "pts": int(s["points"]), "note": (e.get("note") or {}).get("description"), "color": (e.get("note") or {}).get("color")})
table.sort(key=lambda r: r["rank"])
names = {r["id"]: r for r in table}

# ---------- league results from the scoreboard endpoint (second source) ----------
def league_games(sb_key, slug):
    out = []
    for e in R(sb_key)["events"]:
        if e["season"].get("slug") != slug: continue
        c = e["competitions"][0]
        if not c["status"]["type"].get("completed"): continue
        h = next(x for x in c["competitors"] if x["homeAway"] == "home"); a = next(x for x in c["competitors"] if x["homeAway"] == "away")
        out.append({"id": e["id"], "date": e["date"], "home": h["team"]["id"], "away": a["team"]["id"],
                    "hs": int(h["score"]), "as": int(a["score"]),
                    "hname": h["team"]["displayName"], "aname": a["team"]["displayName"], "details": c.get("details", [])})
    out.sort(key=lambda g: (g["date"], g["id"]))
    return out

g26 = league_games("scoreboard_2026", "2026-27-english-premier-league")
g25 = league_games("scoreboard_2025", "2025-26-english-premier-league") + league_games("scoreboard_2026", "2025-26-english-premier-league")
g25.sort(key=lambda g: (g["date"], g["id"]))

def compute_table(games, upto_k=None):
    """Table from game list; if upto_k, use only each club's first k matches (by date)."""
    t = defaultdict(lambda: {"gp": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0})
    for g in games:
        for me, op, ms, os_ in ((g["home"], g["away"], g["hs"], g["as"]), (g["away"], g["home"], g["as"], g["hs"])):
            r = t[me]
            if upto_k is not None and r["gp"] >= upto_k: continue
            r["gp"] += 1; r["gf"] += ms; r["ga"] += os_
            if ms > os_: r["w"] += 1; r["pts"] += 3
            elif ms == os_: r["d"] += 1; r["pts"] += 1
            else: r["l"] += 1
    rows = [{"id": k, **v, "gd": v["gf"] - v["ga"]} for k, v in t.items()]
    rows.sort(key=lambda r: (-r["pts"], -r["gd"], -r["gf"], names.get(r["id"], {"name": r["id"]})["name"]))
    for i, r in enumerate(rows): r["rank"] = i + 1
    return rows

maxgp = max(r["gp"] for r in table)
rounds = []   # position of every club after each club's k-th match
for k in range(1, maxgp + 1):
    rows = compute_table(g26, k)
    rounds.append({r["id"]: {"rank": r["rank"], "pts": r["pts"], "gd": r["gd"]} for r in rows})
# are rounds aligned as clean matchweeks (each block of 10 = all 20 clubs once)?
aligned = all(len({t for g in g26[i*10:(i+1)*10] for t in (g["home"], g["away"])}) == 20 for i in range(len(g26)//10)) and len(g26) % 10 == 0

# ---------- Chelsea PL matches ----------
def che_view(g, rnd_lookup=None):
    home = g["home"] == CHE
    gf, ga = (g["hs"], g["as"]) if home else (g["as"], g["hs"])
    opp = g["away"] if home else g["home"]
    return {"id": g["id"], "home": home, "opp": opp, "opp_name": g["aname"] if home else g["hname"], "gf": gf, "ga": ga,
            "res": "W" if gf > ga else "D" if gf == ga else "L", "pts": 3 if gf > ga else 1 if gf == ga else 0, **et(g["date"])}

che26 = [che_view(g) for g in g26 if CHE in (g["home"], g["away"])]
che25 = [che_view(g) for g in g25 if CHE in (g["home"], g["away"])]
cum = 0
for i, m in enumerate(che26):
    cum += m["pts"]; m["cum_pts"] = cum; m["n"] = i + 1
    m["pos_after"] = rounds[i][CHE]["rank"]
cum = 0
pace25 = []
for m in che25: cum += m["pts"]; pace25.append(cum)
# leader's points after k matches (from the per-round tables)
leader_pts = [max(v["pts"] for v in r.values()) for r in rounds]
fourth_pts = [sorted((v["pts"] for v in r.values()), reverse=True)[3] for r in rounds]

# ---------- match summaries: scorers, cards, shots, possession ----------
summ = {}
for f in glob.glob("data/raw/summary_*.json"):
    d = json.load(open(f)); eid = f.split("_")[-1].split(".")[0]
    goals, reds = [], []
    for k in d.get("keyEvents", []):
        txt = k.get("type", {}).get("text", ""); team = (k.get("team") or {}).get("id")
        parts = [p.get("athlete", {}).get("displayName") for p in k.get("participants", [])]
        if k.get("scoringPlay"):
            og = "Own Goal" in txt
            goals.append({"team": team, "min": k.get("clock", {}).get("displayValue"), "scorer": parts[0] if parts else None,
                          "assist": (parts[1] if len(parts) > 1 and not og else None), "og": og, "pen": "Penalty" in txt, "header": "Header" in txt})
        if "Red Card" in txt:
            reds.append({"team": team, "min": k.get("clock", {}).get("displayValue"), "player": parts[0] if parts else None})
    box = {}
    for t in d.get("boxscore", {}).get("teams", []):
        sm = {s["name"]: s.get("displayValue") for s in t.get("statistics", [])}
        box[t["team"]["id"]] = {k: sm.get(k) for k in ("possessionPct", "totalShots", "shotsOnTarget")}
    hdr = d["header"]["competitions"][0]
    summ[eid] = {"goals": goals, "reds": reds, "box": box, "attendance": d.get("gameInfo", {}).get("attendance"),
                 "venue": (d.get("gameInfo", {}).get("venue") or {}).get("fullName"),
                 "score": {c["team"]["id"]: int(c["score"]) for c in hdr["competitors"]}}

# ---------- all-competitions results (team schedule endpoint) ----------
def sched_event(e):
    c = e["competitions"][0]
    me = next(x for x in c["competitors"] if x["team"]["id"] == CHE); op = next(x for x in c["competitors"] if x["team"]["id"] != CHE)
    lg = e.get("league", {})
    b = [x.get("media", {}).get("shortName") for x in c.get("broadcasts", []) if x.get("media", {}).get("shortName")]
    r = {"id": e["id"], "comp": lg.get("abbreviation") or lg.get("name"), "comp_slug": lg.get("slug"),
         "stage": e.get("seasonType", {}).get("name"), "home": me["homeAway"] == "home", "opp": op["team"]["id"],
         "opp_name": op["team"]["displayName"], "opp_abbr": op["team"].get("abbreviation"),
         "venue": (c.get("venue") or {}).get("fullName"), "city": ((c.get("venue") or {}).get("address") or {}).get("city"),
         "tv": b, "status": c["status"]["type"]["name"], "completed": c["status"]["type"].get("completed", False),
         "time_valid": e.get("timeValid", c.get("timeValid", True)), "neutral": c.get("neutralSite", False),
         "url": next((l["href"] for l in e.get("links", []) if "desktop" in l.get("rel", [])), None), **et(e["date"])}
    if r["completed"]:
        r["gf"], r["ga"] = sval(me), sval(op)
        r["so_gf"], r["so_ga"] = me.get("shootoutScore"), op.get("shootoutScore")
        r["res"] = "W" if r["gf"] > r["ga"] else "L" if r["gf"] < r["ga"] else "D"
        if r["id"] in summ: r["summary"] = summ[r["id"]]
    if r["opp"] in names: r["opp_rank"] = names[r["opp"]]["rank"]
    return r

allres = sorted((sched_event(e) for e in R("all_results")["events"]), key=lambda r: r["iso_et"])
fixtures = sorted((sched_event(e) for e in R("all_fixtures")["events"] if not e["competitions"][0]["status"]["type"].get("completed")), key=lambda r: r["iso_et"])
competitive = [r for r in allres if r["comp_slug"] != "club.friendly"]
friendlies = [r for r in allres if r["comp_slug"] == "club.friendly"]
for m in che26:
    s = next((r for r in allres if r["id"] == m["id"]), None)
    if s: m.update({k: s.get(k) for k in ("venue", "tv", "url", "summary")})

# ---------- scorers (competitive, all comps) ----------
sc = defaultdict(lambda: {"goals": 0, "pl": 0, "cup": 0, "pens": 0, "assists": 0})
og_for = 0
for r in competitive:
    for g in r.get("summary", {}).get("goals", []):
        if g["team"] != CHE: continue
        if g["og"]: og_for += 1; continue
        p = sc[g["scorer"]]; p["goals"] += 1; p["pl" if r["comp_slug"] == "eng.1" else "cup"] += 1; p["pens"] += g["pen"]
        if g["assist"]: sc[g["assist"]]["assists"] += 1
scorers = sorted(({"name": k, **v} for k, v in sc.items()), key=lambda p: (-p["goals"], -p["assists"], p["name"]))

me = names[CHE]
top4 = table[3]; top = table[0]; drop = next(r for r in table if r["note"] == "Relegation")
nxt = fixtures[0] if fixtures else None
form_pl = "".join(m["res"] for m in che26)
form_all = "".join(r["res"] for r in competitive)
tr = {
  "season": season_name, "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
  "sources": man["sources"], "logos": json.load(open("data/logos/manifest.json")),
  "table": table, "chelsea": me, "rounds_aligned": aligned, "matches_in_season": 38,
  "rounds": [{k: v for k, v in r.items()} for r in rounds],
  "che_pl": che26, "pace_2025": pace25, "pace_2025_final": {"pts": pace25[-1] if pace25 else None, "gp": len(pace25)},
  "standings_2025_che": next(({x["name"]: x.get("value") for x in e["stats"]} for e in R("standings_2025")["children"][0]["standings"]["entries"] if e["team"]["id"] == CHE), None),
  "leader_pts": leader_pts, "fourth_pts": fourth_pts,
  "competitive": competitive, "friendlies": friendlies, "fixtures": fixtures, "scorers": scorers, "og_for": og_for,
  "headline": {"rank": me["rank"], "pts": me["pts"], "record": f'{me["w"]}-{me["d"]}-{me["l"]}', "gd": me["gd"], "gp": me["gp"],
               "gap_top": top["pts"] - me["pts"], "top_name": top["name"], "gap_top4": top4["pts"] - me["pts"], "top4_name": top4["name"],
               "above_drop": me["pts"] - drop["pts"], "drop_name": drop["name"], "drop_rank": drop["rank"],
               "form_pl": form_pl, "form_all": form_all, "pts_2025_same_point": pace25[me["gp"]-1] if len(pace25) >= me["gp"] else None,
               "next": nxt, "pl_left": sum(1 for f in fixtures if f["comp_slug"] == "eng.1"),
               "last_pl_date": che26[-1]["date"] if che26 else None},
}
json.dump(tr, open("data/tracker.json", "w"), indent=1, ensure_ascii=False)
print("built data/tracker.json:", me["rank"], me["pts"], "pts", form_pl, "| fixtures", len(fixtures), "| aligned rounds", aligned, "| scorers", scorers[:3])
