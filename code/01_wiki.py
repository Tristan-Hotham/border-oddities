"""Read the Wikipedia articles (raw/wiki_pages.json) and the Wikidata query (raw/wd_enclaves.tsv).

From "List of enclaves and exclaves" (national level only; sub-national tables are counted, not mapped):
  * enclaves that are also exclaves (the true international enclaves), enclaved countries, exclaves that are not
    enclaves, and historic enclaves: from the tables, with area, owner, surrounding country and the geo microformat;
  * semi-enclaves, semi-exclaves, pene-exclaves and divided islands: from the bulleted lists (one entry per list item);
  * rows for pockets of high seas surrounded by exclusive economic zones are kept apart (they are water, not land).
Other articles: infobox coordinates (the first geo microformat on the page), the parcel tables for Baarle and the
India-Bangladesh enclaves, the tripoint list, the land border table, the list of countries with one neighbour, the
condominium table, and sentences checked word for word for the facts quoted on the page.
Wikidata: the items are filtered to international enclaves and exclaves by matching them to the Wikipedia list;
ethnic quarters, ghettos, townships, military bridgeheads and similar types are dropped; sub-national enclaves with
coordinates are kept as a separate layer."""
import csv
import pandas as pd
from common import *

W = wiki()
CHK = {"pages": len(W), "articles": len({v["revid"] for v in W.values()})}
REVIDS = {k: v["revid"] for k, v in W.items()}

# ---------- the list article, walked in document order ----------
L = soup("List of enclaves and exclaves")
for x in L.find_all(["sup", "style"]):
    x.decompose()
path = {2: "", 3: "", 4: ""}
tables, items = [], []
for e in L.find_all(["h2", "h3", "h4", "table", "li"]):
    if e.name in ("h2", "h3", "h4"):
        lv = int(e.name[1]); path[lv] = e.get_text(" ", strip=True)
        for k in range(lv + 1, 5): path[k] = ""
        continue
    sec = " > ".join(p for p in (path[2], path[3], path[4]) if p)
    if e.name == "table":
        if "wikitable" in (e.get("class") or []):
            tables.append((sec, e))
        continue
    if e.find_parent("table") or e.find_parent(class_=re.compile("reflist|references|navbox|toc")):
        continue
    if e.find_parent("li"):
        continue          # nested items are read with their parent
    sub = e.find("ul")
    if sub:
        head = "".join(t.get_text(" ", strip=True) if hasattr(t, "get_text") else str(t) for t in e.contents if getattr(t, "name", None) != "ul")
        head = re.sub(r"\s+", " ", head).strip().rstrip(":").strip()
        for c in sub.find_all("li", recursive=False):
            items.append((sec, head, clean_cell(c), geo_of(c)))
    else:
        items.append((sec, None, clean_cell(e), geo_of(e)))
CHK["list_tables"] = [s for s, _ in tables]


def owner(s):
    """'Argentina ( Corrientes Province ... )' -> 'Argentina'."""
    s = re.sub(r"\(\s*de (facto|jure)\s*\)", "", s)
    return re.split(r"\s\(|\s\[", s)[0].strip()


def parcels(name, area):
    m = re.search(r"\((\d+)(?: parcels| islands)?\)", name)
    if m: return int(m.group(1))
    if " and " in area: return len(area.split(" and "))
    return 1


