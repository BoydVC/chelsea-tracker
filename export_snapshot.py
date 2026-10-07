#!/usr/bin/env python3
"""Inline data, fonts and crests into dist/index.html and dist/chelsea-tracker-2026-27.html (fully offline)."""
import json, base64, os, glob
os.chdir(os.path.dirname(os.path.abspath(__file__)))
t = open("src/template.html").read()
d = json.load(open("data/tracker.json"))
b64 = lambda p: base64.b64encode(open(p, "rb").read()).decode()
fonts = (f'@font-face{{font-family:"OS";src:url(data:font/ttf;base64,{b64("src/fonts/Oswald.ttf")}) format("truetype");font-weight:200 700}}'
         f'@font-face{{font-family:"SG";src:url(data:font/ttf;base64,{b64("src/fonts/SpaceGrotesk.ttf")}) format("truetype");font-weight:300 700}}')
logos = {os.path.basename(p)[:-4]: "data:image/png;base64," + b64(p) for p in glob.glob("data/logos/*.png")}
js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
html = t.replace("/*FONTS*/", fonts).replace("/*DATA*/null", js(d)).replace("/*LOGOS*/{}", js(logos))
os.makedirs("dist", exist_ok=True)
for f in ("dist/index.html", "dist/chelsea-tracker-2026-27.html"): open(f, "w").write(html)
print("wrote dist/chelsea-tracker-2026-27.html", round(len(html) / 1024), "KB")
