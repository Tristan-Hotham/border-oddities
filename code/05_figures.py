"""Header card, blog figures (release/blog/b_*.png, 1800 px wide) and paper figures (release/paper/f_*.png).
Numbers from data/results.json and data/site.json."""
import pandas as pd
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from figstyle import *

R = jload(f"{DATA}/results.json"); S = jload(f"{DATA}/site.json")
BL = os.path.join(ROOT, "release", "blog"); PA = os.path.join(ROOT, "release", "paper")
os.makedirs(BL, exist_ok=True); os.makedirs(PA, exist_ok=True)
HALO = [pe.withStroke(linewidth=3.5, foreground=SEA)]
HALOB = [pe.withStroke(linewidth=3.5, foreground=BG)]
KC = [k[2] for k in S["kinds"]]; KN = [k[1] for k in S["kinds"]]
ODD = S["odd"]; TRI = [t for t in S["tri"] if not t[4]]


def both(fig, name, blog=True):
    fig.savefig(os.path.join(PA, "f_" + name + ".png"), dpi=200, facecolor=fig.get_facecolor())
    if blog:
        fig.savefig(os.path.join(BL, "b_" + name + ".png"), dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def tri_marker(ax, lon, lat, s=16, z=4, c="#2B2F36"):
    x, y = proj(lon, lat); ax.scatter(x, y, marker="^", s=s, c=c, ec="#fff", lw=.4, zorder=z)


def odd_points(ax, s=26, z=5):
    order = [6, 4, 5, 3, 2, 1, 7, 8, 0]          # least important first
    for k in order:
        q = [r for r in ODD if r[2] == k]
        if not q: continue
        x, y = proj([r[1] for r in q], [r[0] for r in q])
        ax.scatter(x, y, s=s, c=KC[k], ec="#fff", lw=.6, zorder=z + order.index(k) * .01)


# ---------- world map of oddities ----------
fig = plt.figure(figsize=(12, 6.7), facecolor=BG); ax = fig.add_axes([0, .06, 1, .86])
outline(ax, fc=SEA, ec="#C9CDD0"); world(ax, ec=BG)
tri_marker(ax, [t[1] for t in TRI], [t[0] for t in TRI], s=11)
odd_points(ax, s=24)
fig.text(.02, .955, f"{R['wiki']['mapped']} border oddities from Wikipedia's lists, by type, and {R['tri']['n']} tripoints computed from Natural Earth (triangles)", fontsize=11, color=FG)
cnt = [sum(1 for r in ODD if r[2] == k) for k in range(len(KN))]
h = [Line2D([], [], marker="o", ls="", mfc=KC[k], mec="#fff", ms=8, label=f"{KN[k]} ({cnt[k]})") for k in range(len(KN)) if cnt[k]]
h.append(Line2D([], [], marker="^", ls="", mfc="#2B2F36", mec="#fff", ms=8, label="Tripoint"))
fig.legend(handles=h, loc="lower center", ncol=5, frameon=False, fontsize=9, bbox_to_anchor=(.5, -.005))
both(fig, "map")

# ---------- insets: the tour ----------
T = S["tour"]
fig, axs = plt.subplots(3, 5, figsize=(12, 8.4), facecolor=BG); fig.subplots_adjust(left=.01, right=.99, top=.93, bottom=.02, wspace=.06, hspace=.28)
for ax, t in zip(axs.flat, T):
    inset_ax(ax, t, fs=7.5)
    ax.set_title(t["t"], fontsize=10, color=FG, loc="left", pad=4, fontproperties=SERB)
fig.text(.01, .965, "Fifteen strange borders, as Natural Earth 1:10m draws them. Red: the owner's land. Dots: the place itself.", fontsize=11, color=FG)
both(fig, "insets")

# ---------- owners ----------
OW = R["wiki"]["owners"]
fig = plt.figure(figsize=(12, 7.6), facecolor=BG); ax = fig.add_axes([.22, .05, .7, .86]); ax.set_facecolor(BG)
nm = [o["owner"] for o in OW][::-1]; land = [o["n"] - o["water"] for o in OW][::-1]; wat = [o["water"] for o in OW][::-1]
ax.barh(nm, land, color=HOT, height=.7, label="on land"); ax.barh(nm, wat, left=land, color="#EBA59F", height=.7, label="island or water")
for i, o in enumerate(OW[::-1]):
    if o["parcels"] > o["n"]: ax.text(o["n"] + .08, i, f"{o['parcels']} pieces", va="center", fontsize=9.5, color=MUT)
spines(ax); ax.tick_params(axis="y", length=0, labelsize=10); ax.set_xlabel("true international enclaves (Wikipedia list entries)")
ax.xaxis.set_major_locator(plt.MultipleLocator(1)); ax.grid(axis="x", color=RULE); ax.set_axisbelow(True)
ax.legend(loc="lower right", frameon=False, fontsize=10)
fig.text(.02, .955, f"Who owns the {R['wiki']['true_enclaves']} true international enclaves ({R['wiki']['true_parcels']} pieces)", fontsize=12, color=FG)
both(fig, "owners")

# ---------- sizes ----------
G = ["Baarle parcels", "Former India and Bangladesh enclaves", "True enclaves on land", "True enclaves: islands and water", "Exclaves that are not enclaves", "Enclaved countries"]
GC = [GOLD, "#8C8478", HOT, "#E07A70", COOL, "#7B2D8E"]
fig = plt.figure(figsize=(12, 6.2), facecolor=BG); ax = fig.add_axes([.03, .1, .94, .8]); ax.set_facecolor(BG)
rng = np.random.default_rng(3)
for gi, g in enumerate(G):
    v = np.array([s[2] for s in S["sizes"] if s[0] == g and s[2] > 0]); y = len(G) - 1 - gi
    ax.scatter(v, y + rng.uniform(-.17, .17, len(v)) - .12, s=26, c=GC[gi], alpha=.8, ec="#fff", lw=.5, zorder=3)
    ax.text(3.2e-4, y + .25, f"{g} ({len(v)})", fontsize=10.5, color=FG, va="center", fontweight="medium")
ax.set_xscale("log"); ax.set_xlim(3e-4, 1.2e5); ax.set_ylim(-.6, len(G) - .35); ax.set_yticks([])
ax.set_xticks([1e-3, 1e-2, 1, 100, 1e4]); ax.set_xticklabels(["1,000 m²", "1 ha", "1 km²", "100 km²", "10,000 km²"])
ax.grid(axis="x", color=RULE); ax.set_axisbelow(True)
for s_ in ("top", "right", "left"): ax.spines[s_].set_visible(False)
bh = R["baarle"]["smallest_m2"] / 1e6
ax.text(bh / 1.35, len(G) - 1 - .12, "H7", fontsize=9.5, color=FG, ha="right", va="center", fontweight="medium")
ax.text(R["wiki"]["lesotho_km2"] / 1.4, -.12, "Lesotho", fontsize=9.5, color=FG, ha="right", va="center", fontweight="medium")
ax.text(R["chhits"]["dk_m2"] / 1e6, len(G) - 2 + .42, "", fontsize=9)
fig.text(.02, .945, "Area of every enclave and exclave with an area in the sources (log scale)", fontsize=12, color=FG)
both(fig, "sizes")

# ---------- neighbours and tripoints ----------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 6.4), facecolor=BG); fig.subplots_adjust(left=.13, right=.97, wspace=.52, top=.88, bottom=.08)
for ax, rows, col, t, mx in ((a1, R["nei"]["top"][:14], COOL, "Neighbours (land borders)", 16), (a2, R["tri"]["top"][:14], NAVY, "Tripoints", 18)):
    ax.set_facecolor(BG); nm = [r["name"] for r in rows][::-1]; v = [r["n"] for r in rows][::-1]; w = [r["wiki"] for r in rows][::-1]
    ax.barh(nm, v, color=col, height=.68)
    for i, (vv, ww) in enumerate(zip(v, w)):
        if ww is not None and ww >= 0: ax.plot([ww, ww], [i - .38, i + .38], color=FG, lw=2.2)
        ax.text(max(vv, ww or 0) + .3, i, str(vv), va="center", fontsize=9.5)
    ax.set_xlim(0, mx); ax.xaxis.set_major_locator(plt.MultipleLocator(2)); ax.set_title(t, loc="left", fontsize=12, color=FG); spines(ax); ax.tick_params(axis="y", length=0, labelsize=10)
fig.text(.02, .955, "Natural Earth 1:10m (bars) against Wikipedia's tables (black ticks); dependencies count with their sovereign", fontsize=11, color=FG)
both(fig, "neighbours")

# ---------- landlocked ----------
LL = set(R["land"]["names"]); DL = set(R["land"]["doubly"])
CTB = pd.read_csv(f"{DATA}/countries_borders.csv").set_index("unit")
LLU = set(CTB[CTB.landlocked == 1].index); DLU = set(CTB[CTB.doubly_landlocked == 1].index)
ONEU = set(CTB[CTB.n_neighbours == 1].index)
def fc(adm, sov):
    u = {"PSE": "PSX"}.get(adm, adm if adm in CTB.index else sov)
    if adm == "PSX": u = "PSX"
    if u in DLU: return HOT
    if u in LLU: return "#E8A33A"
    if u in ONEU: return "#9DB8DC"
    return LAND
fig = plt.figure(figsize=(12, 6.8), facecolor=BG); ax = fig.add_axes([0, .07, 1, .82])
outline(ax, fc=SEA, ec="#C9CDD0"); world(ax, ec=BG, fc_of=fc)
for nm_, lon, lat, dx, dy, ha in (("Liechtenstein", 9.55, 47.15, -3.0e6, -.9e6, "right"), ("Uzbekistan", 64.5, 41.5, 0, 1.6e6, "center")):
    x, y = proj(lon, lat); ax.annotate(nm_, (x, y), xytext=(x + dx, y + dy), fontsize=10, color=HOT, ha=ha, fontweight="medium",
                                       arrowprops=dict(arrowstyle="-", color=HOT, lw=.8), path_effects=HALO)
fig.text(.02, .975, f"{R['land']['n']} landlocked countries, {R['land']['n_doubly']} of them doubly landlocked, and the {R['nei']['n_one']} countries\nwith only one neighbour (Natural Earth; the Caspian counted as a lake)", fontsize=11, color=FG, va="top", linespacing=1.4)
fig.legend(handles=[Patch(color=HOT, label="doubly landlocked"), Patch(color="#E8A33A", label="landlocked"), Patch(color="#9DB8DC", label="one neighbour, with a coast")],
           loc="lower center", ncol=3, frameon=False, fontsize=10, bbox_to_anchor=(.5, 0))
both(fig, "landlocked")

# ---------- Baarle parcels (paper only) ----------
B = pd.read_csv(f"{DATA}/baarle_parcels.csv").sort_values("area_m2")
fig = plt.figure(figsize=(11, 4.6), facecolor=BG); ax = fig.add_axes([.07, .2, .9, .7]); ax.set_facecolor(BG)
ax.bar(range(len(B)), B.area_m2 / 1e4, color=[HOT if c == "Belgium" else COOL for c in B.country])
ax.set_yscale("log"); ax.set_xticks(range(len(B))); ax.set_xticklabels(B.parcel, rotation=90, fontsize=8.5); spines(ax); ax.set_ylabel("hectares (log)")
ax.legend(handles=[Patch(color=HOT, label="Belgian parcel in the Netherlands"), Patch(color=COOL, label="Dutch parcel")], frameon=False, loc="upper left", fontsize=9.5)
both(fig, "baarle", blog=False)

# ---------- header card 1200 x 630 ----------
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
ax = fig.add_axes([.36, .12, .64, .8]); outline(ax, fc=SEA, ec="#C9CDD0", lw=.6); world(ax, lw=.2, ec=BG)
tri_marker(ax, [t[1] for t in TRI], [t[0] for t in TRI], s=6); odd_points(ax, s=14)
fig.text(.04, .86, "The world's", fontproperties=DISP, fontsize=46, color=FG, va="top")
fig.text(.04, .72, "strangest", fontproperties=DISP, fontsize=58, color=HOT, va="top")
fig.text(.04, .55, "borders", fontproperties=DISP, fontsize=58, color=FG, va="top")
fig.text(.04, .36, f"{R['wiki']['true_enclaves']} true enclaves in {R['wiki']['true_parcels']} pieces,\n{R['tri']['n']} tripoints, a quadripoint that is not,\nand an island that changes hands\nevery six months.", fontproperties=SERP, fontsize=14, color=FG, va="top", linespacing=1.35)
fig.text(.04, .04, "maps.tristanhotham.com/border-oddities", fontsize=11, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG)
plt.close(fig)
print("figures done", sorted(os.listdir(BL)), sorted(x for x in os.listdir(PA) if x.endswith(".png")))