WATER = re.compile(r"\bisland|lacustrine|territorial water|including water|incl\b|incl |laguna|islets|cays|reef|bank", re.I)
rows = []
for sec, t in tables:
    if not sec.endswith("National level"):
        continue
    G = grid(t); hdr = [h for h, _ in G[0]]
    col = lambda *names: next((i for i, h in enumerate(hdr) if any(h.startswith(n) for n in names)), None)
    ci = dict(name=col("Name", "Country"), area=col("Area"), ex=col("Exclave of"), inn=col("Enclaved within"), co=col("Coordinates"), no=col("Notes"), ed=col("Existed"))
    kind = {"Enclaves that are also exclaves > National level": "enclave", "Enclaves that are not exclaves > National level": "enclaved_country",
            "Exclaves that are not enclaves > National level": "exclave", "Historic enclaves/exclaves > National level": "historic"}[sec]
    for r in G[1:]:
        if len(r) < len(hdr): continue
        g = lambda k: r[ci[k]][0] if ci[k] is not None else ""
        name = re.sub(r"\s+\[.*?\]", "", g("name")).strip()
        ex = g("ex") if kind != "enclaved_country" else g("name")
        rec = {"name": name, "kind": kind, "area_txt": g("area"), "area_km2": num(g("area")), "owner": owner(ex), "owner_detail": ex,
               "within": owner(g("inn")) if ci["inn"] is not None else "", "within_detail": g("inn") if ci["inn"] is not None else "",
               "lat": None, "lon": None, "coord_src": "", "notes": g("no"), "existed": g("ed"), "section": sec, "parcels": parcels(name, g("area"))}
        geo = r[ci["co"]][1] if ci["co"] is not None else None
        if geo: rec.update(lat=geo[0], lon=geo[1], coord_src="Wikipedia list table")
        rec["de_facto"] = int("de facto" in g("name"))
        rec["maritime"] = int(rec["owner"] == "International waters")
        rec["water"] = int(bool(WATER.search(name + " " + g("area") + " " + g("no"))) and not rec["maritime"])
        rows.append(rec)
T = pd.DataFrame(rows)
for k in ("enclave", "enclaved_country", "exclave", "historic"):
    CHK[f"rows_{k}"] = int((T.kind == k).sum())
CHK["maritime_rows"] = int(T.maritime.sum())
assert CHK["rows_enclaved_country"] == 3 and set(T[T.kind == "enclaved_country"].name) == {"Lesotho", "San Marino", "Vatican City"}

# ---------- the bulleted lists ----------
LISTSEC = {"Semi-enclaves and semi-exclaves > Semi-enclaves that are not semi-exclaves > National level": ("semi", "semi-enclave"),
           "Semi-enclaves and semi-exclaves > Semi-enclaves that are also semi-exclaves > National level": ("semi", "semi-enclave and semi-exclave"),
           "Semi-enclaves and semi-exclaves > Semi-exclaves that are not semi-enclaves > National level": ("semi", "semi-exclave"),
           "Pene-enclaves/exclaves (including inaccessible districts) > National level": ("pene", "pene-exclave"),
           "Pene-enclaves/exclaves (including inaccessible districts) > National level > Divided islands": ("divided_island", "divided island")}
li = []
for sec, head, txt, geo in items:
    if sec not in LISTSEC or len(txt) < 12:
        continue
    kind, sub = LISTSEC[sec]
    m = re.match(r"^([A-Z][^:]{1,60}?)\s:\s(.*)$", txt)
    label = head or (m.group(1) if m else "")
    li.append({"kind": kind, "sub": sub, "country_label": label.strip(), "text": txt, "lat": geo[0] if geo else None, "lon": geo[1] if geo else None})
LI = pd.DataFrame(li)
for k in ("semi", "pene", "divided_island"):
    CHK[f"items_{k}"] = int((LI.kind == k).sum())
assert 15 <= CHK["items_semi"] <= 30 and CHK["items_pene"] >= 40, CHK

# sub-national: table rows and list items, counted only
sub_rows = sum(len(grid(t)) - 1 for s, t in tables if "subnational" in s.lower() or "Other subnational" in s)
CHK["subnational_table_rows"] = sub_rows

# ---------- infobox coordinates of the articles ----------
INFOBOX = {}
for k in W:
    g = geo_of(soup(k))
    if g: INFOBOX[k] = g
CHK["infobox_coords"] = len(INFOBOX)

