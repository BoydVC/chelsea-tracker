#!/usr/bin/env python3
"""Smoke test: cross-checks the page's numbers against independent ESPN endpoints and the raw cache."""
import json, os, re, glob, hashlib, datetime, urllib.request
from collections import defaultdict
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
P = F = 0
def check(cond, msg):
    global P, F
    if cond: P += 1
    else: F += 1; print("FAIL:", msg)
R = lambda k: json.load(open(f"data/raw/{k}.json"))
T = json.load(open("data/tracker.json")); man = json.load(open("data/manifest.json"))
CHE = "363"

# 1. manifest integrity
for k, s in man["sources"].items():
    check(s["ok"] and s["http"] == "200" and s["url"].startswith("https://site.api.espn.com/"), f"source {k} ok/url")
    check(hashlib.sha256(open(s["file"], "rb").read()).hexdigest() == s["sha256"], f"sha256 {k}")
    check(datetime.datetime.fromisoformat(s["fetched_at"]).tzinfo is not None, f"fetched_at tz {k}")

# 2. Official standings (endpoint A) vs table recomputed from the league scoreboard (endpoint B)
st = {e["team"]["id"]: {x["name"]: x.get("value") for x in e["stats"]} | {"name": e["team"]["displayName"]} for e in R("standings")["children"][0]["standings"]["entries"]}
check(len(st) == 20, "20 clubs in standings")
t = defaultdict(lambda: [0]*6)  # gp w d l gf ga
games = []
for e in R("scoreboard_2026")["events"]:
    if e["season"]["slug"] != "2026-27-english-premier-league" or not e["competitions"][0]["status"]["type"]["completed"]: continue
    c = {x["homeAway"]: x for x in e["competitions"][0]["competitors"]}
    h, a, hs, as_ = c["home"]["team"]["id"], c["away"]["team"]["id"], int(c["home"]["score"]), int(c["away"]["score"])
    games.append((e["id"], h, a, hs, as_))
    for me, ms, os_ in ((h, hs, as_), (a, as_, hs)):
        r = t[me]; r[0] += 1; r[4] += ms; r[5] += os_; r[1 if ms > os_ else 2 if ms == os_ else 3] += 1
for tid, s in st.items():
    gp, w, d, l, gf, ga = t[tid]
    check([gp, w, d, l, gf, ga] == [int(s["gamesPlayed"]), int(s["wins"]), int(s["ties"]), int(s["losses"]), int(s["pointsFor"]), int(s["pointsAgainst"])], f"{s['name']} record scoreboard vs standings {t[tid]}")
    check(3*w + d == int(s["points"]), f"{s['name']} points = 3W+D")
    check(w + d + l == gp, f"{s['name']} W+D+L=GP")
    check(gf - ga == int(s["pointDifferential"]), f"{s['name']} GD")
check(sum(r[4] for r in t.values()) == sum(r[5] for r in t.values()), "league GF total == GA total")
# order: recomputed sort matches official rank
order = sorted(st, key=lambda i: (-(3*t[i][1]+t[i][2]), -(t[i][4]-t[i][5]), -t[i][4]))
check([int(st[i]["rank"]) for i in order] == list(range(1, 21)), "recomputed order == official ranks")
# page table == standings
for row in T["table"]:
    s = st[row["id"]]; check(row["pts"] == int(s["points"]) and row["rank"] == int(s["rank"]), f"page table {row['name']}")
check(all(T["rounds"][-1][i]["rank"] == int(st[i]["rank"]) for i in st), "bump chart final column == official table")

# 3. Chelsea: team schedule endpoint (C) vs scoreboard (B) vs standings (A)
pl = [e for e in R("pl_results")["events"] if e["competitions"][0]["status"]["type"]["completed"]]
sbmap = {g[0]: g for g in games}
gf = ga = pts = 0
for e in pl:
    c = {x["team"]["id"]: x for x in e["competitions"][0]["competitors"]}
    me, op = int(c[CHE]["score"]["value"]), int(next(v for k, v in c.items() if k != CHE)["score"]["value"])
    g = sbmap.get(e["id"]); check(g is not None, f"PL match {e['id']} in scoreboard")
    if g: check((g[3], g[4]) == ((me, op) if g[1] == CHE else (op, me)), f"score {e['name']} schedule vs scoreboard")
    gf += me; ga += op; pts += 3 if me > op else 1 if me == op else 0
