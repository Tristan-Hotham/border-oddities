"""Every number used anywhere (data/results.json), the data tables (data/*.csv), and the page data (data/site.json).

The catalogue of oddities (data/oddities.csv) has one row per mapped place:
  * the national-level Wikipedia table entries (true enclaves, enclaved countries, exclaves, former enclaves), placed
    by the table's own coordinates; pockets of high seas are left out (they are water);
  * the national-level list items (semi-enclaves and semi-exclaves, pene-exclaves, divided islands), placed by
    coordinates written in the item, by the infobox of the article about the place, or by the Natural Earth part that
    is the place (its representative point); items that cannot be placed this way are kept, unmapped;
  * condominiums from the Wikipedia table, placed where a source gives a position; Bir Tawil (terra nullius).
Counts of entries follow the Wikipedia list as it stands (revision ids in results.source.revids)."""
import pickle
import numpy as np, pandas as pd
from shapely.geometry import Point, box, shape
from shapely.ops import unary_union
from common import *

WK = jload(f"{WORK}/wiki.json"); NE = jload(f"{WORK}/ne.json")
T = pd.DataFrame(WK["tables"]); LI = pd.DataFrame(WK["lists"]); IB = WK["infobox"]
CT = pd.DataFrame(NE["countries"]).set_index("unit"); UN = NE["names"]
EXC = NE["exclaves"]
EXG = jload(f"{DATA}/ne_exclaves.geojson")["features"]
for e, f in zip(EXC, EXG): e["shape"] = shape(f["geometry"])
P = pickle.load(open(f"{WORK}/ne_poly.pkl", "rb"))
R = {}
pc = lambda a, b: round(100 * a / b, 1) if b else None

# Wikipedia country names -> Natural Earth unit
ALIAS = {"United States of America": "US1", "United States": "US1", "USA": "US1", "Democratic Republic of the Congo": "COD", "Republic of the Congo": "COG",
         "East Timor": "TLS", "Gambia": "GMB", "The Gambia": "GMB", "Czech Republic": "CZE", "Republic of Ireland": "IRL", "Ivory Coast": "CIV",
         "State of Palestine": "PSX", "Palestine": "PSX", "Hong Kong": "CH1", "Macau": "CH1", "China": "CH1", "France": "FR1", "Netherlands": "NL1",
         "United Kingdom": "GB1", "Denmark": "DN1", "Finland": "FI1", "Australia": "AU1", "New Zealand": "NZ1", "Kazakhstan": "KA1", "Cuba": "CU1",
         "Israel": "IS1", "Dhekelia Sovereign Base Area": "GB1", "Eswatini": "SWZ", "North Macedonia": "MKD", "Vatican City": "VAT", "Russia": "RUS",
         "Bosnia and Herzegovina": "BIH", "South Korea": "KOR", "North Korea": "PRK", "Laos": "LAO", "Vietnam": "VNM", "Syria": "SYR", "Iran": "IRN",
         "Bolivia": "BOL", "Venezuela": "VEN", "Moldova": "MDA", "Brunei": "BRN", "Tanzania": "TZA", "Kosovo": "KOS", "Serbia": "SRB",
         "Northern Cyprus": "CYN", "Taiwan": "TWN", "Western Sahara": "SAH", "South Sudan": "SDS", "Somaliland": "SOL"}
BYNAME = {norm(v): k for k, v in UN.items() if not k.startswith("Z:")}


def unit(name):
    if name in ALIAS: return ALIAS[name]
    return BYNAME.get(norm(name))


def rep(u, lat, lon):
    """Representative point of the Natural Earth exclave part of unit u nearest to (lat, lon)."""
    cand = [e for e in EXC if e["unit"] == u]
    e = min(cand, key=lambda e: (e["lat"] - lat) ** 2 + (e["lon"] - lon) ** 2)
    return e["lat"], e["lon"]


def cap(u):
    return NE["capitals"][PRIMARY.get(u, u)][1], NE["capitals"][PRIMARY.get(u, u)][0]


# ---------- catalogue ----------
REV = WK["revids"]
LISTKEY = "List of enclaves and exclaves"
rows = []
WATERN = {"Apipé Islands (4)", "Isla Entre Ríos", "Isla Martín García", "Torres Strait Islands (7)", "Quitasueño", "Serrana", "Likoma Island",
          "Chizumulu Island (incl Lundu Is., Papia Is., Ngkyvo Is.)", "Laguna Los Portillos (and beach)", "Filomena Islands (5 islands)", "Gulf of Fonseca outer tridominium"}
T["water"] = T.name.isin(WATERN).astype(int)
SHORT = {"Baarle-Hertog (22 parcels)": "Baarle-Hertog", "Baarle-Nassau (8 parcels)": "Baarle-Nassau", "West Kowloon Port ( aka . Mainland Port Area)": "West Kowloon Port",
         "Chizumulu Island (incl Lundu Is., Papia Is., Ngkyvo Is.)": "Chizumulu Island", "Sarvan (also Sarvaksoi, Sarvaki-bolo )": "Sarvan",
         "\" Lolazor \"": "Lolazor", "\"Electricity Authority of Cyprus\" Refugee Settlement": "Electricity Authority refugee settlement",
         "Strovilia ( de facto )": "Strovilia", "Barak ( de facto )": "Barak", "San'kovo-Medvezh'e": "Sankovo-Medvezhye",
         "Chon-Qora or Qalacha (the 2 Uzbek villages in the enclave)": "Chon-Qora and Qalacha", "Jangail (also Jangy-ayyl ) or \"Tash-Dobo\"": "Jangail",
         "Indo-Bangladesh enclaves (91 parcels)": "Bangladeshi enclaves in India (to 2015)", "Indo-Bangladesh enclaves (106 parcels)": "Indian enclaves in Bangladesh (to 2015)",
         "Nakhchivan Autonomous Republic": "Nakhchivan", "Dahagram-Angarpota": "Dahagram-Angarpota", "Gaza Strip (de jure)": "Gaza Strip",
         "Yaradullu (north and south)": "Yaradullu", "Laguna Los Portillos (and beach)": "Laguna Los Portillos", "Filomena Islands (5 islands)": "Filomena Islands",
         "Apipé Islands (4)": "Apipé Islands", "Torres Strait Islands (7)": "Torres Strait Islands", "Brezovica Žumberačka (2)": "Brezovica Žumberačka",
         "Karki / Tigranashen": "Karki (Tigranashen)"}
TL = T[(T.maritime == 0)].copy()
TL = TL[~TL.name.str.startswith("Tarchen")]       # Bhutan's former Tibetan enclaves: no coordinates
for r in TL.itertuples():
    rows.append({"name": SHORT.get(r.name, r.name), "kind": r.kind, "sub": {"enclave": "enclave and exclave", "enclaved_country": "enclaved country",
                 "exclave": "exclave, not an enclave", "historic": "former enclave"}[r.kind], "owner": r.owner, "within": r.within,
                 "area_km2": r.area_km2, "parcels": r.parcels, "water": r.water, "de_facto": r.de_facto, "lat": r.lat, "lon": r.lon,
                 "coord_src": "Wikipedia list table", "article": LISTKEY, "existed": r.existed, "text": r.notes[:400]})
