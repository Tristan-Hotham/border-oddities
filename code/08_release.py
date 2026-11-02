"""Blog post and meta (release/blog), Zenodo files and metadata (release/zenodo).
10.5281/zenodo.23873011, https://doi.org/10.5281/zenodo.23873011 and https://blog.tristanhotham.com/2026/10/31/border-oddities/ stay as placeholders for the publisher."""
import json as _json, shutil, zipfile, importlib.util
from common import *

R = jload(f"{DATA}/results.json"); S = jload(f"{DATA}/site.json")
REL = os.path.join(ROOT, "release"); NAME = "Hotham_Islands_on_Land"
KEEP = {"DOI", "DOI_URL", "BLOG_URL"}

# the page build checks the shared facts; these are numbers written in words or alt text in the blog and collage
spec = importlib.util.spec_from_file_location("b", os.path.join(ROOT, "code", "04_build_site.py")); spec.loader.exec_module(importlib.util.module_from_spec(spec))
w, t, n = R["wiki"], R["tri"], R["nei"]
assert (w["mapped"], t["n"], w["true_enclaves"], w["true_parcels"]) == (107, 167, 42, 85)
assert [(o["owner"], o["n"]) for o in w["owners"][:5]] == [("Germany", 6), ("Azerbaijan", 4), ("Cyprus", 4), ("Argentina", 3), ("Tajikistan", 3)]
assert [(r["name"], r["n"]) for r in n["top"][:6]] == [("Russia", 14), ("China", 14), ("France", 11), ("Brazil", 10), ("DR Congo", 9), ("Germany", 9)]
assert [(r["name"], r["n"]) for r in t["top"][:4]] == [("China", 15), ("Russia", 10), ("Austria", 9), ("DR Congo", 9)]
B = [s for s in S["sizes"] if s[0] == "Baarle parcels"]; C = [s for s in S["sizes"] if s[0] == "Former India and Bangladesh enclaves"]
assert len(B) == 30 and 2000 < min(s[2] for s in B) * 1e6 < 3000 and 1.4 < max(s[2] for s in B) < 1.6
assert len(C) == 189 and 900 < min(s[2] for s in C) * 1e6 < 1100 and 15 < max(s[2] for s in C) < 17
assert R["wiki"]["lesotho_km2"] == 30355

