# The world's strangest borders: enclaves, exclaves, tripoints and other oddities

A located catalogue of every national-level enclave, exclave, semi-enclave, pene-exclave, divided island, condominium and piece of unclaimed land in English Wikipedia's lists, compared with what can be computed from Natural Earth's 1:10m countries: neighbours, border lengths, 167 tripoints, detached pieces of countries and landlocked status. With a tour of 15 of the strangest cases, from Baarle to Bir Tawil.

Interactive page: https://maps.tristanhotham.com/border-oddities/
Paper: https://doi.org/10.5281/zenodo.23873011
Blog post: https://blog.tristanhotham.com/2026/10/31/border-oddities/

## Headline results

- Wikipedia lists 42 true international enclaves (surrounded by one country and belonging to another) in 85 pieces, owned by 24 countries. Germany owns the most entries (6: Büsingen and 5 Vennbahn pieces), Belgium the most pieces (22, at Baarle). Plus 3 enclaved countries, 4 exclaves that are not enclaves, 17 semi-enclaves and semi-exclaves, 62 pene-exclaves and 36 divided islands.
- Sizes: from Rückschlag (16,000 m²) and Baarle's parcel H7 (2,469 m²) to Sokh (234 km², the largest on land) and Lesotho (30,355 km²).
- Nested: Baarle has 22 Belgian and 8 Dutch parcels and the border runs through about 54 homes. The India and Bangladesh enclaves (102 Indian, 71 Bangladeshi, 24 counter-enclaves and the counter-counter-enclave Dahala Khagrabari, 6,880 m²) were swapped on 31 July 2015.
- Tripoints: 167 in Natural Earth, plus one quadripoint at Kazungula, where Wikipedia's sources describe two tripoints about 100 to 150 m apart. China has the most (15), then Russia (10).
- Neighbours: China and Russia 14 each, France 11, Brazil 10. Natural Earth and Wikipedia agree for 150 of 160 countries. 18 countries have one neighbour.
- Landlocked: 45 (Caspian as a lake); doubly landlocked: Liechtenstein and Uzbekistan.
- Natural Earth draws only 17 of the 42 true enclaves; it contains 50 detached pieces of countries that touch another country, 13 of them enclaves.

All borders are Natural Earth's de facto lines and Wikipedia's descriptions. Neither is an endorsement of any territorial claim.

## Files

| File | What it is |
|---|---|
| `index.html` | The interactive page (built by `code/04_build_site.py`; results and page data embedded; `data/world.json`, `data/borders.json` and `data/ne_exclaves.geojson` loaded by the page). |
| `header.png` | Social card, 1200 x 630. |
| `data/oddities.csv` | The catalogue: 188 entries (107 mapped) with type, owner, surrounding country, area, pieces, coordinates and their source, Wikipedia revision id, and whether Natural Earth draws it (CC BY-SA 4.0). |
| `data/baarle_parcels.csv` | Baarle's 30 parcels with areas and the homes the border runs through (CC BY-SA 4.0). |
| `data/india_bangladesh_chhits.csv` | Wikipedia's tables of the former India and Bangladesh enclaves (CC BY-SA 4.0). |
| `data/wikidata_enclaves.csv` | Wikidata items typed as enclaves, with the layer each falls into (CC0). |
| `data/countries_borders.csv` | Per Natural Earth country: neighbours, land border, sea coast and lake shore length, tripoints, landlocked and doubly landlocked, detached pieces, and Wikipedia's neighbour count. |
| `data/border_pairs.csv` | Length of every land border between two countries in Natural Earth. |
| `data/tripoints.csv` | Every point on the boundary of three or more units, with the units and whether a zone is involved. |
| `data/ne_exclaves.csv`, `data/ne_exclaves.geojson` | The 50 detached pieces of countries that touch another country, with type, area, neighbours and name. |
| `data/results.json` | Every number used in the page, paper, blog, collage and post. |
| `data/site.json`, `data/world.json`, `data/borders.json` | Page data. |
| `code/` | Scripts, run in order (below), and the page, paper and blog templates. |
| `release/` | Paper PDF and LaTeX source with figures (`paper/`), blog post, figures and meta (`blog/`), Zenodo files (`zenodo/`). |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |
| `qa/` | Screenshots of the page at desktop and phone widths. |

## Method in brief

- Catalogue: the national-level tables and bulleted lists of Wikipedia's List of enclaves and exclaves; 16 pockets of high seas left out; list items placed by coordinates in the item, the place's own infobox, or the Natural Earth piece that is the place, otherwise unmapped. 98 quoted facts are checked word for word against the saved articles.
- Countries: Natural Earth 1:10m admin-0 features grouped by sovereignty (dependencies with their sovereign), de facto units kept, Palestine separate, indeterminate zones (Bir Tawil, Siachen, the Cyprus buffer zone and others) not countries.
- Topology: shared vertices give each edge the countries on its two sides. Shared edges are land border (geodesic length); unshared edges are coast, or lake shore if they face water enclosed by land (the Caspian, 397,054 km²). Tripoint: a vertex on three countries' boundaries.
- Detached pieces: polygons joined where they share an edge; main piece the largest, unless the capital's piece is at least half its size; other pieces touching another country are enclaves, landlocked exclaves, coastal exclaves or pieces of shared islands.
- Caveats: Wikipedia is crowd-sourced and its categories overlap; Natural Earth is generalised (a millimetre at 1:10m is 10 km), misses small enclaves and short borders, and draws de facto lines.

## How to rerun

Needs Python 3 with numpy, pandas, shapely, pyproj, beautifulsoup4, lxml, matplotlib and fontTools, xelatex and pdftotext; node with Playwright for `code/qa.js`. Raw inputs are read in place (paths in `code/common.py`): `raw/wiki_pages.json` and `raw/wd_enclaves.tsv`, and Natural Earth in `/home/claude/newdata/raw/geo/`. Intermediate files go to `/dev/shm/borderoddities/work` (set `BOTMP` to change).

```
python3 code/01_wiki.py         # Wikipedia tables, lists, infobox coordinates, checked facts; Wikidata filter
python3 code/02_geo.py          # Natural Earth topology: neighbours, borders, tripoints, detached pieces, landlocked
python3 code/03_results.py      # catalogue, results.json, data tables, tour and insets
python3 code/04_build_site.py   # index.html
python3 code/05_figures.py      # header, blog and paper figures
python3 code/06_paper.py        # paper PDF
python3 reddit/collage.py       # collage
python3 code/07_readme.py       # README, LICENSE, Reddit post
python3 code/08_release.py      # blog post, Zenodo files
```

## Sources and licences

- Wikipedia contributors, "List of enclaves and exclaves" and 34 other English Wikipedia articles (revision ids in `data/results.json`), CC BY-SA 4.0. The tables derived from them (`data/oddities.csv`, `data/baarle_parcels.csv`, `data/india_bangladesh_chhits.csv`) are shared under CC BY-SA 4.0.
- Wikidata, items typed as enclaves, CC0.
- Natural Earth 1:10m and 1:50m admin-0 countries and 1:10m populated places (https://www.naturalearthdata.com/). Public domain.
- Map labels on the page: OpenFreeMap, © OpenMapTiles, © OpenStreetMap contributors. Hillshade tiles: Esri.

## Citation

Hotham, T. (2026) Islands on land: enclaves, exclaves, tripoints and other oddities of the world's borders. Zenodo. https://doi.org/10.5281/zenodo.23873011

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