# list items: where to put each one
PLACE = [  # (regex on the item text, list of placements)
    (r"^Brunei : Surrounded", [("cap", "BRN")]), (r"^Gambia : Surrounded", [("cap", "GMB")]), (r"^Monaco : Surrounded", [("cap", "MCO")]),
    (r"Temburong", [("ne", "BRN", 4.6, 115.2)]), (r"Oecusse", [("ne", "TLS", -9.3, 124.2)]), (r"Musandam is bounded", [("ib", "Musandam Governorate")]),
    (r"^Spain : Ceuta", [("ib", "Ceuta"), ("ib", "Melilla")]), (r"Gibraltar is on the south coast", [("ne", "GB1", 36.13, -5.35)]),
    (r"^Akrotiri and Dhekelia", [("ne", "GB1", 34.64, 32.94), ("ne", "GB1", 35.03, 33.76)]), (r"Alaska is bounded", [("ne", "US1", 63, -152)]),
    (r"Cabinda is bounded", [("ne", "AGO", -5.1, 12.3)]), (r"Dubrovnik", [("ne", "HRV", 42.7, 18.0)]), (r"Famagusta", [("ne", "CYP", 35.0, 33.9)]),
    (r"French Guiana", [("ne", "FR1", 3.9, -53.0)]), (r"Kaliningrad Oblast is bounded", [("ib", "Kaliningrad Oblast")]),
    (r"Jungholz", [("ib", "Jungholz")]), (r"Kleinwalsertal", [("ib", "Kleinwalsertal")]), (r"^The Zeelandic Flanders", [("ne", "NL1", 51.3, 3.8)]),
    (r"European section of Turkey", [("ne", "TUR", 41.1, 27.2)]), (r"Northern Ireland is bounded", [("ne", "GB1", 54.6, -6.9)]),
    (r"^Point Roberts", [("ib", "Point Roberts, Washington")]), (r"^The Northwest Angle", [("ib", "Northwest Angle")]),
    (r"Curonian Spit", [("ne", "LTU", 55.5, 21.1)]), (r"Isla Grande de Tierra del Fuego", [("ne", "CHL", -53.7, -69.3)]),
    (r"Borneo 's subdivisions", [("ne", "MYS", 3.9, 114.6)]), (r"Hans Island", [("ib", "Hans Island")]), (r"^Märket", [("ib", "Märket")]),
    (r"Sebatik", [("ne", "MYS", 4.2, 117.7)]), (r"West Papua is surrounded", [("ne", "IDN", -4.7, 138.7)]), (r"Timor island is divided", [("ne", "IDN", -9.7, 124.3)]),
    (r"Usedom", [("ne", "DEU", 54.0, 14.07)]), (r"St. Martin / Sint Maarten", [("ne", "FR1", 18.08, -63.06)])]
LKEY = {"semi": "Semi-enclaves and semi-exclaves", "pene": "Pene-enclaves/exclaves", "divided_island": "Divided islands"}
unplaced = {"semi": 0, "pene": 0, "divided_island": 0}
for r in LI.itertuples():
    pl = []
    if r.lat is not None and r.lat == r.lat:
        pl = [(r.lat, r.lon, "coordinates in the Wikipedia list")]
    else:
        for rx, how in PLACE:
            if re.search(rx, r.text):
                for h in how:
                    if h[0] == "ib": pl.append((IB[h[1]][0], IB[h[1]][1], f"infobox of '{h[1]}'"))
                    elif h[0] == "ne": la, lo = rep(h[1], h[2], h[3]); pl.append((la, lo, "Natural Earth part"))
                    elif h[0] == "cap": la, lo = cap(h[1]); pl.append((la, lo, "Natural Earth capital"))
                break
    label = re.split(r":", r.country_label)[0].strip()
    nm = re.sub(r"\s+", " ", re.split(r" : |: | is | are | – |, a |\(", r.text, maxsplit=1)[0]).strip()
    if r.text.startswith(label + " : ") or r.text.startswith(label + " ("):
        nm = re.split(r" is | are | has | can | lies | contains |, ", r.text.split(" : ", 1)[-1], maxsplit=1)[0].strip()
    if not pl:
        unplaced[r.kind] += 1; pl = [(None, None, "")]
    for la, lo, src in pl:
        rows.append({"name": nm[:70], "kind": r.kind, "sub": r.sub, "owner": label, "within": "", "area_km2": None, "parcels": 1, "water": int(r.kind == "divided_island"),
                     "de_facto": 0, "lat": la, "lon": lo, "coord_src": src, "article": LISTKEY, "existed": "", "text": r.text[:400]})
# names for some placed list items (the item's own wording is long)
NAMEFIX = {r"^Brunei : Surrounded": "Brunei", r"^Gambia": "The Gambia", r"^Monaco": "Monaco", r"Temburong": "Temburong", r"Oecusse": "Oecusse",
           r"Musandam is": "Musandam", r"Gibraltar is": "Gibraltar", r"^Akrotiri": "Akrotiri and Dhekelia", r"Alaska is bounded": "Alaska",
           r"Cabinda is": "Cabinda", r"Dubrovnik": "Dubrovnik and southern Dalmatia", r"Famagusta": "Famagusta (Cyprus)", r"French Guiana": "French Guiana",
           r"Kaliningrad Oblast is": "Kaliningrad", r"municipality of Jungholz": "Jungholz", r"Kleinwalsertal": "Kleinwalsertal",
           r"Zeelandic Flanders": "Zeelandic Flanders", r"European section of Turkey": "East Thrace (Turkey in Europe)", r"Northern Ireland is": "Northern Ireland",
           r"^Point Roberts": "Point Roberts", r"^The Northwest Angle": "Northwest Angle", r"Curonian Spit": "Curonian Spit (Lithuania)",
           r"Tierra del Fuego": "Tierra del Fuego", r"Borneo 's": "Borneo", r"Hans Island": "Hans Island", r"^Märket": "Märket", r"Sebatik": "Sebatik",
           r"West Papua": "New Guinea", r"Timor island": "Timor", r"Usedom": "Usedom", r"St. Martin": "Saint Martin", r"Eritrea : The southeastern": "Ras Doumeira tip (Eritrea)",
           r"Shenzhen Bay": "Shenzhen Bay Control Point", r"Properties 79/3": "Trosterud properties (Norway)", r"Pollatawny": "Pollatawny islet",
           r"Kokkina": "Kokkina", r"Hinterriß": "Hinterriß and Eng", r"Lutepää": "Lutepää", r"Os de Civís": "Os de Civís", r"Macahel": "Macahel valley",
           r"Konstanz": "Konstanz old town", r"Stein am Rhein": "Stein am Rhein", r"Campobello": "Campobello Island", r"Haskell Free Library": "Haskell Free Library",
           r"Elm Point": "Elm Point", r"Estcourt Station": "Estcourt Station", r"Alburgh Tongue": "Alburgh Tongue", r"Livigno": "Livigno",
           r"Ambergris Caye": "Ambergris Caye", r"Copacabana": "Copacabana (Bolivia)", r"Preah Vihear": "Preah Vihear temple", r"Mpalila": "Mpalila Island",
           r"Tornio": "Tornio and Haparanda", r"Kataja": "Kataja Island", r"Koiluoto": "Koiluoto Island", r"Limbang": "Limbang", r"Tourém": "Tourém",
           r"Drummully": "Drummully Polyp", r"Sylt|Vilmkærgård": "Danish and German border farms", r"Columbia River": "Columbia River island",
           r"Province Island": "Province Island", r"Pine and Curry": "Pine and Curry Island", r"Salt Lake": "Salt Lake (Alkali Lake) island",
           r"Boundary Lake": "Boundary Lake islands", r"Maritsa River known as island Q": "Island Q (Maritsa)", r"tripoint junction": "Maritsa tripoint islet",
           r"lake island is divided between North Korea": "Korean lake island", r"river island at 38": "Korean river island"}
