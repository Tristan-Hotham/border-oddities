"""Build the paper: fill code/paper_template.tex from data/results.json, add tables and references (with Wikipedia
revision ids), compile with xelatex. Output: release/paper/<NAME>.pdf and .tex (figures f_*.png beside them).
The DOI stays as the 10.5281/zenodo.23873011 placeholder."""
import subprocess
import pandas as pd
from common import *

R = jload(f"{DATA}/results.json"); S = jload(f"{DATA}/site.json")
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Islands_on_Land"
tex = lambda s: str(s).replace("\\", "").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$")

# statements made in words in the paper only
assert R["nei"]["cmp_same"] / R["nei"]["cmp_n"] > .9                      # "nearly every country"
assert R["wiki"]["true_in_ne"] < R["wiki"]["true_enclaves"] / 2           # "most true enclaves are too small for it"


def tfmt(v, f):
    if f == "int": return f"{int(round(float(v))):,}"
    if f == "pc": return f"{round(float(v))}\\%"
    if f == "pc1": return f"{float(v):.1f}\\%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    return tex(str(v))


def area(a):
    if a is None: return ""
    return f"{a:,.0f}" if a >= 100 else f"{a:.1f}" if a >= 1 else f"{a:.3f}"


rows = "".join(f"{tex(r[0])} & {tex(r[1])} & {tex(r[2])} & {area(r[3])} & {r[4]} & {'yes' if r[8] else ''}\\\\\n" for r in S["enclaves"])
TE = ("\\begin{longtable}{p{4.0cm}p{2.7cm}p{2.9cm}rrr}\\caption{True international enclaves in Wikipedia's national-level list: owner, surrounding country, area (km², as listed), "
      "number of separate pieces, and whether Natural Earth 1:10m draws a separate piece within 3 km.}\\label{tab:enclaves}\\\\\\toprule Enclave & Belongs to & Inside & km² & Pieces & In NE\\\\\\midrule\\endfirsthead\n"
      "\\toprule Enclave & Belongs to & Inside & km² & Pieces & In NE\\\\\\midrule\\endhead\n" + rows + "\\bottomrule\\end{longtable}")
E = pd.read_csv(f"{DATA}/ne_exclaves.csv").fillna("")
rows = "".join(f"{tex(r.country)} & {tex(r.wiki_name)} & {tex(r.type)} & {r.area_km2:,.1f} & {tex(r.neighbours)}\\\\\n" for r in E.itertuples())
TN = ("{\\footnotesize\\begin{longtable}{p{2.6cm}p{4.4cm}p{2.6cm}rp{3.4cm}}\\caption{Detached pieces of countries that touch another country in Natural Earth 1:10m, "
      "named after the catalogue entry they contain where there is one.}\\label{tab:ne}\\\\\\toprule Country & Place & Type & km² & Touches\\\\\\midrule\\endfirsthead\n"
      "\\toprule Country & Place & Type & km² & Touches\\\\\\midrule\\endhead\n" + rows + "\\bottomrule\\end{longtable}}")
REV = R["source"]["revids"]
BIB = [("wlist", "List of enclaves and exclaves"), ("wenclave", "Enclave and exclave"), ("wbh", "Baarle-Hertog"), ("wbn", "Baarle-Nassau"),
       ("wib", "India-Bangladesh enclaves"), ("wdahagram", "Dahagram-Angarpota"), ("wtri", "Tripoint"), ("wtrilist", "List of tripoints"), ("wquad", "Quadripoint"),
       ("wcondo", "Condominium (international law)"), ("wnullius", "Terra nullius"), ("wlandlocked", "Landlocked country"),
       ("wland", "List of countries and territories by land borders"), ("wone", "List of countries that border only one other country"),
       ("wpheasant", "Isla de los Faisanes"), ("wbir", "Bir Tawil"), ("wmarket", "Märket"), ("whans", "Hans Island"), ("wmadha", "Madha"), ("wnahwa", "Nahwa"),
       ("wvenn", "Vennbahn")]
TITLE = {"India-Bangladesh enclaves": "Bangladesh-India enclaves", "Isla de los Faisanes": "Pheasant Island", "List of countries and territories by land borders": "List of countries and territories by number of land borders"}
others = sorted(k for k in REV if k not in {b for _, b in BIB} and k not in ("Pene-exclave", "Doubly landlocked country"))
items = ["\\bibitem[Natural Earth(2026)]{naturalearth} Natural Earth (2026) Admin 0 countries (1:10m, 1:50m) and populated places (1:10m). Public domain. \\url{https://www.naturalearthdata.com/}"]
for i, (k, a) in enumerate(BIB):
    t = TITLE.get(a, a)
    items.append(f"\\bibitem[Wikipedia(2026{chr(97 + i)})]{{{k}}} Wikipedia contributors (2026) {tex(t)} (revision {REV[a]}). CC BY-SA 4.0. \\url{{https://en.wikipedia.org/wiki/{t.replace(' ', '_')}}}")
items.append("\\bibitem[Wikipedia(2026v)]{wother} Wikipedia contributors (2026) Articles used for the tour: " +
             "; ".join(f"{tex(TITLE.get(k, k))} (revision {REV[k]})" for k in others) + ". CC BY-SA 4.0.")
items.append("\\bibitem[Wikidata(2026)]{wikidata} Wikidata (2026) Items that are instances of enclave and related types. CC0. \\url{https://www.wikidata.org/}")
TB = "\\begin{thebibliography}{30}\n" + "\n".join(items) + "\n\\end{thebibliography}"

t = open(os.path.join(ROOT, "code", "paper_template.tex"), encoding="utf-8").read()
for k in ("page", "repo"):
    t = t.replace("\\url{{{meta.%s}}}" % k, "\\url{%s}" % R["meta"][k])
t = re.sub(r"\{\{(?!TABLE_|meta\.doi)([^}|]+)(\|(\w+))?\}\}", lambda m: tfmt(get(R, m.group(1)), m.group(3) or "raw"), t)
for k, v in (("ENCLAVES", TE), ("NE", TN), ("BIB", TB)):
    t = t.replace("{{TABLE_%s}}" % k, v)
t = t.replace("\\href{https://doi.org/{{meta.doi}}}{https://doi.org/{{meta.doi}}}", "https://doi.org/\\{\\{DOI\\}\\}")
t = t.replace("\\url{https://doi.org/{{meta.doi}}}", "https://doi.org/\\{\\{DOI\\}\\}")
assert "{{" not in t and "--" not in t and "\u2014" not in t and "\u2013" not in t, re.findall(r"\{\{[^}]*\}\}", t)[:4]
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
log = open(os.path.join(OUT, NAME + ".log"), encoding="utf-8", errors="ignore").read()
print([l for l in log.splitlines() if "Missing character" in l or "undefined" in l.lower() or "Overfull" in l][:12])
for ext in (".aux", ".log", ".out"):
    q = os.path.join(OUT, NAME + ext)
    if os.path.exists(q): os.remove(q)
txt = subprocess.run(["pdftotext", os.path.join(OUT, NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
pages = subprocess.run(["pdfinfo", os.path.join(OUT, NAME + ".pdf")], capture_output=True, text=True).stdout
print("paper", r.returncode, len(txt.split()), "words;", [l for l in pages.splitlines() if l.startswith("Pages")], "dashes:", txt.count("\u2014") + txt.count("\u2013") + txt.count("--"))