check(len(pl) == int(st[CHE]["gamesPlayed"]), "Chelsea PL matches == GP")
check((gf, ga, pts) == (int(st[CHE]["pointsFor"]), int(st[CHE]["pointsAgainst"]), int(st[CHE]["points"])), f"Chelsea GF/GA/Pts from schedule == standings ({gf},{ga},{pts})")
h = T["headline"]
check((h["pts"], h["rank"], h["gd"]) == (int(st[CHE]["points"]), int(st[CHE]["rank"]), gf - ga), "headline == standings")
check(T["che_pl"][-1]["cum_pts"] == h["pts"], "pace line ends at current points")
check(h["form_pl"] == "".join(m["res"] for m in T["che_pl"]), "PL form string")
# ESPN's own form string on Chelsea's last scoreboard event (newest last in our order)
last = max((e for e in R("scoreboard_2026")["events"] if e["season"]["slug"].startswith("2026-27") and e["competitions"][0]["status"]["type"]["completed"] and any(x["team"]["id"] == CHE for x in e["competitions"][0]["competitors"])), key=lambda e: e["date"])
espn_form = next(x for x in last["competitions"][0]["competitors"] if x["team"]["id"] == CHE).get("form")
check(espn_form is not None and set(espn_form) <= set("WDL"), f"ESPN form present ({espn_form})")
# 4. match summaries (endpoint D): final score + goal events add up
comp = T["competitive"]
check(len(comp) == len([e for e in R("all_results")["events"] if e.get("league", {}).get("slug") != "club.friendly"]), "competitive count")
tot_g = 0
for r in comp:
    s = json.load(open(f"data/raw/summary_{r['id']}.json"))
    hs = {c["team"]["id"]: int(c["score"]) for c in s["header"]["competitions"][0]["competitors"]}
    check((hs[CHE], hs[r["opp"]]) == (r["gf"], r["ga"]), f"summary score {r['opp_name']} {r['short']}")
    goals = [k for k in s["keyEvents"] if k.get("scoringPlay")]
    check(sum(1 for k in goals if k["team"]["id"] == CHE) == r["gf"] and sum(1 for k in goals if k["team"]["id"] == r["opp"]) == r["ga"], f"goal events add up {r['opp_name']}")
    tot_g += r["gf"]
check(sum(p["goals"] for p in T["scorers"]) + T["og_for"] == tot_g, "scorers + own goals == Chelsea competitive goals")
# 5. fixtures
fx = T["fixtures"]
pl_fx_ids = {e["id"] for e in R("pl_fixtures")["events"] if not e["competitions"][0]["status"]["type"]["completed"]}
check({f["id"] for f in fx if f["comp_slug"] == "eng.1"} == pl_fx_ids, "PL fixtures: all-comps endpoint == PL endpoint")
check(len(pl_fx_ids) + len(pl) == 38, "PL fixtures + played == 38")
check(all(f["iso_et"] > datetime.datetime.fromisoformat(T["sources"]["all_fixtures"]["fetched_at"]).isoformat()[:10] for f in fx), "fixtures are after fetch date")
check(fx == sorted(fx, key=lambda f: f["iso_et"]), "fixtures sorted")
utc = {e["id"]: e["date"] for e in R("all_fixtures")["events"]}
for f in fx:
    u = datetime.datetime.strptime(utc[f["id"]], "%Y-%m-%dT%H:%MZ")
    # independent DST rule (US: 2nd Sun Mar to 1st Sun Nov, 2 AM local) for the ET offset
    y = u.year; mar = datetime.datetime(y, 3, 8 + (6 - datetime.date(y, 3, 8).weekday()) % 7, 7); nov = datetime.datetime(y, 11, 1 + (6 - datetime.date(y, 11, 1).weekday()) % 7, 6)
    off = 4 if mar <= u < nov else 5
    loc = u - datetime.timedelta(hours=off)
    check(f["time"] == loc.strftime("%-I:%M %p ET"), f"ET time {f['short']} {f['opp_name']} {f['time']} vs {loc}")
    if f["opp"] in st: check(f.get("opp_rank") == int(st[f["opp"]]["rank"]), f"opp rank {f['opp_name']}")
check(h["next"]["id"] == fx[0]["id"], "next match is first fixture")
# 6. last season pace (scoreboard 2025+2026) vs 2025-26 final standings
s25 = next({x["name"]: x.get("value") for x in e["stats"]} for e in R("standings_2025")["children"][0]["standings"]["entries"] if e["team"]["id"] == CHE)
check(len(T["pace_2025"]) == 38 and T["pace_2025"][-1] == int(s25["points"]), f"2025-26 pace ends at {int(s25['points'])} pts over 38")
# 7. snapshot offline + server
html = open("dist/chelsea-tracker-2026-27.html").read()
check(not re.search(r'(src|href)="https?://(?!site\.api|www\.espn)', html) and "url(http" not in html and "fetch(" not in html, "snapshot loads nothing external")
check(not re.search(r'<(script|link|img)[^>]+(src|href)="https?:', html), "no external script/link/img tags")
check("const D=null" not in html and "/*DATA*/" not in html and "/*FONTS*/" not in html, "placeholders replaced")
check(len(glob.glob("data/logos/*.png")) >= 20, "crests cached")
try:
    ok = json.loads(urllib.request.urlopen("http://127.0.0.1:4271/healthz", timeout=5).read())["ok"]
    page = urllib.request.urlopen("http://127.0.0.1:4271/", timeout=5).read().decode()
    api = json.loads(urllib.request.urlopen("http://127.0.0.1:4271/api/tracker", timeout=5).read())
    check(ok and page == html and api["headline"]["pts"] == h["pts"], "server :4271 healthz, page, api")
except Exception as e:
    check(False, f"server :4271 reachable ({e})")
print(f"{P} passed, {F} failed")
raise SystemExit(1 if F else 0)