for r in rows:
    if r["kind"] in ("semi", "pene", "divided_island"):
        for rx, nm in NAMEFIX.items():
            if re.search(rx, r["text"]):
                r["name"] = nm; break
akro = [r for r in rows if r["name"] == "Akrotiri and Dhekelia"]
if len(akro) == 2: akro[0]["name"], akro[1]["name"] = "Akrotiri", "Dhekelia"
cm = [r for r in rows if r["text"].startswith("Spain : Ceuta")]
if len(cm) == 2: cm[0]["name"], cm[1]["name"] = "Ceuta", "Melilla"

# condominiums and terra nullius
CON = pd.DataFrame(WK["condominiums"])
borders = jload(f"{DATA}/borders.json")["features"]


def mid_border(key):
    f = next(f for f in borders if f["properties"]["p"] == key)
    g = shape(f["geometry"]); p = g.interpolate(.5, normalized=True) if g.geom_type == "LineString" else max(g.geoms, key=lambda q: q.length).interpolate(.5, normalized=True)
    return p.y, p.x


fon = T[T.name == "Gulf of Fonseca outer tridominium"].iloc[0]
COND_POS = {"Pheasant Island": (IB["Isla de los Faisanes"][0], IB["Isla de los Faisanes"][1], "infobox of 'Pheasant Island'"),
            "Gulf of Fonseca": (fon.lat, fon.lon, "Wikipedia list table (outer tridominium)"),
            "Brčko District": (44.8305, 18.854, "Natural Earth admin-1 label point"),
            "Moselle": mid_border("DEU|LUX") + ("midpoint of the Natural Earth Germany and Luxembourg border",)}
for c in CON.itertuples():
    la, lo, src = COND_POS.get(c.name, (None, None, ""))
    rows.append({"name": c.name, "kind": "condominium", "sub": "condominium", "owner": c.states, "within": "", "area_km2": c.area_km2, "parcels": 1, "water": 0,
                 "de_facto": 0, "lat": la, "lon": lo, "coord_src": src, "article": "Condominium (international law)", "existed": c.created, "text": c.notes})
bt = [e for e in jload(f"{DATA}/world.json")["features"] if e["properties"]["u"] == "Z:BRT"][0]
rows.append({"name": "Bir Tawil", "kind": "nullius", "sub": "terra nullius", "owner": "claimed by neither Egypt nor Sudan", "within": "", "area_km2": 2060, "parcels": 1, "water": 0,
             "de_facto": 0, "lat": IB["Bir Tawil"][0], "lon": IB["Bir Tawil"][1], "coord_src": "infobox of 'Bir Tawil'", "article": "Bir Tawil", "existed": "1902", "text": "Unclaimed land between Egypt and Sudan."})
rows.append({"name": "Gornja Siga and three other pockets", "kind": "nullius", "sub": "terra nullius", "owner": "claimed by neither Croatia nor Serbia", "within": "", "area_km2": None,
             "parcels": 4, "water": 0, "de_facto": 0, "lat": None, "lon": None, "coord_src": "", "article": "Terra nullius", "existed": "", "text": "Four pockets on the western bank of the Danube claimed by neither Croatia nor Serbia."})
O = pd.DataFrame(rows)
O.insert(0, "id", range(1, len(O) + 1))
O["mapped"] = O.lat.notna().astype(int)
O["revid"] = O.article.map(lambda a: REV.get(a, REV.get("Isla de los Faisanes")))

# is it in Natural Earth? (a Natural Earth exclave part within 3 km)
def in_ne(la, lo):
    if la is None or la != la: return 0
    p = Point(lo, la)
    return int(any(e["shape"].buffer(.03).contains(p) for e in EXC))


O["in_natural_earth"] = [in_ne(a, b) for a, b in zip(O.lat, O.lon)]
O.to_csv(f"{DATA}/oddities.csv", index=False)

# ---------- results: the Wikipedia catalogue ----------
TE = TL[TL.kind == "enclave"]
land = TE[TE.water == 0]
R["wiki"] = {"true_enclaves": len(TE), "true_parcels": int(TE.parcels.sum()), "true_land": len(land), "true_water": int(TE.water.sum()),
             "enclaved_countries": int((TL.kind == "enclaved_country").sum()), "exclaves": int((TL.kind == "exclave").sum()),
             "maritime": int(T.maritime.sum()), "historic_rows": int((T.kind == "historic").sum()),
             "semi": int((LI.kind == "semi").sum()), "pene": int((LI.kind == "pene").sum()), "divided": int((LI.kind == "divided_island").sum()),
             "unplaced": unplaced, "subnational_rows": WK["checks"]["subnational_table_rows"],
             "condominiums": len(CON), "mapped": int(O.mapped.sum()), "catalogue_rows": len(O),
             "true_in_ne": int(O[(O.kind == "enclave")].in_natural_earth.sum())}
w = R["wiki"]
w["true_not_in_ne"] = w["true_enclaves"] - w["true_in_ne"]
own = TE.groupby("owner").agg(n=("name", "size"), parcels=("parcels", "sum"), water=("water", "sum")).sort_values(["n", "parcels"], ascending=False)
w["owners"] = [{"owner": k, "n": int(v.n), "parcels": int(v.parcels), "water": int(v.water)} for k, v in own.iterrows()]
w["n_owner_countries"] = len(own)
w["n_within_countries"] = int(TE.within.nunique())
wi = TE.groupby("within").size().sort_values(ascending=False)
w["withins"] = [{"within": k, "n": int(v)} for k, v in wi.items()]
w["top_owner"] = own.index[0]; w["top_owner_n"] = int(own.n.iloc[0])
w["top_parcels_owner"] = own.parcels.idxmax(); w["top_parcels"] = int(own.parcels.max())
sm = land.dropna(subset=["area_km2"]).sort_values("area_km2")
w["smallest_entry"] = SHORT.get(sm.iloc[0]["name"], sm.iloc[0]["name"]); w["smallest_entry_m2"] = round(sm.iloc[0].area_km2 * 1e6)
w["largest_land"] = sm.iloc[-1]["name"]; w["largest_land_km2"] = sm.iloc[-1].area_km2
wat = TE[TE.water == 1].dropna(subset=["area_km2"]).sort_values("area_km2")
w["largest_island"] = SHORT.get(wat[~wat.area_txt.str.contains("water")].iloc[-1]["name"]); w["largest_island_km2"] = wat[~wat.area_txt.str.contains("water")].iloc[-1].area_km2
ec = TL[TL.kind == "enclaved_country"].set_index("name")
w["lesotho_km2"] = ec.loc["Lesotho", "area_km2"]; w["vatican_km2"] = ec.loc["Vatican City", "area_km2"]; w["sanmarino_km2"] = ec.loc["San Marino", "area_km2"]
w["nakhchivan_km2"] = TL.set_index("name").loc["Nakhchivan Autonomous Republic", "area_km2"]
area = TL.set_index("name").area_km2
for k, nm in (("sokh", "Sokh"), ("vorukh", "Vorukh"), ("madha", "Madha"), ("nahwa", "Nahwa"), ("llivia", "Llívia"), ("busingen", "Büsingen am Hochrhein"),
              ("campione", "Campione d'Italia"), ("ruckschlag", "Rückschlag"), ("sankovo", "San'kovo-Medvezh'e"), ("dahagram", "Dahagram-Angarpota"),
              ("jungholz", "Jungholz"), ("baarle_h", "Baarle-Hertog (22 parcels)"), ("baarle_n", "Baarle-Nassau (8 parcels)")):
    w[k + "_km2"] = float(area[nm])
