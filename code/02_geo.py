"""Natural Earth 1:10m geometry: neighbours, border lengths, tripoints, exclaves and landlocked countries.

Units. Each Natural Earth admin-0 feature is assigned to a country unit (common.py): its sovereignty group (SOV_A3), with
Palestine kept separate; indeterminate zones (the Cyprus buffer zone, Brazilian Island, the Siachen Glacier, the
Southern Patagonian Ice Field, Bir Tawil and some reefs) are zones, not countries.

Topology. Natural Earth's countries share their boundary vertices exactly, so every polygon edge (a pair of consecutive
vertices, rounded to 1e-7 degrees) is recorded with the units on its two sides:
  * an edge with two different units is land border between them (length: geodesic, WGS84);
  * an edge with one unit is coast, unless it lies on the shore of water enclosed by land (a hole in the union of all
    land, such as the Caspian or Aral Sea), when it is lake shore;
  * an edge between a unit and a zone is zone border.
A tripoint is a vertex on the boundary of three or more units. A quadripoint near miss is a pair of tripoints less
than 5 km apart that between them involve four units.

Parts and exclaves. The polygons of a unit are joined into parts wherever they share an edge (touching at a single point
does not join them). The main part is the largest part holding polygons of the unit's main feature, unless the part
holding its capital is at least half that size, in which case it is the capital's part (Peninsular Malaysia, not
Malaysian Borneo; Jutland, not Zealand). Every other part that shares land border with another unit is an exclave:
  * enclave: no sea coast and one neighbour;  * landlocked exclave: no sea coast, two or more neighbours;
  * coastal exclave: sea coast, on a continental landmass (over 2 million km2 of contiguous land);
  * part of a shared island: sea coast, on a smaller landmass shared with another unit.
Landlocked: no sea coast. Doubly landlocked: landlocked, and every neighbour landlocked too."""
from collections import defaultdict
import numpy as np
from shapely.geometry import shape, Polygon, Point, mapping
from shapely.ops import unary_union
from shapely.prepared import prep
from pyproj import Geod
from common import *

GD = Geod(ellps="WGS84")
F = jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]
CHK = {"features": len(F)}


def unit_of(p):
    a = p["ADM0_A3"]
    if a in ZONES: return "Z:" + a
    return UNIT_FIX.get(a, p["SOV_A3"])


UN = {}          # unit -> display name
FEAT = []        # (adm0, unit, props)
for f in F:
    p = f["properties"]; u = unit_of(p); FEAT.append((p["ADM0_A3"], u, p))
    if u.startswith("Z:"): UN[u] = ZONES[u[2:]]
    elif u not in UN or p["ADM0_A3"] == PRIMARY.get(u, u):
        UN[u] = UNIT_NAME.get(u, UNIT_NAME.get(p["ADM0_A3"], p["NAME_LONG"] if len(p["NAME_LONG"]) < 30 else p["NAME"]))
UN.update({k: v for k, v in UNIT_NAME.items() if k in UN})

# ---------- polygons and edges ----------
K = lambda x, y: (round(x, 7), round(y, 7))
POLY = []        # dict(unit, adm, geom, area_km2)
EDGE = defaultdict(list)     # (k1, k2) sorted -> [poly ids]
VERT = defaultdict(set)      # k -> units
for i, f in enumerate(F):
    adm, u, p = FEAT[i]
    g = shape(f["geometry"]); gs = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    for q in gs:
        pid = len(POLY)
        a, _ = GD.geometry_area_perimeter(q)
        POLY.append({"unit": u, "adm": adm, "geom": q, "area": abs(a) / 1e6})
        for ring in [q.exterior] + list(q.interiors):
            cs = [K(x, y) for x, y in ring.coords]
            for k1, k2 in zip(cs[:-1], cs[1:]):
                if k1 == k2: continue
                EDGE[(k1, k2) if k1 < k2 else (k2, k1)].append(pid)
                VERT[k1].add(u)
CHK["polygons"] = len(POLY); CHK["edges"] = len(EDGE); CHK["vertices"] = len(VERT)
over = sum(1 for v in EDGE.values() if len(v) > 2)
CHK["edges_in_3plus_polygons"] = over

ek = list(EDGE.keys())
A = np.array([[e[0][0], e[0][1], e[1][0], e[1][1]] for e in ek])
_, _, LEN = GD.inv(A[:, 0], A[:, 1], A[:, 2], A[:, 3])
LEN = LEN / 1000.0
ELEN = dict(zip(ek, LEN))