# ---------- Baarle parcels ----------
BH = soup("Baarle-Hertog"); bt = BH.find_all("table", class_="wikitable")
baarle = []
for t in bt[:2]:
    for r in grid(t)[1:]:
        code = r[0][0].split(",")[0].strip()
        baarle.append({"parcel": code, "name": r[0][0].split(",", 1)[1].strip() if "," in r[0][0] else "", "country": "Netherlands" if code.startswith("N") else "Belgium",
                       "area_ha": float(r[1][0]), "area_m2": round(float(r[1][0]) * 1e4), "notes": r[3][0]})
B = pd.DataFrame(baarle)
assert len(B) == 30 and (B.country == "Belgium").sum() == 22 and (B.country == "Netherlands").sum() == 8


def homes(note):
    """Homes the boundary runs through, as the parcel note words it ('about 20 dwellings', 'two dwellings', 'a house')."""
    m = re.search(r"runs through (.*?)(?:[.;(]|$)", note)
    if not m: return 0
    n = 0
    for q, _ in re.findall(r"(about \d+|\d+|two|three|a|one) (dwellings?|houses?)\b(?! number)", m.group(1)):
        n += int(re.sub(r"\D", "", q)) if re.search(r"\d", q) else {"a": 1, "one": 1, "two": 2, "three": 3}[q]
    return n


B["houses_split"] = B.notes.map(homes)
assert "the middle of one front door" in B.set_index("parcel").loc["H7", "notes"]
B.to_csv(f"{DATA}/baarle_parcels.csv", index=False)

# ---------- India-Bangladesh chhits ----------
IB = soup("India–Bangladesh enclaves"); it_ = IB.find_all("table", class_="wikitable")
chh = []
for side, t in zip(("Bangladeshi chhit in India", "Indian chhit in Bangladesh"), it_[:2]):
    for r in grid(t)[1:]:
        a = r[1][0].replace("†", "").strip()
        chh.append({"side": side, "name": r[0][0].replace("❋", "").strip(), "area_km2": float(a) if re.fullmatch(r"[\d.]+", a) else None, "notes": r[3][0]})
C = pd.DataFrame(chh)
C.to_csv(f"{DATA}/india_bangladesh_chhits.csv", index=False)
dk = C[C.name == "Dahala Khagrabari (#51)"].iloc[0]
assert "only counter-counter enclave" in dk.notes
nat = C[C.name == "Natatoka (#38)"].iloc[0]
assert "Smallest known chhit" in nat.notes

# ---------- tripoints (Wikipedia list) ----------
TP = soup("List of tripoints"); trip = []
for t in TP.find_all("table", class_="wikitable"):
    for r in grid(t)[1:]:
        g = r[4][1]
        trip.append({"name": r[0][0], "c1": r[1][0], "c2": r[2][0], "c3": r[3][0], "lat": g[0] if g else None, "lon": g[1] if g else None, "region": r[5][0]})
TRIP = pd.DataFrame(trip)
TRIP.to_csv(f"{WORK}/wiki_tripoints.csv", index=False)

# ---------- land borders ----------
LB = soup("List of countries and territories by land borders"); lb = []
for r in grid(LB.find("table", class_="wikitable"))[2:]:
    nm = re.sub(r"\s*\(.*$|\s*\[.*$", "", r[0][0]).strip()
    lb.append({"country": nm, "km": num(r[1][0]), "n_borders": num(r[3][0]), "n_neigh": num(r[4][0])})
LBD = pd.DataFrame(lb)
LBD.to_csv(f"{WORK}/wiki_land_borders.csv", index=False)

# ---------- one neighbour ----------
ON = soup("List of countries that border only one other country"); one = []
for i, t in enumerate(ON.find_all("table", class_="wikitable")[:2]):
    for r in grid(t)[2:]:
        one.append({"country": r[0][0], "neighbour": r[1][0], "km": num(r[2][0]), "landlocked": int(i == 0)})
ONE = pd.DataFrame(one)

# ---------- landlocked countries ----------
LLW = [r[0][0] for r in grid(soup("Landlocked country").find("table", class_="wikitable"))[1:] if r[0][0] not in ("Total", "Percentage of the world")]
assert len(LLW) == 47