post = open(os.path.join(ROOT, "code", "blog_template.html"), encoding="utf-8").read()
post = re.sub(r"\{\{(?!IMG|DOI_URL|BLOG_URL|DOI\}\})([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(R, m.group(1)), m.group(3)), post)
used = re.findall(r"\{\{IMG\|([^|]+)\|", post)
assert 5 <= len(used) <= 8, len(used)
assert all(re.search(r"^\{\{IMG\|" + re.escape(u), post, re.M) for u in used) and "wp:image" not in post
for img in used:
    assert os.path.exists(f"{REL}/blog/{img}"), img
for fn in os.listdir(f"{REL}/blog"):
    if fn.startswith("b_") and fn not in used:
        os.remove(f"{REL}/blog/{fn}")
assert set(re.findall(r"\{\{([^|}]+)\}\}", post)) <= KEEP, set(re.findall(r"\{\{([^|}]+)\}\}", post))
vis = re.sub(r"<!--.*?-->", "", post, flags=re.S)
for bad in ("\u2014", "\u2013", "--", "DSIT", "DCMS", "civil serv"):
    assert bad not in vis, bad
open(f"{REL}/blog/post.html", "w", encoding="utf-8").write(post)
words = len(re.sub(r"<[^>]+>|\{\{IMG\|[^}]*\}\}", " ", vis).split())
meta = {"title": "The world's strangest borders: enclaves, exclaves, tripoints and a front door in two countries",
        "slug": "border-oddities",
        "excerpt": f"I mapped every enclave, exclave and border oddity in Wikipedia's lists and every tripoint on Natural Earth's map. There are {w['true_enclaves']} true enclaves in {w['true_parcels']} pieces, most too small for the map to see.",
        "seo_description": f"A map of the world's strangest borders: {w['true_enclaves']} true enclaves, Baarle, the India and Bangladesh swap, {t['n']} tripoints and Bir Tawil.",
        "tags": ["borders", "enclaves", "exclaves", "maps", "data visualisation", "political geography", "Baarle", "Natural Earth"],
        "header_alt": f"Title card reading 'The world's strangest borders' with 'strangest' in red, beside a world map dotted with coloured circles for enclaves and other oddities and small black triangles for tripoints. Text: {w['true_enclaves']} true enclaves in {w['true_parcels']} pieces, {t['n']} tripoints, a quadripoint that is not, and an island that changes hands every six months."}
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
jsave(meta, f"{REL}/blog/meta.json", indent=2)

# Zenodo
Z = f"{REL}/zenodo"; os.makedirs(Z, exist_ok=True)
for fn in os.listdir(Z):
    os.remove(os.path.join(Z, fn))
shutil.copy(f"{REL}/paper/{NAME}.pdf", f"{Z}/{NAME}.pdf")
zp = f"{Z}/border-oddities_data_and_code.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for d in ("code", "data"):
        for fn in sorted(os.listdir(os.path.join(ROOT, d))):
            if fn.endswith(".pyc") or fn == "__pycache__":
                continue
            z.write(os.path.join(ROOT, d, fn), f"border-oddities/{d}/{fn}")
    for fn in ("README.md", "LICENSE"):
        z.write(os.path.join(ROOT, fn), f"border-oddities/{fn}")
    z.write(os.path.join(ROOT, "reddit", "collage.py"), "border-oddities/reddit/collage.py")
tex = open(f"{REL}/paper/{NAME}.tex", encoding="utf-8").read()
ab = re.search(r"\\begin\{center\}\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n\\textbf\{Keywords", tex, re.S).group(1)
ab = ab.replace("\\%", "%").replace("\\&", "&")
zmeta = {"title": "Islands on Land: Enclaves, Exclaves, Tripoints and Other Oddities of the World's Borders",
         "upload_type": "publication", "publication_type": "workingpaper",
         "description": f"<p>{ab}</p><p>Interactive version: <a href=\"{PAGE}\">{PAGE}</a>. Data and code: <a href=\"{REPO}\">{REPO}</a>. Blog post: {BLOG}.</p><p>Sources: English Wikipedia (CC BY-SA 4.0; tables derived from it are shared under the same licence), Wikidata (CC0), Natural Earth (public domain).</p>",
         "creators": [{"name": "Hotham, Tristan", "affiliation": "Independent researcher", "orcid": "0000-0003-4931-9349"}],
         "keywords": ["political geography", "enclaves", "exclaves", "tripoints", "land borders", "landlocked countries", "Natural Earth", "Wikipedia", "open data", "maps"],
         "license": "cc-by-4.0", "language": "eng",
         "related_identifiers": [{"identifier": REPO, "relation": "isSupplementedBy", "resource_type": "software"},
                                 {"identifier": PAGE, "relation": "isSupplementedBy", "resource_type": "other"},
                                 {"identifier": "https://en.wikipedia.org/wiki/List_of_enclaves_and_exclaves", "relation": "isDerivedFrom", "resource_type": "other"},
                                 {"identifier": "https://www.naturalearthdata.com/", "relation": "isDerivedFrom", "resource_type": "dataset"}],
         "files": sorted(os.listdir(Z))}
sj = _json.dumps(zmeta, ensure_ascii=False) + _json.dumps(meta, ensure_ascii=False)
assert "\u2014" not in sj and "\u2013" not in sj and "--" not in sj
jsave(zmeta, f"{Z}/metadata.json", indent=2)
print("blog words", words, "figures", len(used), "; zenodo", sorted(os.listdir(Z)), os.path.getsize(zp) // 1024, "KB zip")