# ---------- enclosed water: holes in the union of all land ----------
land = unary_union([p["geom"] for p in POLY])
holes = [Polygon(r) for g in (land.geoms if land.geom_type == "MultiPolygon" else [land]) for r in g.interiors]
holes = [h for h in holes if h.is_valid and h.area > 0]
CHK["land_holes"] = len(holes)
big = sorted(holes, key=lambda h: -h.area)[:5]
CHK["largest_holes_centroids"] = [[round(h.centroid.x, 1), round(h.centroid.y, 1), round(abs(GD.geometry_area_perimeter(h)[0]) / 1e6)] for h in big]
HOLE = prep(unary_union([h.buffer(1e-6) for h in holes]))

# ---------- classify edges ----------
SEA, LAKE, INTERNAL = "sea", "lake", "internal"
etype = {}
pair_len = defaultdict(float)
zone_len = defaultdict(float)
coast = defaultdict(lambda: {"sea": 0.0, "lake": 0.0})
for e, pids in EDGE.items():
    us = sorted({POLY[i]["unit"] for i in pids})
    L = ELEN[e]
    if len(pids) == 1:
        mx, my = (e[0][0] + e[1][0]) / 2, (e[0][1] + e[1][1]) / 2
        t = LAKE if HOLE.contains(Point(mx, my)) else SEA
        etype[e] = t; coast[us[0]][t] += L
    elif len(us) == 1:
        etype[e] = INTERNAL
    else:
        real = [u for u in us if not u.startswith("Z:")]
        if len(real) == 2:
            pair_len[tuple(real)] += L; etype[e] = "border"
        elif len(real) == 1:
            zone_len[(real[0], [u for u in us if u.startswith("Z:")][0])] += L; etype[e] = "zone"
        else:
            etype[e] = "zone"
CHK["sea_km"] = round(sum(c["sea"] for c in coast.values())); CHK["lake_km"] = round(sum(c["lake"] for c in coast.values()))
CHK["border_km_total"] = round(sum(pair_len.values()))

NEI = defaultdict(set)
for (a, b), L in pair_len.items():
    NEI[a].add(b); NEI[b].add(a)
ZNEI = defaultdict(set)
for (a, z), L in zone_len.items():
    ZNEI[a].add(z)

# ---------- tripoints ----------
TRI = []
for k, us in VERT.items():
    if len(us) >= 3:
        real = sorted(u for u in us if not u.startswith("Z:"))
        TRI.append({"lon": k[0], "lat": k[1], "units": sorted(us), "real": real, "zone": int(len(real) < len(us)), "n": len(us)})
TRI_C = [t for t in TRI if len(t["real"]) >= 3 and not t["zone"]]
CHK["tripoints_all"] = len(TRI); CHK["tripoints_countries"] = len(TRI_C)
CHK["multi4"] = [t for t in TRI if t["n"] >= 4]
TPC = defaultdict(int)
for t in TRI_C:
    for u in t["real"]: TPC[u] += 1


def gdist(a, b):
    return GD.inv(a["lon"], a["lat"], b["lon"], b["lat"])[2]


NEAR = []
tc = np.array([[t["lon"], t["lat"]] for t in TRI])
for i, a in enumerate(TRI):
    d = np.hypot(tc[:, 0] - a["lon"], (tc[:, 1] - a["lat"]))
    for j in np.where((d < .06) & (np.arange(len(TRI)) > i))[0]:
        b = TRI[j]; s = set(a["units"]) | set(b["units"])
        if len(s) >= 4:
            NEAR.append({"units": sorted(s), "m": round(gdist(a, b)), "a": [a["lon"], a["lat"]], "b": [b["lon"], b["lat"]]})
NEAR.sort(key=lambda r: r["m"])

# ---------- parts ----------
par = list(range(len(POLY)))


def find(i):
    while par[i] != i:
        par[i] = par[par[i]]; i = par[i]
    return i


lpar = list(range(len(POLY)))


def lfind(i):
    while lpar[i] != i:
        lpar[i] = lpar[lpar[i]]; i = lpar[i]
    return i


for e, pids in EDGE.items():
    if len(pids) >= 2:
        for q in pids[1:]:
            ra, rb = lfind(pids[0]), lfind(q)
            if ra != rb: lpar[ra] = rb
            if POLY[pids[0]]["unit"] == POLY[q]["unit"]:
                ra, rb = find(pids[0]), find(q)
                if ra != rb: par[ra] = rb
