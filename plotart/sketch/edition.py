"""Editions like Art Blocks / fxhash: traits from feature(), rarities, metadata and a gallery page.

A variant is one seed. feature("Palette", "nacht") records its traits; over many seeds the share of
each value shows how rare it is. The metadata follow the common gallery/NFT layout (name,
description, image, attributes) – useful for one's own website as well.
"""
from __future__ import annotations

import html
import json
import time
from pathlib import Path

from .runner import execute

MISSING = "–"      # value of a trait a variant does not set


def collect_features(source: str, seeds, params: dict | None = None,
                     budget_s: float | None = None) -> tuple[list[dict], bool]:
    """Run the sketch for every seed → ([{"seed", "features"} or {"seed", "error"}], finished)."""
    entries, t0 = [], time.perf_counter()
    seeds = list(seeds)
    for k, seed in enumerate(seeds):
        sk, _log, err, _ms = execute(source, params, int(seed))
        entries.append({"seed": int(seed), "error": err["message"]} if err else
                       {"seed": int(seed), "features": dict(sk.features)})
        if budget_s is not None and time.perf_counter() - t0 > budget_s and k < len(seeds) - 1:
            return entries, False
    return entries, True


def feature_stats(entries: list[dict]) -> dict:
    """Rarities: per trait the values with count and percent (rarest first), per seed a rarity score
    (sum of 1 / share over all traits – higher = rarer) and the rank (1 = rarest)."""
    ok = [e for e in entries if "features" in e]
    n = len(ok)
    names: list[str] = []
    for e in ok:
        names += [k for k in e["features"] if k not in names]
    counts = {name: {} for name in names}
    for e in ok:
        for name in names:
            v = e["features"].get(name, MISSING)
            counts[name][json.dumps(v, ensure_ascii=False)] = counts[name].get(json.dumps(v, ensure_ascii=False), 0) + 1
    traits = {name: sorted(({"value": json.loads(v), "count": c, "percent": round(100 * c / n, 1)}
                            for v, c in vals.items()), key=lambda t: (t["count"], str(t["value"])))
              for name, vals in counts.items()}
    scores = {}
    for e in ok:
        scores[e["seed"]] = round(sum(n / counts[name][json.dumps(e["features"].get(name, MISSING), ensure_ascii=False)]
                                      for name in names), 3)
    order = sorted(scores, key=lambda s: (-scores[s], s))
    return {"count": n, "traits": traits, "scores": scores, "ranks": {s: i + 1 for i, s in enumerate(order)}}


def token_metadata(entry: dict, number: int, size: int, title: str, description: str, artist: str,
                   image: str | None, stats: dict) -> dict:
    """Metadata of one variant in the usual gallery/NFT layout."""
    meta = {"name": f"{title} #{number}", "description": description, "edition": number, "edition_size": size,
            "seed": entry["seed"],
            "attributes": [{"trait_type": k, "value": v} for k, v in entry["features"].items()],
            "rarity_score": stats["scores"].get(entry["seed"]), "rarity_rank": stats["ranks"].get(entry["seed"])}
    if image:
        meta["image"] = image
    if artist:
        meta["artist"] = artist
    return meta