# ---------- condominiums ----------
CO = soup("Condominium (international law)"); con = []
for r in grid(CO.find("table", class_="wikitable"))[1:]:
    con.append({"name": r[0][0], "states": r[1][0], "area_km2": num(r[2][0]), "created": r[4][0], "notes": r[5][0][:300]})
CON = pd.DataFrame(con)

# ---------- facts quoted on the page, checked word for word ----------
FACTS = {
    "Baarle-Nassau": ["The smallest Belgian parcel, H7, locally named De Loversche Akkers , measures 2,469 square metres",
                      "the border is made visible on all streets with iron pins", "the style of house numbers is different in both countries",
                      "Treaty of Maastricht in 1843"],
    "Baarle-Hertog": ["22 Belgian exclaves fully within the Netherlands", "seven Dutch enclaves within the Belgian exclaves",
                      "Some houses in the town of Baarle-Hertog / Baarle-Nassau are divided between the two countries",
                      "customers had to move to a table on the Belgian side", "restaurants in the Netherlands had to close earlier than those in Belgium"],
    "India–Bangladesh enclaves": ["The main body of Bangladesh contained 102 Indian enclaves, which in turn contained 21 Bangladeshi counter-enclaves",
                                  "Dahala Khagrabari , an Indian counter-counter-enclave, the world's only third-order enclave",
                                  "The Indian mainland contained 71 Bangladeshi enclaves, which in turn contained 3 Indian counter-enclaves",
                                  "found 51,549 people", "The enclaves were exchanged at midnight on 31 July 2015",
                                  "India received 51 Bangladeshi enclaves", "Bangladesh received 111 Indian enclaves",
                                  "the only remaining enclave is Dahagram–Angarpota", "card or chess games", "1713 treaty",
                                  "178-by-85-metre (584 ft × 279 ft) corridor, called the Tin Bigha Corridor", "The Tin Bigha Corridor was leased to Bangladesh in 1992"],
    "Dahagram–Angarpota": ["Tin Bigha Corridor", "about 200 m (660 ft) away from the border of Bangladesh"],
    "Llívia": ["Treaty of the Pyrenees , signed in 1659", "\"villages\"", "\"town\"", "approximately 1.6 km (1.0 mile) wide"],
    "Büsingen am Hochrhein": ["about 680 m [2,230 ft] wide", "Swiss customs union", "7.62 km"],
    "Campione d'Italia": ["over 14 km (9 mi)", "Lake Lugano", "less than one kilometre"],
    "Point Roberts, Washington": ["traveling 25 mi (40 km) through Canada", "49th parallel", "population of 1,191 at the 2020 census"],
    "Northwest Angle": ["only place in the contiguous United States north of the 49th parallel", "Mitchell Map", "1783 Treaty of Paris",
                        "total population of 149 at the 2020 United States Census"],
    "Kaliningrad Oblast": ["bordered by Poland to the south, Lithuania to the north and east, and the Baltic Sea to the west", "15,125 square kilometres"],
    "Nakhchivan Autonomous Republic": ["landlocked exclave of the Republic of Azerbaijan", "bordered by Armenia to the east and north, Iran to the southwest, and Turkey to the northwest"],
    "Cabinda Province": ["separated from the rest of Angola by a narrow strip of territory belonging to the Democratic Republic of the Congo", "7,290 km"],
    "Musandam Governorate": ["Strait of Hormuz", "separated from the rest of Oman by the United Arab Emirates", "accessible by land only from the United Arab Emirates"],
    "Madha": ["exclave of Oman entirely surrounded by the United Arab Emirates", "halfway between the Musandam Peninsula and the Omani mainland", "1969"],
    "Nahwa": ["counter-enclave (or second-order enclave )", "about 40 buildings"],
    "Isla de los Faisanes": ["whose administration alternates between the two nations every six months", "It is administered by France from 1 August to 31 January",
                             "It is administered by Spain from 1 February to 31 July", "There are no pheasants on the island", "Treaty of the Pyrenees", "Louis XIV met his future wife"],
    "Bir Tawil": ["claimed by neither country", "2,060 km", "1899", "1902", "the straight political boundary between Egypt and Sudan established in 1899 and the irregular administrative boundary established in 1902", "the 22nd parallel", "Halaib Triangle is claimed by both and Bir Tawil by neither"],
    "Märket": ["3.3-hectare", "Treaty of Fredrikshamn of 1809", "The border used to be straight until the Grand Duchy of Finland built the lighthouse on the Swedish side",
               "smallest sea island shared by two countries", "When it was built by the Grand Duchy of Finland in 1885", "the border was adjusted in 1985",
               "no net transfer of territory occurred", "inverted 'S'", "around 480 metres"],
    "Jungholz": ["connected to the rest of Austria by a single point, which is the summit of the mountain Sorgschrofen", "only accessible via Germany"],
    "Hans Island": ["14 June 2022", "Whisky War", "barren and uninhabited", "was for years a border dispute", "A 1,280 m (4,200 ft) shared border"],
    "Sankovo-Medvezhye": ["Chernobyl in 1986"],
    "Vennbahn": ["Treaty of Versailles", "six small exclaves of Germany", "of which five remain"],
    "Kleinwalsertal": ["accessible only via Oberstdorf"],
    "Tripoint": ["As of 2020, there are 181 international tripoints in the world", "China with 16 international tripoints and Russia with 11 to 14"],
    "Quadripoint": ["two separate tripoints exist about 100 to 150 metres", "Kazungula Bridge opened for traffic in May 2021",
                    "The existence of a short boundary of about 150 metres (490 ft) between Zambia and Botswana was agreed by all four states"],
    "Landlocked country": ["there are 44 landlocked countries, two of them doubly landlocked", "Liechtenstein in Western Europe , surrounded by Austria and Switzerland",
                           "Uzbekistan's doubly landlocked status depends on whether the Caspian Sea is considered a lake or a sea"],
    "Enclave and exclave": ["Three such sovereign states exist globally: Lesotho"],
    "Terra nullius": ["Gornja Siga"],
}
for k, ss in FACTS.items():
    t = wtext(k)
    for s in ss:
        assert s in t, (k, s)
