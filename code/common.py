"""Shared paths, unit definitions and helpers for the border-oddities project.

Raw inputs (read in place, never modified):
  raw/wiki_pages.json         English Wikipedia articles as parsed HTML with revision ids (37 keys, 34 distinct
                              articles), CC BY-SA 4.0. Used for the enclave tables and lists, the tripoint list, the land
                              border table, the condominium table, infobox coordinates and facts quoted in the text.
  raw/wd_enclaves.tsv         Wikidata items that are instances of enclave or related types, with coordinates,
                              country, area, population and English Wikipedia link (CC0). Noisy: filtered in 01_wiki.py.
  raw/wd_tripoints.tsv        Wikidata tripoint query: header only, no rows (not used).
  /home/claude/newdata/raw/geo/ne_10m_admin_0_countries.geojson   Natural Earth 1:10m countries (public domain): the
                              geometry for tripoints, exclaves, neighbours, border lengths and landlocked status.
  /home/claude/newdata/raw/geo/ne_50m_admin_0_countries.geojson   Natural Earth 1:50m countries (world outlines).
  /home/claude/newdata/raw/geo/ne_10m_populated_places_simple.geojson   capitals (to pick each country's main part).
"""
import json, gzip, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("BO_RAW", os.path.join(ROOT, "raw"))
GEO = os.environ.get("BO_GEO", "/home/claude/newdata/raw/geo")
FONTS = os.environ.get("BO_FONTS", "/home/claude/ref/fonts")
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(os.environ.get("BOTMP", "/dev/shm/borderoddities"), "work")   # intermediates live in memory, not in the repo
for d in (DATA, WORK):
    os.makedirs(d, exist_ok=True)

SLUG = "border-oddities"
PAGE = f"https://maps.tristanhotham.com/{SLUG}/"
REPO = f"https://github.com/Tristan-Hotham/{SLUG}"
DOI = "10.5281/zenodo.23873011"                # filled in by the publisher
BLOG = "https://blog.tristanhotham.com/2026/10/31/border-oddities/"          # filled in by the publisher
AI = ("I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped "
      "prepare the analysis code. I reviewed and checked all text and results.")
TITLE = "The world's strangest borders"
PAPER_TITLE = "Islands on Land: Enclaves, Exclaves, Tripoints and Other Oddities of the World's Borders"

# ---------- Natural Earth units ----------
# A "country" is a Natural Earth sovereignty group (SOV_A3), so dependencies count with their sovereign (Hong Kong and
# Macao with China, Gibraltar and the Cyprus base areas with the United Kingdom, Saint-Martin with France, Sint Maarten
# with the Netherlands). Natural Earth's de facto units are kept as they are (Kosovo, Northern Cyprus, Somaliland,
# Taiwan, Western Sahara); Palestine, which Natural Earth groups with Israel, is kept separate. This follows Natural
# Earth's de facto lines and is not an endorsement of any claim.
ZONES = {"CNM": "Cyprus UN buffer zone", "BRI": "Brazilian Island", "KAS": "Siachen Glacier", "SPI": "Southern Patagonian Ice Field",
         "BRT": "Bir Tawil", "PGA": "Spratly Islands", "BJN": "Bajo Nuevo Bank", "SER": "Serranilla Bank", "SCR": "Scarborough Reef"}
UNIT_FIX = {"PSX": "PSX"}                      # feature ADM0_A3 -> unit, overriding SOV_A3
PRIMARY = {"FR1": "FRA", "GB1": "GBR", "CH1": "CHN", "US1": "USA", "NL1": "NLD", "DN1": "DNK", "FI1": "FIN", "AU1": "AUS",
           "NZ1": "NZL", "KA1": "KAZ", "CU1": "CUB", "IS1": "ISR"}
UNIT_NAME = {"FR1": "France", "GB1": "United Kingdom", "CH1": "China", "US1": "United States", "NL1": "Netherlands", "DN1": "Denmark",
             "FI1": "Finland", "AU1": "Australia", "NZ1": "New Zealand", "KA1": "Kazakhstan", "CU1": "Cuba", "IS1": "Israel",
             "PSX": "Palestine", "SAH": "Western Sahara", "COD": "DR Congo", "COG": "Republic of the Congo", "CZE": "Czechia",
             "TZA": "Tanzania", "SDS": "South Sudan", "SOL": "Somaliland", "CYN": "Northern Cyprus", "MKD": "North Macedonia",
             "SWZ": "Eswatini", "CIV": "Ivory Coast", "KOS": "Kosovo", "SRB": "Serbia", "RUS": "Russia", "PRK": "North Korea",
             "KOR": "South Korea", "LAO": "Laos", "VNM": "Vietnam", "SYR": "Syria", "IRN": "Iran", "BOL": "Bolivia", "VEN": "Venezuela",
             "MDA": "Moldova", "BRN": "Brunei", "TLS": "Timor-Leste", "BIH": "Bosnia and Herzegovina", "GNB": "Guinea-Bissau",
             "GNQ": "Equatorial Guinea", "CAF": "Central African Republic", "GMB": "The Gambia", "DOM": "Dominican Republic",
             "TWN": "Taiwan", "VAT": "Vatican City", "ARE": "United Arab Emirates", "PNG": "Papua New Guinea", "BWA": "Botswana",
             "ZMB": "Zambia", "ZWE": "Zimbabwe", "NAM": "Namibia", "ESP": "Spain", "PRT": "Portugal", "ITA": "Italy",
             "DEU": "Germany", "AUT": "Austria", "CHE": "Switzerland", "LIE": "Liechtenstein", "UZB": "Uzbekistan",
             "MYS": "Malaysia", "IDN": "Indonesia", "SAU": "Saudi Arabia", "BLR": "Belarus", "UKR": "Ukraine"}
