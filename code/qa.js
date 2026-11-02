// QA: open index.html at desktop and phone widths, log console errors, take screenshots to qa/.
// Run from the study root with a static server (python3 -m http.server 8961; set PORT to change).
const { chromium } = require("playwright");
// MapLibre from a local npm copy (the CDN is not reachable from the build container); tiles, labels and fonts are blocked here,
// so the check also shows that the page works without them.
const ML = process.env.MAPLIBRE_DIST || "/tmp/ml/node_modules/maplibre-gl/dist";
(async () => {
  const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  const errs = [];
  for (const [nm, vw, vh] of (process.env.ONLY ? [[process.env.ONLY, process.env.ONLY === "phone" ? 390 : 1280, 900]] : [["desktop", 1280, 900], ["phone", 390, 844]])) {
    const p = await b.newPage({ viewport: { width: vw, height: vh }, deviceScaleFactor: nm === "phone" ? 2 : 1 });
    await p.route(/arcgisonline|googleapis|gstatic|openfreemap/, r => r.abort());
    await p.route(/maplibre-gl\.js$/, r => r.fulfill({ path: ML + "/maplibre-gl.js" }));
    await p.route(/maplibre-gl\.css$/, r => r.fulfill({ path: ML + "/maplibre-gl.css" }));
    p.on("console", m => { if (m.type() === "error" && !/ERR_FAILED|net::|Failed to fetch|AJAXError/.test(m.text())) errs.push(nm + ": " + m.text()); });
    p.on("pageerror", e => errs.push(nm + " pageerror: " + e.message));
    await p.goto("http://localhost:" + (process.env.PORT || 8961) + "/index.html", { waitUntil: "load" });
    for (let k = 0; k < 150 && !(await p.evaluate(() => typeof ready !== "undefined" && ready && window.geoReady)); k++) await p.waitForTimeout(500);
    console.log(nm, "map ready:", await p.evaluate(() => [typeof ready !== "undefined" && ready, document.getElementById("loading") === null, !!window.geoReady]));
    await p.waitForTimeout(2000);
    await p.screenshot({ path: `qa/${nm}_top.png` });
    const shot = async (sel, f) => { await p.locator(sel).scrollIntoViewIfNeeded(); await p.waitForTimeout(700);
      try { await p.locator(sel).screenshot({ path: `qa/${nm}_${f}.png`, timeout: 8000, animations: "disabled" }); } catch (e) { await p.screenshot({ path: `qa/${nm}_${f}.png`, fullPage: false }); } };
    const idle = async () => p.evaluate(() => new Promise(r => { map.once("idle", r); map.triggerRepaint(); setTimeout(r, 5000); }));
    const drawn = async (l) => { await idle(); return p.evaluate(l => map.queryRenderedFeatures({ layers: [l] }).length, l); };
    await shot("#atlas", "map");
    console.log(nm, "drawn: odd", await drawn("odd"), "tri", await drawn("tri"), "parts", await drawn("parts"), "land", await drawn("land"));
    // tour: first stop, a middle one, the last
    for (const [i, f] of [[0, "tour_baarle"], [1, "tour_cooch"], [8, "tour_kaliningrad"], [11, "tour_madha"], [14, "tour_market"]]) {
      await p.evaluate(i => goStop(i), i); await p.waitForTimeout(3200); await shot("#atlas", f);
    }
    // kind filter: hide pene-exclaves
    await p.evaluate(() => goStop(-1)); await p.waitForTimeout(2500);
    await p.click('#kindRow .btn:nth-of-type(5)'); await p.waitForTimeout(600);
    console.log(nm, "odd drawn after hiding one kind:", await drawn("odd"));
    await p.click('#kindRow .btn:nth-of-type(5)');
    // popup on a table row
    await p.locator("#encTable tr[data-i]").nth(11).click(); await p.waitForTimeout(3000);
    console.log(nm, "popup:", (await p.textContent(".maplibregl-popup-content").catch(() => "none")).slice(0, 140));
    await shot("#atlas", "popup_baarle");
    await p.click(".lyrBtn"); await p.waitForTimeout(300); await shot("#map", "layers_panel"); await p.click(".lyrBtn");
    for (const c of ["ownerChart", "sizeChart", "encTable", "triChart", "neiChart", "conTable"]) await shot("#" + c, c);
    if (nm === "phone") {
      await p.click("#theme"); await p.waitForTimeout(1500); await shot("#atlas", "dark_map"); await shot("#sizeChart", "dark_size");
      await p.locator("#atlas").scrollIntoViewIfNeeded(); await p.click(".mfs-btn"); await p.waitForTimeout(1500); await p.screenshot({ path: `qa/${nm}_fullscreen.png` });
      await p.click(".mfs-btn"); await p.waitForTimeout(500);
    } else {
      await p.locator("#atlas").scrollIntoViewIfNeeded(); await p.click(".mfs-btn"); await p.waitForTimeout(1500); await p.screenshot({ path: `qa/${nm}_fullscreen.png` });
      await p.click(".mfs-btn"); await p.waitForTimeout(500);
    }
    const ov = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    console.log(nm, "horizontal overflow px:", ov);
    await p.close();
  }
  // no MapLibre at all (CDN blocked): the page must still render its text and charts
  const q = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await q.route(/arcgisonline|googleapis|gstatic|openfreemap|maplibre/, r => r.abort());
  q.on("pageerror", e => errs.push("nomap pageerror: " + e.message));
  await q.goto("http://localhost:" + (process.env.PORT || 8961) + "/index.html", { waitUntil: "load" }); await q.waitForTimeout(1500);
  console.log("no maplibre:", await q.textContent("#loading"), "| charts:", await q.evaluate(() => document.querySelectorAll(".chart svg").length));
  await q.locator("#atlas").screenshot({ path: "qa/nomap_atlas.png" });
  await q.close();
  console.log("errors:", errs.length ? errs : "none");
  await b.close();
})();