LMA = defaultdict(float)
for i, p in enumerate(POLY): LMA[lfind(i)] += p["area"]
PART = defaultdict(list)
for i, p in enumerate(POLY): PART[(p["unit"], find(i))].append(i)
pinfo = {}
for (u, r), ids in PART.items():
    pinfo[(u, r)] = {"unit": u, "ids": ids, "area": sum(POLY[i]["area"] for i in ids), "adms": sorted({POLY[i]["adm"] for i in ids}),
                     "landmass": LMA[lfind(ids[0])], "nei": defaultdict(float), "sea": 0.0, "lake": 0.0, "zone": defaultdict(float)}
for e, pids in EDGE.items():
    t = etype[e]
    if t == INTERNAL: continue
    for i in pids:
        u = POLY[i]["unit"]; pi = pinfo[(u, find(i))]
        if t in (SEA, LAKE): pi[t] += ELEN[e]
        else:
            for j in pids:
                v = POLY[j]["unit"]
                if v == u: continue
                (pi["zone"] if v.startswith("Z:") else pi["nei"])[v] += ELEN[e]

# capitals
PP = jload(f"{GEO}/ne_10m_populated_places_simple.geojson")["features"]
CAP = {}
for f in PP:
    p = f["properties"]
    if p.get("adm0cap") == 1:
        a = p.get("adm0_a3"); pop = p.get("pop_max") or 0
        if a not in CAP or pop > CAP[a][2]: CAP[a] = (p["longitude"], p["latitude"], pop, p["name"])
CAP["PSX"] = CAP.get("PSX") or CAP.get("PSE")
MAIN = {}
units = sorted({p["unit"] for p in POLY if not p["unit"].startswith("Z:")})
for u in units:
    prim = PRIMARY.get(u, u)
    ps = [k for k in pinfo if k[0] == u]
    cand = [k for k in ps if prim in pinfo[k]["adms"]] or ps
    big = max(cand, key=lambda k: pinfo[k]["area"])
    m = big
    c = CAP.get(prim)
    if c:
        pt = Point(c[0], c[1])
        for k in ps:
            if any(POLY[i]["geom"].buffer(.02).contains(pt) for i in pinfo[k]["ids"]):
                if k != big and pinfo[k]["area"] >= .5 * pinfo[big]["area"]: m = k
                break
    MAIN[u] = m

EXC = []
for k, pi in pinfo.items():
    u = k[0]
    if u.startswith("Z:") or MAIN.get(u) == k or not pi["nei"]:
        continue
    sea = pi["sea"] > 0.05
    if not sea and len(pi["nei"]) == 1: typ = "enclave"
    elif not sea: typ = "landlocked exclave"
    elif pi["landmass"] > 2e6: typ = "coastal exclave"
    else: typ = "part of a shared island"
    big_i = max(pi["ids"], key=lambda i: POLY[i]["area"])
    geom = unary_union([POLY[i]["geom"] for i in pi["ids"]])
    rp = geom.representative_point()
    EXC.append({"unit": u, "name": UN[u], "adm": pi["adms"], "type": typ, "area_km2": round(pi["area"], 2), "neighbours": sorted(pi["nei"]),
                "neighbour_names": [UN[v] for v in sorted(pi["nei"])], "border_km": round(sum(pi["nei"].values()), 1),
                "sea_km": round(pi["sea"], 1), "lake_km": round(pi["lake"], 1), "landmass_km2": round(pi["landmass"]),
                "lon": round(rp.x, 4), "lat": round(rp.y, 4), "bbox": [round(v, 4) for v in geom.bounds], "geom": geom})
EXC.sort(key=lambda r: -r["area_km2"])
CHK["exclave_parts"] = len(EXC)

# ---------- per-country table ----------
CT = []
for u in units:
    sea = coast[u]["sea"]
    CT.append({"unit": u, "name": UN[u], "n_neighbours": len(NEI[u]), "neighbours": sorted(NEI[u]), "neighbour_names": sorted(UN[v] for v in NEI[u]),
               "land_border_km": round(sum(L for (a, b), L in pair_len.items() if u in (a, b)), 1), "sea_coast_km": round(sea, 1),
               "lake_shore_km": round(coast[u]["lake"], 1), "zones": sorted(UN[z] for z in ZNEI[u]), "tripoints": TPC.get(u, 0),
               "landlocked": int(sea < 0.05 and u != "ATA"), "exclave_parts": sum(1 for e in EXC if e["unit"] == u),
               "area_km2": round(sum(pinfo[k]["area"] for k in pinfo if k[0] == u)), "parts": sum(1 for k in pinfo if k[0] == u),
               "main_part_km2": round(pinfo[MAIN[u]]["area"])})