CASPIAN_ETC = "holes in the union of all land units (the Caspian Sea, the Aral Sea and other enclosed lakes)"

# Map types (order = legend order) and colours
KINDS = [("enclave", "True enclave", "#C8322B"), ("enclaved_country", "Enclaved country", "#7B2D8E"),
         ("exclave", "Exclave", "#2F5FA7"), ("semi", "Semi-enclave or semi-exclave", "#2E9A8C"),
         ("pene", "Pene-exclave", "#E0A11B"), ("divided_island", "Divided island", "#5E8C3A"),
         ("historic", "Former enclave", "#8C8478"), ("condominium", "Condominium", "#D46A8C"),
         ("nullius", "Terra nullius", "#1D2128")]
KCOL = {k: c for k, _, c in KINDS}
KNAME = {k: n for k, n, _ in KINDS}
TRI_COL = "#3B3B3B"


def jload(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def dash(v):
    """Remove em and en dashes and double hyphens from text (house style)."""
    if isinstance(v, str):
        v = re.sub(r"(\d)\s*[–—]\s*(\d)", r"\1 to \2", v)
        v = v.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ").replace("–", "-")
        while "--" in v:
            v = v.replace("--", "-")
        return v
    if isinstance(v, list):
        return [dash(x) for x in v]
    if isinstance(v, dict):
        return {(dash(k) if isinstance(k, str) else k): dash(x) for k, x in v.items()}
    return v


def jsave(obj, path, indent=None):
    if os.path.abspath(path).startswith(DATA):
        obj = dash(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"[\W_]+", " ", s).strip()


def get(R, path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f=None):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(float(v)):,}"
    if f == "pc": return f"{round(float(v))}%"
    if f == "pc1": return f"{float(v):.1f}%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    if f == "f3": return f"{float(v):.3f}"
    if f == "k": return f"{float(v) / 1000:.1f}"
    raise ValueError(f)


# ---------- Wikipedia helpers ----------
_W = None


def wiki():
    global _W
    if _W is None:
        _W = jload(os.path.join(RAW, "wiki_pages.json"))
    return _W


def soup(key):
    from bs4 import BeautifulSoup
    return BeautifulSoup(wiki()[key]["html"], "lxml")


def clean_cell(c):
    for x in c.find_all(["sup", "style"]):
        x.decompose()
    return re.sub(r"\s+", " ", c.get_text(" ", strip=True).replace("﻿", "").replace("\xa0", " ")).strip()


def geo_of(c):
    """First geo microformat (decimal 'lat; lon') inside a cell or page, as (lat, lon)."""
    g = c.find(class_="geo")
    if not g:
        return None
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*;\s*(-?\d+(?:\.\d+)?)", g.get_text())
    return (float(m.group(1)), float(m.group(2))) if m else None


def grid(table):
    """A wikitable as a list of rows, rowspans and colspans expanded. Each cell is (text, (lat, lon) or None)."""
    out, pend = [], {}
    for r in table.find_all("tr"):
        cells = r.find_all(["th", "td"], recursive=False)
        row, ci, k = [], 0, 0
        while k < len(cells) or ci in pend:
            if ci in pend:
                v, n = pend[ci]; row.append(v)
                if n > 1: pend[ci] = (v, n - 1)
                else: del pend[ci]
                ci += 1; continue
            c = cells[k]; k += 1
            g = geo_of(c); v = (clean_cell(c), g)
            rs, cs = int(c.get("rowspan", 1) or 1), int(c.get("colspan", 1) or 1)
            for _ in range(cs):
                row.append(v)
                if rs > 1: pend[ci] = (v, rs - 1)
                ci += 1
        out.append(row)
    return out


def wtext(key):
    """Plain text of an article without tables, references and styles."""
    s = soup(key)
    for x in s.find_all(["sup", "style", "table"]):
        x.decompose()
    return re.sub(r"\s+", " ", s.get_text(" ", strip=True).replace("﻿", "").replace("\xa0", " "))


def num(s):
    """First number in a string ('~320', '2,016.41', '0.0183+') or None."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s or "")
    return float(m.group(0).replace(",", "")) if m else None