w["kinds"] = {k: int((O.kind == k).sum()) for k in KCOL}
assert w["true_enclaves"] == 42 and w["true_parcels"] == 85 and w["enclaved_countries"] == 3 and w["exclaves"] == 4
assert w["top_owner"] == "Germany" and w["top_parcels_owner"] == "Belgium" and w["largest_land"] == "Sokh" and w["smallest_entry"] == "Rückschlag"

# Baarle and the chhits
B = pd.DataFrame(WK["baarle"]); C = pd.DataFrame(WK["chhits"])
R["baarle"] = {"belgian": int((B.country == "Belgium").sum()), "dutch": int((B.country == "Netherlands").sum()),
               "smallest": B.sort_values("area_m2").iloc[0].parcel, "smallest_m2": int(B.area_m2.min()), "largest": B.sort_values("area_m2").iloc[-1].parcel,
               "largest_ha": round(float(B.area_ha.max()), 1), "houses_split": int(B.houses_split.sum()), "parcels_with_houses": int((B.houses_split > 0).sum()),
               "total_ha": round(float(B.area_ha.sum()), 1), "h1_ha": round(float(B.set_index("parcel").loc["H1", "area_ha"]), 1)}
assert R["baarle"]["smallest"] == "H7" and R["baarle"]["smallest_m2"] == 2469
dk = C[C.name == "Dahala Khagrabari (#51)"].iloc[0]; nat = C[C.name == "Natatoka (#38)"].iloc[0]
R["chhits"] = {"indian": 102, "bangladeshi": 71, "counter_bd": 21, "counter_in": 3, "counter_counter": 1, "people_2010": 51549,
               "to_bangladesh": 111, "to_india": 51, "swap_date": "31 July 2015", "dk_m2": round(dk.area_km2 * 1e6), "natatoka_m2": round(nat.area_km2 * 1e6),
               "table_rows": len(C), "dahagram_km2": float(area["Dahagram-Angarpota"])}
R["chhits"]["total"] = 102 + 71 + 21 + 3 + 1          # stated in the article, checked word for word in 01_wiki.py
assert R["chhits"]["dk_m2"] == 6880 and R["chhits"]["natatoka_m2"] == 1050

# ---------- results: Natural Earth ----------
TRI = NE["tripoints"]
tri3 = [t for t in TRI if t["n"] == 3 and not t["zone"]]
quad = [t for t in TRI if t["n"] >= 4 and not t["zone"]]
tz = [t for t in TRI if t["zone"]]
TPC = {}
for t in tri3 + quad:
    for u in t["real"]: TPC[u] = TPC.get(u, 0) + 1
tl = sorted(TPC.items(), key=lambda x: (-x[1], UN[x[0]]))
WTRI = pd.DataFrame(WK["wiki_tripoints"])
wtc = {}
for c in list(WTRI.c1) + list(WTRI.c2) + list(WTRI.c3):
    u = unit(c)
    if u: wtc[u] = wtc.get(u, 0) + 1
R["tri"] = {"n": len(tri3), "quad": len(quad), "zone": len(tz), "all_vertices": len(TRI), "with_quad": len(tri3) + len(quad),
            "leader": UN[tl[0][0]], "leader_n": tl[0][1], "second": UN[tl[1][0]], "second_n": tl[1][1],
            "top": [{"unit": u, "name": UN[u], "n": n, "wiki": wtc.get(u, 0)} for u, n in tl[:14]],
            "wiki_list": len(WTRI), "wiki_article": 181, "wiki_china": wtc.get("CH1", 0), "wiki_russia": wtc.get("RUS", 0),
            "countries_with": len(TPC), "zero_countries": int(sum(1 for u in CT.index if CT.loc[u, "n_neighbours"] > 0 and TPC.get(u, 0) == 0))}
kz = quad[0]
R["tri"]["kazungula"] = {"lat": kz["lat"], "lon": kz["lon"], "units": [UN[u] for u in kz["real"]]}
assert R["tri"]["leader"] == "China" and set(kz["real"]) == {"BWA", "NAM", "ZMB", "ZWE"} and len(quad) == 1
assert not any(set(p) == {"BWA", "ZMB"} for p in [(q["a"], q["b"]) for q in NE["pairs"]])          # no Botswana and Zambia border in NE

CTr = CT[CT.index != "ATA"].copy()
nb = CTr.sort_values(["n_neighbours", "land_border_km"], ascending=False)
LBW = pd.DataFrame(WK["land_borders"])
wnb = {}
for r in LBW.itertuples():
    u = unit(r.country)
    if u and u not in wnb and r.country not in ("France, Metropolitan",): wnb[u] = r.n_neigh
cmp_ = [(u, int(CT.loc[u, "n_neighbours"]), int(wnb[u])) for u in CTr.index if u in wnb and wnb[u] == wnb[u] and CT.loc[u, "n_neighbours"] + wnb[u] > 0]
R["nei"] = {"top": [{"unit": u, "name": r["name"], "n": int(r.n_neighbours), "km": round(r.land_border_km), "wiki": int(wnb.get(u, -1)) if wnb.get(u) == wnb.get(u) else None}
                    for u, r in nb.head(16).iterrows()],
            "china": int(CT.loc["CH1", "n_neighbours"]), "russia": int(CT.loc["RUS", "n_neighbours"]), "france": int(CT.loc["FR1", "n_neighbours"]),
            "brazil": int(CT.loc["BRA", "n_neighbours"]), "germany": int(CT.loc["DEU", "n_neighbours"]),
            "one": sorted(CTr[CTr.n_neighbours == 1].name), "n_one": int((CTr.n_neighbours == 1).sum()), "n_none": int((CTr.n_neighbours == 0).sum()),
            "n_with": int((CTr.n_neighbours > 0).sum()), "n_units": len(CTr), "cmp_n": len(cmp_), "cmp_same": sum(a == b for _, a, b in cmp_),
            "cmp_diff": [{"name": UN[u], "ne": a, "wiki": b} for u, a, b in cmp_ if a != b],
            "wiki_one": sorted(set(pd.DataFrame(WK["one_neighbour"]).country)), "mean": round(float(CTr[CTr.n_neighbours > 0].n_neighbours.mean()), 1)}