CHK["facts_checked"] = sum(len(v) for v in FACTS.values())

# ---------- Wikidata ----------
wd = []
with open(os.path.join(RAW, "wd_enclaves.tsv"), encoding="utf-8") as f:
    rd = csv.reader(f, delimiter="\t")
    hdr = next(rd)
    for r in rd:
        r = r + [""] * (8 - len(r))
        unq = lambda s: re.sub(r'@en$', "", s).strip().strip('"')
        m = re.match(r"POINT\((-?[\d.]+) (-?[\d.]+)\)", r[3])
        wd.append({"qid": r[0].rsplit("/", 1)[-1].rstrip(">"), "label": unq(r[1]), "type": unq(r[2]), "lon": float(m.group(1)) if m else None,
                   "lat": float(m.group(2)) if m else None, "country": unq(r[4]), "area": r[5], "pop": r[6],
                   "enwiki": r[7].rsplit("/", 1)[-1].rstrip(">") if r[7] else ""})
WD0 = pd.DataFrame(wd)
CHK["wd_rows"] = len(WD0); CHK["wd_items"] = int(WD0.qid.nunique()); CHK["wd_types"] = WD0.type.value_counts().to_dict()
KEEP_T = {"enclave", "Indo-Bangladesh enclaves"}
WD = WD0[WD0.type.isin(KEEP_T)].drop_duplicates("qid").copy()
CHK["wd_enclave_items"] = len(WD)
# international: matched to a national-level Wikipedia entry (by name), or one of the cases named in the tours
INTL = {"Shohimardon": "Shakhimardan", "Lesotho": "Lesotho", "Llívia": "Llívia", "Vatican City": "Vatican City", "San Marino": "San Marino",
        "Baarle-Hertog": "Baarle-Hertog (22 parcels)", "Baarle-Nassau": "Baarle-Nassau (8 parcels)", "Vorukh": "Vorukh", "Madha": "Madha", "Nahwa": "Nahwa",
        "Dahala Khagrabari": "Indo-Bangladesh enclaves (106 parcels)", "Dahagram–Angarpota": "Dahagram-Angarpota", "Artsvashen": "Artsvashen",
        "Yuxarı Əskipara": "Yukhari Askipara", "Karki": "Karki / Tigranashen", "Barxudarlı": "Barkhudarli", "Sankovo-Medvezhye": "San'kovo-Medvezh'e",
        "Jungholz": "Jungholz", "Münsterbildchen": "Münsterbildchen", "Roetgener Wald": "Roetgener Wald", "Rückschlag": "Rückschlag",
        "Ruitzhof": "Ruitzhof", "Xylotymvou": "Xylotymbou", "Ormideia": "Ormidhia", "Likoma Island": "Likoma Island",
        "Chizumulu Island": "Chizumulu Island (incl Lundu Is., Papia Is., Ngkyvo Is.)", "Martín García Island": "Isla Martín García",
        "Isla Apipé": "Apipé Islands (4)", "West Kowloon Station Mainland Port Area": "West Kowloon Port ( aka . Mainland Port Area)"}