def write_edition(out_dir: str | Path, entries: list[dict], title: str, description: str = "", artist: str = "",
                  images: dict | None = None) -> dict:
    """metadata/<seed>.json, edition.json and galerie.html in out_dir. images: seed → file name."""
    out = Path(out_dir)
    images = images or {}
    ok = [e for e in entries if "features" in e]
    stats = feature_stats(entries)
    (out / "metadata").mkdir(parents=True, exist_ok=True)
    tokens = []
    for number, e in enumerate(ok, 1):
        meta = token_metadata(e, number, len(ok), title, description, artist, images.get(e["seed"]), stats)
        (out / "metadata" / f"{e['seed']}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                                            encoding="utf-8")
        tokens.append(meta)
    summary = {"title": title, "description": description, "artist": artist, "count": len(ok),
               "traits": stats["traits"], "tokens": tokens}
    (out / "edition.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "galerie.html").write_text(gallery_html(summary), encoding="utf-8")
    return stats


def gallery_html(summary: dict) -> str:
    """Self-contained gallery page: grid, filters per trait, sorting by number or rarity, detail view."""
    data = json.dumps(summary, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(summary.get("title") or "Edition")
    return _GALLERY.replace("__GALERIE_TITEL__", title).replace("__GALERIE_DATEN__", data)


_GALLERY = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__GALERIE_TITEL__</title>
<style>
  [hidden] { display: none !important; }
  :root { --bg: #f6f5f1; --card: #fff; --ink: #1d1d1f; --muted: #6b6b70; --line: #e2e0da; --accent: #1f5fbf; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #121216; --card: #1c1c22; --ink: #ececf0; --muted: #9a9aa4; --line: #2c2c34; --accent: #7fa6e0; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  header { max-width: 1200px; margin: 0 auto; padding: 32px 16px 8px; }
  h1 { margin: 0 0 4px; font-size: 28px; letter-spacing: -0.01em; }
  .by { color: var(--muted); margin: 0 0 12px; }
  .desc { max-width: 720px; white-space: pre-line; }
  .bar { max-width: 1200px; margin: 0 auto; padding: 12px 16px; display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; }
  .bar label { font-size: 13px; color: var(--muted); display: flex; gap: 6px; align-items: center; }
  select { font: inherit; font-size: 13px; padding: 4px 6px; border-radius: 6px; border: 1px solid var(--line); background: var(--card); color: var(--ink); }
  .count { margin-left: auto; font-size: 13px; color: var(--muted); }
  main { max-width: 1200px; margin: 0 auto; padding: 8px 16px 48px; display: grid; gap: 16px;
         grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; cursor: pointer;
          text-align: left; padding: 0; color: inherit; font: inherit; }
  .card:hover { border-color: var(--accent); }
  .card img { display: block; width: 100%; aspect-ratio: 1; object-fit: contain; background: var(--bg); }
  .card .meta { padding: 8px 10px; display: flex; justify-content: space-between; font-size: 13px; }
  .card .rank { color: var(--muted); }
  dialog { border: none; border-radius: 12px; padding: 0; max-width: min(1000px, 94vw); width: 100%;
           background: var(--card); color: var(--ink); }
  dialog::backdrop { background: rgba(0, 0, 0, .6); }
  .detail { display: grid; grid-template-columns: minmax(0, 3fr) minmax(220px, 2fr); }
  .detail img { width: 100%; display: block; background: var(--bg); }
  .info { padding: 18px; }
  .info h2 { margin: 0 0 4px; font-size: 20px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
  td { padding: 5px 0; border-top: 1px solid var(--line); vertical-align: top; }
  td.p { text-align: right; color: var(--muted); white-space: nowrap; }
  .close { position: absolute; top: 8px; right: 10px; background: var(--card); border: 1px solid var(--line);
           border-radius: 50%; width: 32px; height: 32px; cursor: pointer; color: var(--ink); font-size: 16px; }
  @media (max-width: 700px) { .detail { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1 id="title"></h1>
  <p class="by" id="by"></p>
  <div class="desc" id="desc"></div>
</header>
<div class="bar" id="bar">
  <label>Sortieren <select id="sort"><option value="nr">nach Nummer</option><option value="rare">seltenste zuerst</option></select></label>
  <span class="count" id="count"></span>
</div>
<main id="grid"></main>
<dialog id="dlg"><button class="close" id="close" aria-label="Schließen">✕</button>
  <div class="detail"><img id="dImg" alt=""><div class="info"><h2 id="dName"></h2><div class="by" id="dSub"></div>
  <table id="dTraits"></table></div></div></dialog>
<script type="application/json" id="data">__GALERIE_DATEN__</script>
<script>
const E = JSON.parse(document.getElementById("data").textContent);
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const pct = (p) => p == null ? "" : p.toLocaleString("de-AT", { maximumFractionDigits: 1 }) + " %";
const val = (t, name) => { const a = t.attributes.find((x) => x.trait_type === name); return a ? a.value : "–"; };
const share = {};
for (const [name, list] of Object.entries(E.traits)) for (const v of list) share[name + "\\u0000" + JSON.stringify(v.value)] = v.percent;
$("title").textContent = E.title || "Edition";
$("by").textContent = [E.artist, E.count + " Varianten"].filter(Boolean).join(" · ");
$("desc").textContent = E.description || "";
const filters = {};
for (const [name, list] of Object.entries(E.traits)) {
  const l = document.createElement("label");
  l.textContent = name + " ";
  const s = document.createElement("select");
  s.innerHTML = '<option value="">alle</option>' + list.slice().sort((a, b) => String(a.value).localeCompare(String(b.value), "de"))
    .map((v) => `<option value="${esc(JSON.stringify(v.value))}">${esc(v.value)} (${v.count})</option>`).join("");
  s.onchange = () => { filters[name] = s.value; render(); };
  l.appendChild(s);
  $("bar").insertBefore(l, $("count"));
}
$("sort").onchange = render;
function render() {
  let list = E.tokens.filter((t) => Object.entries(filters).every(([n, v]) => !v || JSON.stringify(val(t, n)) === v));
  if ($("sort").value === "rare") list = list.slice().sort((a, b) => a.rarity_rank - b.rarity_rank);
  $("count").textContent = `${list.length} von ${E.tokens.length}`;
  $("grid").innerHTML = list.map((t) => `<button class="card" data-seed="${t.seed}">` +
    (t.image ? `<img loading="lazy" src="${esc(t.image)}" alt="${esc(t.name)}">` : "") +
    `<div class="meta"><span>#${t.edition} · Seed ${t.seed}</span><span class="rank">Rang ${t.rarity_rank}</span></div></button>`).join("");
}
$("grid").onclick = (e) => {
  const card = e.target.closest(".card");
  if (!card) return;
  const t = E.tokens.find((x) => String(x.seed) === card.dataset.seed);
  $("dImg").src = t.image || ""; $("dImg").hidden = !t.image;
  $("dName").textContent = t.name;
  $("dSub").textContent = `Seed ${t.seed} · Seltenheit: Rang ${t.rarity_rank} von ${E.tokens.length}`;
  $("dTraits").innerHTML = t.attributes.map((a) => `<tr><td>${esc(a.trait_type)}</td><td>${esc(a.value)}</td>` +
    `<td class="p">${pct(share[a.trait_type + "\\u0000" + JSON.stringify(a.value)])}</td></tr>`).join("");
  $("dlg").showModal();
};
$("close").onclick = () => $("dlg").close();
$("dlg").onclick = (e) => { if (e.target === $("dlg")) $("dlg").close(); };
render();
</script>
</body>
</html>
"""