nn = R["nei"]
assert nn["china"] == 14 and nn["russia"] == 14 and nb.iloc[0]["name"] in ("China", "Russia") and nb.iloc[2]["n_neighbours"] < 14
pairs = sorted(NE["pairs"], key=lambda p: -p["km"])
R["borders"] = {"total_km": round(sum(p["km"] for p in pairs)), "n_pairs": len(pairs),
                "longest": [{"a": UN[p["a"]], "b": UN[p["b"]], "km": round(p["km"])} for p in pairs[:8]],
                "shortest": [{"a": UN[p["a"]], "b": UN[p["b"]], "km": round(p["km"], 2)} for p in pairs[-8:]],
                "longest_country": CTr.land_border_km.idxmax(), "longest_country_name": CTr.loc[CTr.land_border_km.idxmax(), "name"],
                "longest_country_km": round(float(CTr.land_border_km.max())), "china_km": round(float(CT.loc["CH1", "land_border_km"])),
                "russia_km": round(float(CT.loc["RUS", "land_border_km"])), "wiki_china_km": 22147, "wiki_russia_km": 20017}
LL = CTr[CTr.landlocked == 1]
R["land"] = {"n": len(LL), "doubly": sorted(CTr[CTr.doubly_landlocked == 1].name), "names": sorted(LL.name),
             "liechtenstein_nb": sorted(CT.loc["LIE", "neighbour_names"]), "uzbekistan_nb": sorted(CT.loc["UZB", "neighbour_names"]),
             "largest": LL.area_km2.idxmax(), "largest_name": LL.loc[LL.area_km2.idxmax(), "name"], "caspian_km2": NE["checks"]["largest_holes_centroids"][0][2],
             "wiki_n": 44, "enclaved": sorted(LL[LL.n_neighbours == 1].name)}
assert R["land"]["doubly"] == ["Liechtenstein", "Uzbekistan"] and R["land"]["enclaved"] == ["Lesotho", "San Marino", "Vatican City"]
assert "Kosovo" in R["land"]["names"] and R["land"]["n"] == 45

# name each Natural Earth part after the catalogue entry of the same owner nearest its representative point (Wikipedia
# names), if one lies inside it and within half the part's width; two parts that Natural Earth separates by water are named here
OMm = O[O.mapped == 1]


def owner_unit(lbl):
    for part in re.split(r"\s*/\s*", lbl):
        u_ = unit(part.strip())
        if u_: yield u_


for e in EXC:
    hits = []
    for r in OMm.itertuples():
        if e["unit"] not in set(owner_unit(r.owner)) or not e["shape"].buffer(.03).contains(Point(r.lon, r.lat)): continue
        d = np.hypot((r.lon - e["lon"]) * np.cos(np.radians(e["lat"])), r.lat - e["lat"]) * 111.2
        if d <= max(25, np.sqrt(e["area_km2"]) / 2): hits.append((d, r.name))
    e["wiki_name"] = min(hits)[1] if hits else ""
    if e["unit"] == "RUS" and e["lat"] < 47: e["wiki_name"] = "Crimea (Natural Earth's de facto line)"
    if e["unit"] == "CAN": e["wiki_name"] = "Canada south and east of the St Lawrence (river drawn as water)"
    for (u_, la_, nm_) in (("CYP", 35.01, "Famagusta and eastern Larnaca (Cyprus)"), ("FR1", 18.08, "Saint-Martin"), ("NL1", 18.04, "Sint Maarten"),
                           ("DEU", 54.01, "Usedom (Germany)"), ("ARG", -53.84, "Tierra del Fuego (Argentina)"), ("IDN", 4.08, "Sebatik (Indonesia)")):
        if e["unit"] == u_ and abs(e["lat"] - la_) < .05: e["wiki_name"] = nm_
for e, f in zip(EXC, EXG):
    f["properties"]["place"] = e["wiki_name"]
jsave({"type": "FeatureCollection", "features": EXG}, f"{DATA}/ne_exclaves.geojson")
E = pd.DataFrame([{k: v for k, v in e.items() if k != "shape"} for e in EXC])
R["ne"] = {"features": NE["checks"]["features"], "polygons": NE["checks"]["polygons"], "edges": NE["checks"]["edges"],
           "exclave_parts": len(E), "types": E.type.value_counts().to_dict(), "units_with": int(E.unit.nunique()),
           "most_unit": E.unit.value_counts().idxmax(), "most_name": UN[E.unit.value_counts().idxmax()], "most_n": int(E.unit.value_counts().max()),
           "largest": E.iloc[0]["name"], "largest_km2": round(float(E.iloc[0].area_km2)), "smallest": E.iloc[-1]["name"], "smallest_km2": float(E.iloc[-1].area_km2),
           "enclaves": [{"name": r["name"], "place": r.wiki_name, "km2": r.area_km2, "within": ", ".join(r.neighbour_names)} for _, r in E[E.type == "enclave"].iterrows()],
           "sokh_km2": float(E[(E.unit == "UZB")].area_km2.max()), "border_km": NE["checks"]["border_km_total"], "sea_km": NE["checks"]["sea_km"]}
assert R["ne"]["largest"] == "United States"
by_u = E.groupby("name").size().sort_values(ascending=False)
R["ne"]["by_unit"] = [{"name": k, "n": int(v)} for k, v in by_u.head(10).items()]
E.drop(columns=["bbox"]).assign(neighbours=E.neighbour_names.map("; ".join)).drop(columns=["neighbour_names"]).rename(columns={"name": "country", "adm": "ne_features"}) \
    .assign(ne_features=lambda d: d.ne_features.map("; ".join)).to_csv(f"{DATA}/ne_exclaves.csv", index=False)

# per-country table and tripoints table
ct = CTr.reset_index().copy()
ct["neighbours"] = ct.neighbour_names.map("; ".join); ct["zones"] = ct.zones.map("; ".join)
ct["tripoints"] = ct.unit.map(lambda u: TPC.get(u, 0)); ct["wikipedia_neighbours"] = ct.unit.map(lambda u: wnb.get(u))
ct.drop(columns=["neighbour_names"]).to_csv(f"{DATA}/countries_borders.csv", index=False)
pd.DataFrame([{"a": UN[p["a"]], "b": UN[p["b"]], "km": p["km"]} for p in pairs]).to_csv(f"{DATA}/border_pairs.csv", index=False)
pd.DataFrame([{"lat": t["lat"], "lon": t["lon"], "countries": "; ".join(UN[u] for u in t["units"]), "n_units": t["n"], "involves_zone": t["zone"]} for t in TRI]) \
    .to_csv(f"{DATA}/tripoints.csv", index=False)