WD["label2"] = WD.label.where(WD.label != "", WD.enwiki.str.replace("_", " ").str.replace("%27", "'"))
WD.loc[WD.qid == "Q244207", "label2"] = "Campione d'Italia"; INTL["Campione d'Italia"] = "Campione d'Italia"
names = set(T.name)
miss = [v for v in INTL.values() if v not in names]
assert not miss, miss
WD["intl_match"] = WD.label2.map(INTL).fillna("")
HIST = {"Papal States", "Congo Free State", "Austria–Hungary", "West Germany", "allied-occupied Germany", "Margraviate of Brandenburg", "Soviet Union"}
WD["layer"] = "subnational"
WD.loc[WD.intl_match != "", "layer"] = "international"
WD.loc[WD.country.isin(HIST) | WD.label2.isin(["West Berlin", "Lado Enclave", "Comtat Venaissin", "Jasna Góra Enclave", "Enclave of the popes", "Verenahof",
                                                "European enclaves in North Africa before 1830", "Vennbahn exclaves"]), "layer"] = "historic or other"
WD.loc[(WD.layer == "subnational") & (WD.lat.isna() | (WD.country == "") | WD.label2.isin(["Palestinian enclaves", "Sovereign State of the Bektashi Order", "Fallujah Pocket",
                                                                                            "Turkish part of Aleppo Governorate", "Jassar Enclave", "Sucumbíos Triangle", "Bonn Enclave"])), "layer"] = "historic or other"
WD = WD[WD.label2 != ""]
WD[["qid", "label2", "type", "country", "lat", "lon", "area", "pop", "enwiki", "layer", "intl_match"]].rename(columns={"label2": "label"}).to_csv(f"{DATA}/wikidata_enclaves.csv", index=False)
CHK["wd_layers"] = WD.layer.value_counts().to_dict()
CHK["wd_intl_matched"] = int((WD.layer == "international").sum())

out = {"tables": T.to_dict("records"), "lists": LI.to_dict("records"), "infobox": {k: list(v) for k, v in INFOBOX.items()},
       "baarle": B.to_dict("records"), "chhits": C.to_dict("records"), "wiki_tripoints": TRIP.to_dict("records"),
       "land_borders": LBD.to_dict("records"), "one_neighbour": ONE.to_dict("records"), "landlocked_wiki": LLW, "condominiums": CON.to_dict("records"),
       "wikidata": WD.to_dict("records"), "revids": REVIDS, "checks": CHK}
jsave(json.loads(pd.io.json.dumps(out) if False else json.dumps(out, default=lambda o: None if o != o else o)), f"{WORK}/wiki.json")
print(json.dumps(CHK, ensure_ascii=False)[:1500])
print(T.groupby("kind").size().to_dict(), LI.groupby("kind").size().to_dict())
