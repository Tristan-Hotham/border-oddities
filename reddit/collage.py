"""r/dataisbeautiful collage for border-oddities: 2400 x 3200 px, light background. Numbers from data/results.json.
Rule: no text sits on land or on data. The world map and the insets carry no labels at all; every caption sits on the
paper below its panel, and the legend explains every colour and symbol."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
from figstyle import *
from matplotlib.lines import Line2D

R = jload(f"{DATA}/results.json"); S = jload(f"{DATA}/site.json")
BGc = "#F7F5F0"; SEAc = "#E9EFF2"; LANDc = "#E2DDD1"
w, t, n, ba, c = R["wiki"], R["tri"], R["nei"], R["baarle"], R["chhits"]
KC = [k[2] for k in S["kinds"]]; KN = [k[1] for k in S["kinds"]]
ODD = S["odd"]; TRI = [x for x in S["tri"] if not x[4]]

fig = plt.figure(figsize=(12, 16.0), dpi=200, facecolor=BGc)
fig.text(.045, .985, "The world's strangest borders", fontproperties=DISP, fontsize=42, color=FG, va="top")
fig.text(.045, .943, f"{w['true_enclaves']} true enclaves in {w['true_parcels']} pieces, {t['n']} tripoints, {w['mapped']} oddities in all. Belgium owns {ba['belgian']} pieces of the Dutch town\n"
         f"of Baarle, and in one the border runs through a front door. Most are too small for a world map to see.",
         fontproperties=SERP, fontsize=14, color=FG, va="top", linespacing=1.45)

# ---- world map (no labels on it)
ax = fig.add_axes([.01, .6, .98, .275])
outline(ax, fc=SEAc, ec="#C9CDD0", lw=.8); world(ax, lw=.3, land=LANDc, ec=BGc)
x, y = proj([q[1] for q in TRI], [q[0] for q in TRI]); ax.scatter(x, y, marker="^", s=12, c="#2B2F36", ec="#fff", lw=.3, zorder=4)
order = [6, 4, 5, 3, 2, 1, 7, 8, 0]
for k in order:
    q = [r for r in ODD if r[2] == k]
    if q:
        x, y = proj([r[1] for r in q], [r[0] for r in q]); ax.scatter(x, y, s=30, c=KC[k], ec="#fff", lw=.6, zorder=5 + order.index(k) * .01)
cnt = [sum(1 for r in ODD if r[2] == k) for k in range(len(KN))]
h = [Line2D([], [], marker="o", ls="", mfc=KC[k], mec="#fff", ms=9, label=f"{KN[k]} ({cnt[k]})") for k in range(len(KN)) if cnt[k]]
h.append(Line2D([], [], marker="^", ls="", mfc="#2B2F36", mec="#fff", ms=9, label=f"Tripoint ({t['n']})"))
fig.legend(handles=h, loc="upper center", ncol=4, frameon=False, fontsize=10.5, bbox_to_anchor=(.5, .598), columnspacing=1.4, handletextpad=.4)

# ---- insets (dots only), captions below on paper
PICK = ["madha", "llivia", "cooch", "kazungula", "kaliningrad", "nakhchivan", "roberts", "birtawil"]
CAP = {"madha": f"Nahwa (UAE) inside Madha (Oman)\ninside the UAE",
       "llivia": "Llívia: a Spanish town\ninside France since 1659",
       "cooch": f"Cooch Behar: {c['indian'] + c['bangladeshi']} enclaves,\nswapped in 2015",
       "kazungula": "Kazungula: four countries\nat one point on the map",
       "kaliningrad": "Kaliningrad: Russia\nbetween Poland and Lithuania",
       "nakhchivan": "Nakhchivan: Azerbaijan\nwith no coast at all",
       "roberts": "Point Roberts: 40 km of\nCanada from the rest of the US",
       "birtawil": f"Bir Tawil: {R['facts']['bir_tawil_km2']:,} km²\nclaimed by nobody"}
TT = {x["id"]: x for x in S["tour"]}
for i, k in enumerate(PICK):
    col, row = i % 4, i // 4
    a = fig.add_axes([.04 + col * .236, .395 - row * .165, .215, .105])
    inset_ax(a, TT[k], label=False, sea=SEAc, land=LANDc)
    fig.text(.04 + col * .236, .395 - row * .165 - .005, CAP[k], fontsize=9.6, color=FG, va="top", linespacing=1.3)
fig.text(.04, .515, "Eight of them as Natural Earth 1:10m draws them. Red: the owner's land; dot: the place; dark grey: unclaimed.", fontsize=10.5, color=MUT)

# ---- bars: neighbours and tripoints
for j, (rows, colr, ttl) in enumerate(((n["top"][:8], COOL, "Most neighbours"), (t["top"][:8], NAVY, "Most tripoints"))):
    a = fig.add_axes([.13 + j * .475, .05, .32, .095]); a.set_facecolor(BGc)
    nm = [r["name"] for r in rows][::-1]; v = [r["n"] for r in rows][::-1]
    a.barh(nm, v, color=colr, height=.66)
    for ii, vv in enumerate(v): a.text(vv + .25, ii, str(vv), va="center", fontsize=10)
    a.set_xlim(0, 17); a.set_xticks([]); spines(a); a.spines["bottom"].set_visible(False); a.tick_params(axis="y", length=0, labelsize=10.5)
    a.set_title(ttl, loc="left", fontsize=13, color=FG, fontproperties=SERB, pad=8)
fig.text(.045, .176, f"China and Russia border {n['china']} countries each. Two countries are doubly landlocked: Liechtenstein and Uzbekistan.", fontsize=11, color=FG)
fig.text(.045, .018, "Data: Wikipedia, List of enclaves and exclaves and related articles (CC BY-SA 4.0); Wikidata (CC0); Natural Earth 1:10m (public domain).\n"
         "Borders are Natural Earth's de facto lines, not an endorsement of any claim. Tripoints computed from shared boundary vertices. Dr Tristan Hotham.",
         fontsize=8.6, color=MUT, linespacing=1.4)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strangest_borders.png")
fig.savefig(out, dpi=200, facecolor=BGc)
print("collage", out)