# ---------- derived values used in the text ----------
R["land"]["n_doubly"] = len(R["land"]["doubly"])
w["span_x"] = round(w["lesotho_km2"] * 1e6 / R["baarle"]["smallest_m2"])
w["span_orders"] = round(float(np.log10(w["span_x"])), 1)
assert 1e7 < w["span_x"] < 2e7                                  # "more than ten million times"
w["vennbahn_n"] = int(sum(1 for r in TE.itertuples() if "Vennbahn" in r.notes))
assert w["vennbahn_n"] == 5 and w["top_owner_n"] == 6           # five Vennbahn pieces plus Büsingen
TY = R["ne"]["types"]
R["ne"]["n_enclave"] = TY.get("enclave", 0); R["ne"]["n_coastal"] = TY.get("coastal exclave", 0); R["ne"]["n_island"] = TY.get("part of a shared island", 0)
R["ne"]["n_landlocked"] = TY.get("landlocked exclave", 0)
assert R["ne"]["n_landlocked"] == 1
R["txt"] = {"one_ne": ", ".join(nn["one"]), "landlocked": ", ".join(R["land"]["names"]),
            "ne_enclaves": ", ".join(f"{e['place'] or 'part of ' + e['name']} ({e['name']} in {e['within']})" for e in R["ne"]["enclaves"])}
R["nei"]["second_name"] = nb.iloc[1]["name"]
R["borders"]["vatican_m"] = round(next(p["km"] for p in pairs if {p["a"], p["b"]} == {"ITA", "VAT"}) * 1000)
R["borders"]["gib_m"] = round(next(p["km"] for p in pairs if {p["a"], p["b"]} == {"ESP", "GB1"}) * 1000)
R["borders"]["cus_km"] = round(next(p["km"] for p in pairs if {p["a"], p["b"]} == {"CAN", "US1"}))
R["borders"]["kzru_km"] = round(next(p["km"] for p in pairs if {p["a"], p["b"]} == {"KA1", "RUS"}))
assert R["borders"]["longest"][0]["a"] == "Canada" and R["borders"]["longest"][1]["b"] == "Russia"

LLW = set(WK["landlocked_wiki"]) - {"Transnistria", "South Ossetia"}
LLW = {{"Czech Republic": "Czechia"}.get(x, x) for x in LLW}
assert LLW == set(R["land"]["names"]), (LLW ^ set(R["land"]["names"]))
assert len(LLW) == 44 + 1 and "Kosovo" in LLW        # Wikipedia's 44, plus Kosovo
R["tri"]["by_name"] = {UN[u]: n for u, n in TPC.items()}
R["nei"]["austria"] = int(CT.loc["AUT", "n_neighbours"]); R["nei"]["cmp_diff_n"] = len(R["nei"]["cmp_diff"])
for nm in ("Portugal", "Canada", "United States"):
    assert nm not in R["tri"]["by_name"]
assert R["tri"]["by_name"]["Austria"] == 9 and R["tri"]["by_name"]["DR Congo"] == 9 and int(CT.loc["AUT", "n_neighbours"]) == 8
cd = {d["name"] for d in R["nei"]["cmp_diff"]}
assert cd == {"Afghanistan", "Bahrain", "Botswana", "Canada", "Ethiopia", "United Kingdom", "India", "Netherlands", "Saudi Arabia", "Zambia"}, cd
CONm = CON.dropna(subset=["area_km2"])
assert CONm.area_km2.idxmin() == CON.index[CON.name == "Pheasant Island"][0]
assert min(int(re.search(r"\d{4}", c).group(0)) for c in CON.created if re.search(r"\d{4}", c)) == 1659
for nm in ("Baarle-Hertog", "Büsingen am Hochrhein", "Campione d'Italia", "Jungholz"):
    assert O[(O.kind == "enclave") & (O.name == nm)].in_natural_earth.max() == 0, nm
for nm in ("Llívia", "Madha", "Nahwa", "Sokh"):
    assert O[(O.kind == "enclave") & (O.name == nm)].in_natural_earth.max() == 1, nm

# ---------- source ----------
R["source"] = {"articles": WK["checks"]["articles"], "pages": WK["checks"]["pages"], "facts_checked": WK["checks"]["facts_checked"],
               "revids": {k: v for k, v in sorted(REV.items())}, "wd_rows": WK["checks"]["wd_rows"], "wd_enclave_items": WK["checks"]["wd_enclave_items"],
               "wd_layers": WK["checks"]["wd_layers"], "wd_intl": WK["checks"]["wd_intl_matched"], "wd_types": len(WK["checks"]["wd_types"]),
               "year": 2026, "articles_minus1": WK["checks"]["articles"] - 1}
R["meta"] = {"page": PAGE, "repo": REPO, "doi": DOI, "blog": BLOG, "slug": SLUG}
R["facts"] = {"pheasant_m2": round(CON.set_index("name").loc["Pheasant Island", "area_km2"] * 1e6), "bir_tawil_km2": 2060, "marked_ha": 3.3,
              "hans_m": 1280, "hans_year": 2022, "busingen_m": 680, "llivia_km": 1.6, "campione_road_km": 14, "point_roberts_km": 40, "point_roberts_pop": 1191,
              "nwangle_pop": 149, "kaliningrad_km2": 15125, "cabinda_km2": 7290, "musandam_km2": 1800, "tripoints_2020": 181, "kazungula_m": "100 to 150",
              "landlocked_wiki": 44, "pyrenees": 1659, "maastricht": 1843, "tin_bigha": "178 by 85 m"}

# ---------- tour ----------
def wiki_pt(k):
    return IB[k]


