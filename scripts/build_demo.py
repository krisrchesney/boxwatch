#!/usr/bin/env python3
"""Build demo-data.json, the sample shelf the hosted demo opens with.

Every game here is a real title from catalog.json (BGG's top 500), with the real
stats, cover link and best-guess box size stored there; nothing is invented. The
shelf is a Kallax 4x4 (16 cubes). It starts with a hand-picked mix of small
two-player boxes, party and family games and big heavy boxes (DEMO_GAMES), then
adds the next-highest-ranked games that physically fit a Kallax cube until the
shelf is about 70% full, which leaves room to rearrange.

    python scripts/build_demo.py

Edit DEMO_GAMES (or ROWS/COLS/FILL) and re-run. Names must match catalog.json exactly.
"""

import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog.json")
OUT = os.path.join(ROOT, "demo-data.json")

ROWS, COLS = 4, 4                      # Kallax 4x4
CUBE_W, CUBE_H, CUBE_D = 13, 13, 15.25  # IKEA Kallax cube, inches
FILL = 0.72                             # stop adding games when this much shelf width is used (leave slack to play with)

DEMO_GAMES = [
    # small two-player boxes
    "7 Wonders Duel", "Patchwork", "Jaipur", "Targi", "Splendor Duel",
    # low, shallow two-player boxes up front, taller shallow ones that can sit behind them
    "Hanamikoji", "Schotten Totten", "Lost Cities", "Air, Land, & Sea",
    "Battle Line", "Codenames: Duet", "Sky Team", "Unmatched: Robin Hood vs. Bigfoot",
    # party and light games
    "Codenames", "Just One", "The Crew: Mission Deep Sea",
    # family weight
    "Azul", "Splendor", "Quacks", "Cascadia", "Carcassonne", "Ticket to Ride: Europe",
    "Pandemic", "Dominion", "Everdell", "Wingspan", "Terraforming Mars",
    # heavy, bigger boxes
    "Brass: Birmingham", "Great Western Trail", "Root", "Spirit Island", "Ark Nova", "Scythe",
]
CHECKED_OUT = "Wingspan"  # one game out on loan, so the dashed "checked out" spot shows on the shelf
# Per-game choices, to show the controls: this one lies flat and is kept to the back row, so it is
# tucked away out of sight behind the front boxes (the cube's label says how many are hidden).
PLACEMENT_OVERRIDES = {"Lost Cities": {"orientation": "horizontal", "depthPref": "back"}}


def spine_if_it_fits(dims):
    """Narrowest shelf width this box can use in a Kallax cube, or None if it won't fit at all
    (the same best-fit rule the app uses)."""
    best = None
    for i in range(3):
        spine = dims[i]
        x, y = [d for j, d in enumerate(dims) if j != i]
        fits = (x <= CUBE_H and y <= CUBE_D) or (y <= CUBE_H and x <= CUBE_D)
        if fits and spine <= CUBE_W and (best is None or spine < best):
            best = spine
    return best


def family(name):
    return name.split(":")[0].strip().lower()


def main():
    with open(CATALOG, encoding="utf-8") as f:
        catalog = json.load(f)
    ranked = catalog["games"]  # sorted by rank
    by_name = {}
    for g in ranked:
        by_name.setdefault(g["n"], g)

    missing = [n for n in DEMO_GAMES if n not in by_name]
    if missing:
        sys.exit("not in catalog.json (top 500 only): " + ", ".join(missing))

    chosen = [by_name[n] for n in DEMO_GAMES]
    no_dims = [g["n"] for g in chosen if not g.get("dims")]
    if no_dims:
        sys.exit("hand-picked game has no box dimensions in catalog.json: " + ", ".join(no_dims))
    used = sum(spine_if_it_fits(g["dims"]) or 0 for g in chosen)
    families = {family(g["n"]) for g in chosen}
    target = ROWS * COLS * CUBE_W * FILL
    for g in ranked:  # then the best-ranked games that fit, one per series, until the shelf is ~72% full (FILL)
        if used >= target:
            break
        if g in chosen or not g.get("dims") or family(g["n"]) in families:
            continue
        spine = spine_if_it_fits(g["dims"])
        if spine is None:
            continue
        chosen.append(g)
        families.add(family(g["n"]))
        used += spine

    games = []
    for i, c in enumerate(chosen, 1):
        dims = c.get("dims") or [0, 0, 0]
        out = c["n"] == CHECKED_OUT
        games.append({
            "id": f"demo_{i}",
            "status": "checked_out" if out else "shelved",
            "homeSlot": None, "slotIndex": 0,
            "checkedOutAt": "2026-10-20T19:30:00.000Z" if out else None,
            "name": c["n"], "editionName": "", "photo": c.get("img") or "",
            "rating": c["r"] or 0, "numRatings": c["u"] or 0, "complexity": c["w"] or 0,
            "yearPublished": c["y"] or 0,
            "minPlayers": c["mn"] or 0, "maxPlayers": c["mx"] or 0,
            "bestPlayers": c.get("best") or "", "playTime": str(c["t"] or ""),
            "category": (c.get("c") or ["Uncategorized"])[0],
            "bggCategories": c.get("c") or [], "bggMechanics": c.get("m") or [],
            "publisher": c.get("p") or "", "designer": c.get("d") or "", "bggRank": c["rk"],
            "dims": {"a": dims[0], "b": dims[1], "c": dims[2]},
            "orientation": "auto", "depthPref": "auto",
            "bggUrl": "https://boardgamegeek.com/boardgame/" + str(c["id"]),
            "isExpansion": False, "expandsOf": "", "parentGameId": "", "storedInParent": False,
        })
        games[-1].update(PLACEMENT_OVERRIDES.get(c["n"], {}))

    state = {
        "version": 1,
        "units": [
            {"id": "unit_demo1", "presetKey": "kallax_4x4", "label": f"Kallax {ROWS}×{COLS}", "rows": ROWS, "cols": COLS,
             "cubeW": CUBE_W, "cubeH": CUBE_H, "cubeD": CUBE_D},
        ],
        "games": games,
        "pending": [],
        "priorityOrder": ["playerCount", "complexity", "category"],
        "groupTogether": False,  # pack each cube full, so the first view shows several games per cube
        "shelfOrientation": "best",
    }
    # Version stamp: the page keeps a visitor's saved edits only while this matches, so changing
    # the sample shelf replaces stale saved copies instead of being hidden by them.
    state["demoVersion"] = hashlib.sha1(
        json.dumps(state, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}: {len(games)} real games from the top 500, Kallax {ROWS}x{COLS} ({ROWS * COLS} cubes), "
          f"~{used:.0f}in of {ROWS * COLS * CUBE_W}in of shelf width used (catalog snapshot {catalog['source']['snapshot']})")


if __name__ == "__main__":
    main()
