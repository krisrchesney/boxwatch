#!/usr/bin/env python3
"""Build catalog.json: a static snapshot of BoardGameGeek's top-ranked games.

The hosted demo has no server (and so no BGG token), but its Search box still
works by looking names up in this file. Every field comes from the official BGG
XML API under *your* registered token; the community ranking CSV is only used to
learn which game ids are top-ranked.

    # token goes in the environment (or bgg_token.txt next to server.py)
    BGG_API_TOKEN=... python scripts/build_catalog.py --ranking 2026-10-28.csv --top 500

The ranking CSV is any dated file from https://github.com/beefsack/bgg-ranking-historicals
(columns ID, Name, Year, Rank, ...). The script is resumable: finished games are
cached in scripts/.catalog_cache.json, so re-running picks up where it stopped.
Use --assemble-only to write catalog.json from whatever is cached so far.

Be polite to BGG: one request every couple of seconds, and a 500-game build makes
about 525 requests, so expect it to take 25-30 minutes.

BGG's terms require crediting BoardGameGeek by name and showing the "Powered by BGG"
logo on public pages, and forbid modifying the data. Don't strip the "source" block.
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server  # noqa: E402  (reuse the app's BGG client and parsing)

CACHE_PATH = os.path.join(ROOT, "scripts", ".catalog_cache.json")
OUT_PATH = os.path.join(ROOT, "catalog.json")
DELAY_SECONDS = 2.5
BATCH = 20  # BGG caps /thing at 20 ids per request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def polite(fn, *args):
    """Call a BGG helper, backing off when BGG says slow down or has a hiccup."""
    for attempt in range(6):
        try:
            return fn(*args)
        except RuntimeError as e:
            msg = str(e)
            if any(code in msg for code in ("HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504")):
                wait = 20 * (attempt + 1)
                print(f"  BGG pushed back ({msg[:40]}); waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("BGG kept refusing after 6 attempts; try again later")


def top_ids(ranking_csv, n):
    rows = []
    with open(ranking_csv, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if str(row.get("Rank", "")).isdigit():
                rows.append((int(row["Rank"]), row["ID"]))
    rows.sort()
    return [game_id for _, game_id in rows[:n]]


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, CACHE_PATH)


def fetch_things(ids, cache):
    todo = [i for i in ids if "thing" not in cache.get(i, {})]
    print(f"stats: {len(ids) - len(todo)} cached, {len(todo)} to fetch", flush=True)
    for k in range(0, len(todo), BATCH):
        chunk = todo[k:k + BATCH]
        things = polite(server.bgg_things, chunk)
        for i in chunk:
            if i in things:
                cache.setdefault(i, {})["thing"] = things[i]
        save_cache(cache)
        print(f"  stats {min(k + BATCH, len(todo))}/{len(todo)}", flush=True)
        time.sleep(DELAY_SECONDS)


def fetch_dims(ids, cache):
    todo = [i for i in ids if "thing" in cache.get(i, {}) and "dims" not in cache[i]]
    print(f"dimensions: {len(ids) - len(todo)} cached, {len(todo)} to fetch", flush=True)
    for n, i in enumerate(todo, 1):
        versions, base_name = polite(server.bgg_thing_versions, i)
        best = server.pick_best_version(versions, base_name)
        cache[i]["dims"] = [best["length"], best["width"], best["depth"]] if best else None
        if n % 5 == 0 or n == len(todo):
            save_cache(cache)
            print(f"  dimensions {n}/{len(todo)}", flush=True)
        time.sleep(DELAY_SECONDS)


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def assemble(ids, cache, snapshot):
    games = []
    for i in ids:
        entry = cache.get(i)
        if not entry or "thing" not in entry:
            continue
        t = entry["thing"]
        if t.get("rank") is None:
            continue
        games.append({
            "id": int(i),
            "n": t["name"],
            "y": to_int(t.get("yearpublished")),
            "mn": to_int(t.get("minplayers")),
            "mx": to_int(t.get("maxplayers")),
            "best": t.get("bestPlayers"),
            "t": to_int(t.get("playingtime")),
            "r": t.get("rating"),
            "u": t.get("numratings"),
            "w": t.get("complexity"),
            "rk": t["rank"],
            "c": (t.get("categories") or [])[:3],
            "m": (t.get("mechanics") or [])[:3],
            "p": (t.get("publishers") or [None])[0],
            "d": (t.get("designers") or [None])[0],
            "dims": entry.get("dims"),
        })
    games.sort(key=lambda g: g["rk"])
    return {
        "source": {
            "name": "BoardGameGeek",
            "url": "https://boardgamegeek.com",
            "note": "Game data from BoardGameGeek via its XML API. Snapshot only; ratings and ranks change daily.",
            "snapshot": snapshot,
        },
        "count": len(games),
        "games": games,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ranking", required=True, help="dated ranking CSV (ID,Name,Year,Rank,...)")
    ap.add_argument("--top", type=int, default=500, help="how many top-ranked games to include")
    ap.add_argument("--snapshot", help="snapshot date label (default: ranking file name or today)")
    ap.add_argument("--assemble-only", action="store_true", help="write catalog.json from the cache without fetching")
    args = ap.parse_args()

    # Label the snapshot with the date in the ranking file's name (e.g. 2026-10-28.csv).
    found = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(args.ranking))
    snapshot = args.snapshot or (found.group(0) if found else datetime.date.today().isoformat())

    ids = top_ids(args.ranking, args.top)
    cache = load_cache()
    if not args.assemble_only:
        fetch_things(ids, cache)
        fetch_dims(ids, cache)

    catalog = assemble(ids, cache, snapshot)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    with_dims = sum(1 for g in catalog["games"] if g["dims"])
    print(f"wrote {OUT_PATH}: {catalog['count']} games, {with_dims} with box dimensions, "
          f"{os.path.getsize(OUT_PATH) // 1024} KB", flush=True)


if __name__ == "__main__":
    main()
