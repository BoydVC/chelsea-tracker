#!/usr/bin/env python3
"""Download small club crests (ESPN CDN combiner, 96px) for the 20 PL clubs + cup/friendly opponents; record in data/logos/manifest.json."""
import json, subprocess, datetime, os, glob
os.chdir(os.path.dirname(os.path.abspath(__file__)))
ids = set()
for e in json.load(open("data/raw/standings.json"))["children"][0]["standings"]["entries"]: ids.add(e["team"]["id"])
for f in ("all_results", "all_fixtures"):
    for e in json.load(open(f"data/raw/{f}.json"))["events"]:
        for c in e["competitions"][0]["competitors"]: ids.add(c["team"]["id"])
man = {}
for i in sorted(ids):
    u = f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/soccer/500/{i}.png&h=96&w=96"
    out = f"data/logos/{i}.png"
    r = subprocess.run(["curl", "-s", "-m", "30", "-o", out, "-w", "%{http_code}", u], capture_output=True, text=True)
    ok = r.stdout.strip() == "200" and os.path.getsize(out) > 200 and open(out, "rb").read(4) == b"\x89PNG"
    if not ok and os.path.exists(out): os.remove(out)
    man[i] = {"url": u, "ok": ok, "fetched_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
json.dump(man, open("data/logos/manifest.json", "w"), indent=1)
print(sum(m["ok"] for m in man.values()), "/", len(man), "logos")