TOUR = [
    {"id": "baarle", "t": "Baarle", "k": "Enclaves inside enclaves", "c": [51.441, 4.93], "z": 10.6, "bb": [4.62, 51.30, 5.24, 51.58], "own": ["BEL"], "pts": [[51.4369, 4.9286, "Baarle"]],
     "s": f"Twenty-two pieces of Belgium sit inside the Netherlands here, and {R['baarle']['dutch']} pieces of the Netherlands sit inside those, or inside Belgium proper. The smallest Belgian parcel, H7, is {R['baarle']['smallest_m2']:,} square metres. Wikipedia's parcel table has the border running through about {R['baarle']['houses_split']} homes; in H7 it splits a front door, which has one Belgian and one Dutch house number. Natural Earth draws none of this: at 1:10 million Baarle is just the Netherlands."},
    {"id": "cooch", "t": "Cooch Behar", "k": "The world's only counter-counter-enclave", "c": [26.2, 88.85], "z": 8.6, "bb": [88.35, 25.85, 89.35, 26.55], "own": ["IND"],
     "pts": [[26.149911, 88.762161, "Dahala Khagrabari"], [26.300278, 88.945278, "Dahagram"]],
     "s": f"Until midnight on {R['chhits']['swap_date']}, {R['chhits']['indian']} pieces of India sat inside Bangladesh and {R['chhits']['bangladeshi']} pieces of Bangladesh inside India, with {R['chhits']['counter_bd'] + R['chhits']['counter_in']} counter-enclaves inside those. One, Dahala Khagrabari, was a patch of India, inside Bangladesh, inside India, inside Bangladesh: {R['chhits']['dk_m2']:,} square metres of farmland. The swap gave Bangladesh {R['chhits']['to_bangladesh']} enclaves and India {R['chhits']['to_india']}. Only Dahagram-Angarpota is left, joined to Bangladesh by the Tin Bigha Corridor."},
    {"id": "swiss", "t": "Büsingen and Campione", "k": "Switzerland's two foreign islands", "c": [46.8, 8.85], "z": 7.0, "bb": [8.30, 45.70, 9.30, 47.85], "own": ["CHE"],
     "pts": [[47.69694, 8.69028, "Büsingen"], [45.967, 8.967, "Campione"]],
     "s": f"Büsingen am Hochrhein is a German village of {w['busingen_km2']:.2f} km² surrounded by Switzerland, at its narrowest about 680 m from Germany, and inside the Swiss customs area. Campione d'Italia, an Italian town of {w['campione_km2']:.1f} km² on Lake Lugano, is less than a kilometre from Italy as the crow flies but over 14 km by road through Switzerland. Neither appears in Natural Earth: both are swallowed by Switzerland."},
    {"id": "llivia", "t": "Llívia", "k": "A town, not a village", "c": [42.464, 1.98], "z": 10.6, "bb": [1.75, 42.33, 2.20, 42.58], "own": ["ESP"], "pts": [[42.46444, 1.98083, "Llívia"]],
     "s": f"The Treaty of the Pyrenees of 1659 gave France the villages of the Cerdanya valley. Llívia was a town, so it stayed Spanish: {w['llivia_km2']:.2f} km² of Spain about 1.6 km inside France. This one is big enough for Natural Earth, which draws it at {next(e['area_km2'] for e in EXC if e['unit'] == 'ESP' and abs(e['lat'] - 42.46) < .1):.1f} km²."},
    {"id": "jungholz", "t": "Jungholz", "k": "Attached by a single point", "c": [47.574, 10.447], "z": 10.4, "bb": [10.20, 47.45, 10.70, 47.68], "own": ["AUT"], "pts": [[47.57361, 10.44722, "Jungholz"]],
     "s": "Jungholz is Austrian, but it touches the rest of Austria only at one point, the summit of the Sorgschrofen, where four borders meet. Every road in comes through Germany. Natural Earth, which works at about a kilometre's precision, does not separate it from Austria."},
    {"id": "kazungula", "t": "Kazungula", "k": "A quadripoint that is not", "c": [-17.794, 25.26], "z": 11.0, "bb": [25.0, -17.95, 25.5, -17.62], "own": [], "pts": [[R["tri"]["kazungula"]["lat"], R["tri"]["kazungula"]["lon"], "Kazungula"]],
     "s": "Botswana, Namibia, Zambia and Zimbabwe come within a whisker of meeting here, where the Chobe joins the Zambezi. Wikipedia says all four states agreed in the late 2000s that Botswana and Zambia share a border of about 150 m, so there are two tripoints rather than one quadripoint; the Kazungula Bridge has crossed it since 2021. Natural Earth draws a single point where all four meet: the only quadripoint in its 1:10 million world."},
    {"id": "roberts", "t": "Point Roberts", "k": "South of the 49th parallel", "c": [48.99, -123.06], "z": 10.6, "bb": [-123.35, 48.90, -122.75, 49.12], "own": ["US1"], "pts": [[48.98639, -123.05694, "Point Roberts"]],
     "s": f"The 49th parallel cut the tip off the Tsawwassen peninsula, leaving a piece of Washington State reachable by land only through 40 km of Canada. Its 1,191 residents (2020) have their own ZIP code. Natural Earth draws it as a separate part of the United States of {next(e['area_km2'] for e in EXC if e['unit'] == 'US1' and e['area_km2'] < 10):.1f} km²."},
    {"id": "angle", "t": "Northwest Angle", "k": "A mapping mistake from 1783", "c": [49.33, -95.1], "z": 9.0, "bb": [-95.6, 48.95, -94.5, 49.55], "own": ["US1"], "pts": [[49.39, -95.153, "Northwest Angle"]],
     "s": "The 1783 Treaty of Paris drew the border from a map that got the Lake of the Woods wrong. The result is the only part of the contiguous United States north of the 49th parallel, reachable by land only through Manitoba. 149 people lived there in 2020."},
    {"id": "kaliningrad", "t": "Kaliningrad", "k": "Russia on the Baltic", "c": [54.75, 21.3], "z": 6.7, "bb": [19.2, 53.7, 23.2, 55.6], "own": ["RUS"], "pts": [[54.71, 20.51, "Kaliningrad"]],
     "s": f"Russia's westernmost region, the northern half of what was East Prussia, is bordered by Poland, Lithuania and the Baltic Sea. Wikipedia gives it 15,125 km²; Natural Earth's outline, which leaves out the lagoons, measures {next(e['area_km2'] for e in EXC if e['unit'] == 'RUS' and e['lat'] > 54):,.0f} km²."},
    {"id": "nakhchivan", "t": "Nakhchivan", "k": "A landlocked exclave", "c": [39.25, 45.4], "z": 7.1, "bb": [44.3, 38.6, 46.8, 40.0], "own": ["AZE"], "pts": [[39.21, 45.41, "Nakhchivan"]],
     "s": f"Azerbaijan's exclave of {w['nakhchivan_km2']:,.0f} km² is bordered by Armenia, Iran and Turkey and has no coast at all. In Natural Earth it is the only exclave that has no coast and touches more than one country."},
    {"id": "cabinda", "t": "Cabinda", "k": "Angola north of the Congo", "c": [-5.0, 12.4], "z": 7.3, "bb": [11.3, -6.3, 13.4, -4.2], "own": ["AGO"], "pts": [[-5.55, 12.19, "Cabinda"]],
     "s": f"A strip of the Democratic Republic of the Congo, the country's only coast, separates Cabinda from the rest of Angola. Wikipedia gives the province 7,290 km²; Natural Earth draws {next(e['area_km2'] for e in EXC if e['unit'] == 'AGO'):,.0f} km²."},
    {"id": "madha", "t": "Musandam, Madha and Nahwa", "k": "Oman, the Emirates, Oman, the Emirates", "c": [25.6, 56.25], "z": 8.2, "bb": [55.85, 24.85, 56.65, 26.45], "own": ["OMN"],
     "pts": [[25.28444, 56.33306, "Madha"], [25.26833, 56.28028, "Nahwa", "l"], [25.917, 56.283, "Musandam"]],
     "s": f"Oman's Musandam peninsula, on the Strait of Hormuz, is cut off from the rest of Oman by the United Arab Emirates. Halfway between the two lies Madha, a piece of Oman surrounded by the Emirates, and inside Madha lies Nahwa, a village of about 40 buildings that belongs to Sharjah. The lines were settled in 1969. Natural Earth draws all three, Nahwa at {next(e['area_km2'] for e in EXC if e['unit'] == 'ARE'):.1f} km²."},
    {"id": "pheasant", "t": "Pheasant Island", "k": "Six months French, six months Spanish", "c": [43.3428, -1.7656], "z": 12.0, "bb": [-1.92, 43.27, -1.62, 43.42], "own": [], "pts": [[43.34278, -1.76556, "Pheasant Island"]],
     "s": f"This river island in the Bidasoa, {R['facts']['pheasant_m2']:,} square metres in the condominium table, belongs to both France and Spain. France runs it from 1 August to 31 January, Spain from 1 February to 31 July. Louis XIV met his bride here, the Treaty of the Pyrenees was signed here, and there are no pheasants."},
    {"id": "birtawil", "t": "Bir Tawil", "k": "The land nobody wants", "c": [21.87, 33.75], "z": 7.6, "bb": [32.6, 21.1, 36.9, 22.9], "own": [], "pts": [[21.86917, 33.74778, "Bir Tawil"]],
     "s": "Two lines drawn by Britain, in 1899 and 1902, disagree. Egypt claims the 1899 line and Sudan the 1902 one, because each gives it the larger Halaib Triangle on the Red Sea. That leaves Bir Tawil, 2,060 km² of desert, claimed by neither. Natural Earth draws it as an indeterminate zone, which this page does not count as a country."},
    {"id": "market", "t": "Märket", "k": "A border that zigzags round a lighthouse", "c": [60.3008, 19.1314], "z": 8.6, "bb": [18.35, 59.95, 20.15, 60.55], "own": [], "pts": [[60.30083, 19.13139, "Märket"]],
     "s": "A treaty of 1809 ran the border between Sweden and Finland straight through the middle of this 3.3 hectare skerry. In 1885 Finland built a lighthouse on its highest point, which turned out to be on the Swedish half. In 1985 the line was redrawn as an inverted S of about 480 m, putting the lighthouse in Finland with no net change of territory. It is the smallest sea island shared by two countries, and far too small for Natural Earth."},
]
for t in TOUR:
    assert 2 <= len(t["s"].split(". ")) and "—" not in t["s"] and "–" not in t["s"]