LL = {c["unit"] for c in CT if c["landlocked"] and c["n_neighbours"] > 0}
for c in CT:
    c["doubly_landlocked"] = int(c["unit"] in LL and all(v in LL for v in c["neighbours"]))
    c["landlocked_neighbours"] = sum(v in LL for v in c["neighbours"])

# ---------- page and figure geometry ----------
def rnd(c, k=4):
    if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
        return [round(c[0], k), round(c[1], k)]
    return [rnd(x, k) for x in c]


def feat(geom, props, tol, k):
    g = geom.simplify(tol, preserve_topology=True) if tol else geom
    if g.is_empty: return None
    m = mapping(g)
    return {"type": "Feature", "properties": props, "geometry": {"type": m["type"], "coordinates": rnd(m["coordinates"], k)}}


# world fill for the page: 10m, lightly simplified, one feature per unit (polygons grouped, not dissolved)
byu = defaultdict(list)
for p in POLY:
    if p["unit"] != "ATA" or p["area"] > 5000: byu[p["unit"]].append(p["geom"])
wf = []
from shapely.geometry import MultiPolygon
for u, gs in byu.items():
    keep = [g.simplify(.012, preserve_topology=True) for g in gs]
    keep = [g for g in keep if not g.is_empty and g.area > 3e-4]
    if not keep: continue
    mp = MultiPolygon([g for g in keep if g.geom_type == "Polygon"])
    f_ = feat(mp, {"u": u, "n": UN[u], "z": int(u.startswith("Z:"))}, 0, 3)
    if f_: wf.append(f_)
jsave({"type": "FeatureCollection", "features": wf}, f"{DATA}/world.json")

# border lines (shared edges) for the page, merged into lines per pair
from shapely.geometry import MultiLineString
from shapely.ops import linemerge
segs = defaultdict(list)
for e, t in etype.items():
    if t in ("border", "zone"):
        us = sorted({POLY[i]["unit"] for i in EDGE[e]})
        segs["|".join(us)].append((e[0], e[1]))
bl = []
for key, ss in segs.items():
    ml = linemerge(MultiLineString(ss))
    g = ml.simplify(.006, preserve_topology=False)
    m = mapping(g)
    bl.append({"type": "Feature", "properties": {"p": key, "z": int("Z:" in key)}, "geometry": {"type": m["type"], "coordinates": rnd(m["coordinates"], 3)}})
jsave({"type": "FeatureCollection", "features": bl}, f"{DATA}/borders.json")

# exclave parts at full 10m detail
ef = [feat(e["geom"], {"unit": e["unit"], "name": e["name"], "type": e["type"], "area": e["area_km2"], "nb": ", ".join(e["neighbour_names"])}, 0, 5) for e in EXC]
jsave({"type": "FeatureCollection", "features": [f for f in ef if f]}, f"{DATA}/ne_exclaves.geojson")

# full-detail polygons kept in WORK for the figures and insets
import pickle
pickle.dump({"poly": [(p["unit"], p["adm"], p["geom"]) for p in POLY], "names": UN}, open(f"{WORK}/ne_poly.pkl", "wb"))

for e in EXC: e.pop("geom")
out = {"countries": CT, "pairs": [{"a": a, "b": b, "km": round(L, 2)} for (a, b), L in sorted(pair_len.items(), key=lambda x: -x[1])],
       "zones": [{"unit": a, "zone": z, "km": round(L, 2)} for (a, z), L in zone_len.items()],
       "tripoints": TRI, "near": NEAR[:20], "exclaves": EXC, "names": UN, "checks": CHK,
       "capitals": {k: list(v) for k, v in CAP.items() if v and k in {PRIMARY.get(u, u) for u in units}}}
jsave(out, f"{WORK}/ne.json")
print({k: v for k, v in CHK.items() if k != "multi4"}, "multi4:", len(CHK["multi4"]))
top = sorted(CT, key=lambda c: -c["n_neighbours"])[:10]
print([(c["name"], c["n_neighbours"]) for c in top])
print("tripoint leaders", sorted(((UN[u], n) for u, n in TPC.items()), key=lambda x: -x[1])[:8])
print("doubly", [c["name"] for c in CT if c["doubly_landlocked"]], "landlocked", len(LL))
print("one neighbour", [c["name"] for c in CT if c["n_neighbours"] == 1])
print("near", NEAR[:4])
for e in EXC[:60]: print(e["name"], e["type"], e["area_km2"], e["neighbour_names"], e["lat"], e["lon"])
