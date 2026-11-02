"""Build index.html from code/page_template.html. Every number in the text is a {{path|format}} token filled from
data/results.json; page data (results, site.json) is embedded; data/world.json, data/borders.json and
data/ne_exclaves.geojson are loaded by the page. Facts stated in words are checked here and in 03_results.py. The
full-screen map snippet (code/fullscreen_snippet.html) is pasted before </body>. 10.5281/zenodo.23873011 and https://blog.tristanhotham.com/2026/10/31/border-oddities/ stay as
placeholders for the publisher."""
import json
from common import *

R = jload(f"{DATA}/results.json")
SITE = jload(f"{DATA}/site.json")
W, T, N, L = R["wiki"], R["tri"], R["nei"], R["land"]

# facts stated in words (page, blog, paper, collage)
assert W["top_owner"] == "Germany" and W["top_parcels_owner"] == "Belgium" and W["largest_land"] == "Sokh" and W["largest_island"] == "Apipé Islands"
assert W["smallest_entry"] == "Rückschlag" and W["span_x"] > 1e7                                   # "more than ten million times"
assert T["leader"] == "China" and T["second"] == "Russia" and T["quad"] == 1 and set(T["kazungula"]["units"]) == {"Botswana", "Namibia", "Zambia", "Zimbabwe"}
assert N["china"] == N["russia"] == 14 and N["top"][2]["name"] == "France" and N["top"][3]["name"] == "Brazil"
assert L["doubly"] == ["Liechtenstein", "Uzbekistan"] and L["liechtenstein_nb"] == ["Austria", "Switzerland"]
assert L["uzbekistan_nb"] == ["Afghanistan", "Kazakhstan", "Kyrgyzstan", "Tajikistan", "Turkmenistan"]
assert R["ne"]["most_name"] == "United Kingdom" and R["ne"]["largest"] == "United States" and R["ne"]["smallest"] == "Nicaragua"
assert R["borders"]["russia_km"] < R["borders"]["wiki_russia_km"] and R["borders"]["china_km"] < R["borders"]["wiki_china_km"]
assert {"Lesotho", "San Marino", "Vatican City"} <= set(N["one"]) and "Canada" in N["one"] and "Denmark" in N["one"]
assert R["chhits"]["counter_bd"] + R["chhits"]["counter_in"] == 24
assert R["baarle"]["belgian"] == 22 and R["baarle"]["dutch"] == 8 and R["baarle"]["smallest"] == "H7"
assert W["unplaced"]["semi"] == 1


def build():
    tpl = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()
    html = re.sub(r"\{\{(?!DOI\}\}|BLOG_URL\}\})([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(R, m.group(1)), m.group(3)), tpl)
    left = re.findall(r"\{\{[^}]*\}\}", html)
    assert set(left) <= {"10.5281/zenodo.23873011", "https://blog.tristanhotham.com/2026/10/31/border-oddities/"}, left[:5]
    J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("/*RESULTS*/", J(R)).replace("/*SITE*/", J(SITE))
    html = html.replace("/*FULLSCREEN*/", open(os.path.join(ROOT, "code", "fullscreen_snippet.html"), encoding="utf-8").read())
    vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", html, flags=re.S)
    vis = re.sub(r"<[^>]+>", " ", vis)
    for bad in ("—", "–", "--", "DSIT", "DCMS", "civil serv", "nan", "None"):
        assert not re.search(re.escape(bad) if bad not in ("nan", "None") else r"\b" + bad + r"\b", vis), bad
    for scr in re.findall(r"<script>(.*?)</script>", html, flags=re.S):
        for bad in ("—", "–"):
            assert bad not in scr, bad
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    print("index.html", len(html.encode()) // 1024, "KB")


if __name__ == "__main__":
    build()