assert 12 <= len(TOUR) <= 15


# insets: Natural Earth 10m clipped to each box, projected (equirectangular, cos lat), as SVG paths
def inset(t, W_=300):
    """Natural Earth 10m clipped to the tour box, widened or heightened to an aspect ratio between 4:3 and 1:1."""
    x0, y0, x1, y1 = t["bb"]; c = np.cos(np.radians((y0 + y1) / 2))
    wk, hk = (x1 - x0) * c, (y1 - y0)
    if hk / wk > 1:                                   # too tall: widen
        d = (hk - wk) / c / 2; x0, x1 = x0 - d, x1 + d
    elif hk / wk < .75:                               # too wide: heighten
        d = (.75 * wk - hk) / 2; y0, y1 = y0 - d, y1 + d
    H_ = W_ * (y1 - y0) / ((x1 - x0) * c)
    sx = W_ / (x1 - x0)
    X = lambda lo: (lo - x0) * sx; Y = lambda la: (y1 - la) * sx / c
    bb = box(x0, y0, x1, y1); paths = {}
    for u, adm, g in P["poly"]:
        if not g.intersects(bb): continue
        q = g.intersection(bb).simplify((x1 - x0) / 600)
        for p in (q.geoms if hasattr(q, "geoms") else [q]):
            if p.geom_type != "Polygon" or p.is_empty: continue
            d = "".join("M" + "L".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in ring.coords) + "Z" for ring in [p.exterior] + list(p.interiors))
            paths.setdefault(u, []).append(d)
    return {"w": round(W_), "h": round(H_), "bb": [round(v, 4) for v in (x0, y0, x1, y1)], "units": [{"u": u, "n": UN[u], "d": "".join(ds)} for u, ds in paths.items()],
            "pts": [[round(X(p[1]), 1), round(Y(p[0]), 1), p[2]] + p[3:] for p in t["pts"]]}


for t in TOUR:
    t["inset"] = inset(t)
R["tour"] = [{k: v for k, v in t.items() if k != "inset"} for t in TOUR]
R["tour_n"] = len(TOUR)

# ---------- page data ----------
OM = O[O.mapped == 1]
KI = {k: i for i, (k, _, _) in enumerate(KINDS)}
site = {"kinds": KINDS, "odd": [[round(r.lat, 5), round(r.lon, 5), KI[r.kind], r.name, r.owner[:60], r.within[:60],
                                 None if r.area_km2 != r.area_km2 or r.area_km2 is None else r.area_km2, r.sub, int(r.in_natural_earth), r.coord_src, (r.text or "")[:260]] for r in OM.itertuples()],
        "tri": [[t["lat"], t["lon"], " / ".join(UN[u] for u in t["units"]), t["n"], t["zone"]] for t in TRI],
        "wd": [[r["lat"], r["lon"], r["label"], r["country"]] for r in WK["wikidata"] if r["layer"] == "subnational" and r["lat"] is not None],
        "tour": TOUR, "zones": {k: v for k, v in UN.items() if k.startswith("Z:")}}
SZ = [["Baarle parcels", r["parcel"] + " (" + r["country"] + ")", r["area_ha"] / 100] for r in WK["baarle"]]
# chhits: one dot per parcel; rows that give the total of a composite enclave are left out so no land is counted twice
SZ += [["Former India and Bangladesh enclaves", r["name"], r["area_km2"]] for r in WK["chhits"] if r["area_km2"] and r["area_km2"] == r["area_km2"] and not re.match(r"(Largest )?[Cc]omposite exclave", r["notes"] or "")]
R["chhits"]["sized_parcels"] = sum(1 for z in SZ if z[0] == "Former India and Bangladesh enclaves")
SZ += [["True enclaves on land" if r.water == 0 else "True enclaves: islands and water", SHORT.get(r.name, r.name), r.area_km2] for r in TE.itertuples() if r.area_km2 == r.area_km2]
SZ += [["Enclaved countries", r.name, r.area_km2] for r in TL[TL.kind == "enclaved_country"].itertuples()]
SZ += [["Exclaves that are not enclaves", SHORT.get(r.name, r.name), r.area_km2] for r in TL[TL.kind == "exclave"].itertuples() if r.area_km2 == r.area_km2]
site["sizes"] = SZ
R["sizes_n"] = len(SZ)
R["condos"] = [{"name": c.name, "states": c.states, "km2": c.area_km2 if c.area_km2 == c.area_km2 else None, "created": c.created} for c in CON.itertuples()]
site["enclaves"] = [[SHORT.get(r.name, r.name), r.owner, r.within, r.area_km2 if r.area_km2 == r.area_km2 else None, int(r.parcels), int(r.water), r.lat, r.lon,
                     int(O[(O.kind == "enclave") & (O.name == SHORT.get(r.name, r.name))].in_natural_earth.max())] for r in TE.itertuples()]
jsave(site, f"{DATA}/site.json")
jsave(R, f"{DATA}/results.json", indent=1)
print({k: v for k, v in R["wiki"].items() if k not in ("owners", "withins")})
print(R["tri"]); print({k: v for k, v in R["nei"].items()}); print(R["land"]); print({k: v for k, v in R["ne"].items() if k != "enclaves"})
print(R["baarle"], R["chhits"]); print(R["borders"])
print("data", {k: os.path.getsize(f"{DATA}/{k}") // 1024 for k in os.listdir(DATA)})
