"""House style for static figures: fonts (static instances cut from the variable Fraunces in /home/claude/ref/fonts,
written to WORK), the palette, Natural Earth outlines in the Equal Earth projection, and inset maps from the 1:10m
polygons kept by 02_geo.py."""
import pickle
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
import numpy as np
from pyproj import Transformer
from shapely.geometry import box, shape
from common import *

FD = os.path.join(WORK, "fonts"); os.makedirs(FD, exist_ok=True)
if not os.path.exists(f"{FD}/Fraunces-Black.ttf"):
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    for w, nm in ((900, "Black"), (700, "Bold")):
        instancer.instantiateVariableFont(TTFont(f"{FONTS}/FrauncesVar.ttf"), {"wght": w, "opsz": 144, "SOFT": 0, "WONK": 0}).save(f"{FD}/Fraunces-{nm}.ttf")
DISP = fm.FontProperties(fname=f"{FD}/Fraunces-Black.ttf")
DISPB = fm.FontProperties(fname=f"{FD}/Fraunces-Bold.ttf")
SERP = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-Regular.ttf")
SERB = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-Semibold.ttf")
for f in ("IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf"):
    fm.fontManager.addfont(f"{FONTS}/{f}")
MONO = "IBM Plex Mono"
plt.rcParams.update({"font.family": MONO, "font.size": 12, "axes.edgecolor": "#636A72", "axes.labelcolor": "#1D2128",
                     "xtick.color": "#636A72", "ytick.color": "#636A72"})
BG, FG, MUT, LAND, RULE, SEA = "#F6F4EF", "#1D2128", "#636A72", "#E2DED3", "#DDD8CC", "#EEF1F2"
HOT, COOL, NAVY, GOLD = "#C8322B", "#2F5FA7", "#1F2F4D", "#E0A11B"
LINE = "#A39A8B"

EE = Transformer.from_crs(4326, 8857, always_xy=True)
W50 = jload(f"{GEO}/ne_50m_admin_0_countries.geojson")
SHAPES = []
for f in W50["features"]:
    g = f["geometry"]; cs = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for poly in cs:
        ring = np.array(poly[0])
        x, y = EE.transform(np.clip(ring[:, 0], -179.9, 179.9), np.clip(ring[:, 1], -89.5, 89.5))
        SHAPES.append((f["properties"]["ADM0_A3"], f["properties"]["SOV_A3"], np.column_stack([x, y])))
WORLD_EXT = (-17.0e6, 17.0e6, -8.75e6, 8.7e6)


def world(ax, lw=.3, ext=WORLD_EXT, ec="#FFFFFF", land=LAND, z=1, skip_ata=True, fc_of=None):
    for adm, sov, p in SHAPES:
        if skip_ata and adm == "ATA":
            continue
        fc = fc_of(adm, sov) if fc_of else land
        ax.add_patch(MPoly(p, closed=True, fc=fc or land, ec=ec, lw=lw, zorder=z))
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.axis("off")


def outline(ax, fc=None, lw=.8, ec=MUT, z=0):
    """Equal Earth globe outline."""
    lat = np.linspace(-90, 90, 181)
    xl, yl = EE.transform(np.full_like(lat, -180), lat); xr, yr = EE.transform(np.full_like(lat, 180), lat[::-1])
    ax.add_patch(MPoly(np.column_stack([np.r_[xl, xr], np.r_[yl, yr]]), closed=True, fc=fc or "none", ec=ec, lw=lw, zorder=z))


def proj(lon, lat):
    return EE.transform(np.asarray(lon), np.asarray(lat))


def spines(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


_P = None


def ne10():
    global _P
    if _P is None:
        _P = pickle.load(open(f"{WORK}/ne_poly.pkl", "rb"))
    return _P


def inset_ax(ax, t, own_col=HOT, land=LAND, sea=SEA, ec="#FFFFFF", lw=.6, label=True, fs=8.5):
    """Draw a tour stop's inset box (Natural Earth 1:10m) on ax, in plate carree scaled by cos(lat)."""
    P = ne10(); x0, y0, x1, y1 = t["inset"]["bb"]; c = np.cos(np.radians((y0 + y1) / 2))
    bb = box(x0, y0, x1, y1); own = set(t["own"])
    ax.set_facecolor(sea)
    pieces = []
    for u, adm, g in P["poly"]:
        if not g.intersects(bb): continue
        q = g.intersection(bb)
        for p in (q.geoms if hasattr(q, "geoms") else [q]):
            if p.geom_type == "Polygon" and not p.is_empty: pieces.append((p.area, u, p))
    for _, u, p in sorted(pieces, key=lambda x: -x[0]):          # largest first, so enclaves sit on top of the land around them
        xy = np.array(p.exterior.coords)
        fc = own_col if u in own else ("#5E5A54" if u == "Z:BRT" else "#B9B2A4" if u.startswith("Z:") else land)
        ax.add_patch(MPoly(np.column_stack([xy[:, 0] * c, xy[:, 1]]), closed=True, fc=fc, ec=ec, lw=lw, alpha=.6 if (u in own or u == "Z:BRT") else 1, zorder=1))
    ax.set_xlim(x0 * c, x1 * c); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color("#C9C2B6"); s.set_linewidth(.8)
    import matplotlib.patheffects as pe
    for p in t["pts"]:
        la, lo, nm = p[0], p[1], p[2]; left = len(p) > 3 and p[3] == "l"
        ax.scatter([lo * c], [la], s=22, c=FG, ec="#fff", lw=1, zorder=5)
        if label:
            ax.text(lo * c + (-1 if left else 1) * (x1 - x0) * c * .035, la, nm, ha="right" if left else "left", va="center", fontsize=fs, color=FG,
                    zorder=6, path_effects=[pe.withStroke(linewidth=3, foreground=sea)])
