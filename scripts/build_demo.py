#!/usr/bin/env python3
"""Build demo-data.json, the sample shelf the hosted demo opens with.

Every game here is a real title from catalog.json (BGG's top 500), with the real
stats and best-guess box size stored there; nothing is invented. The mix is chosen
so the first view shows several games per cube: small two-player boxes, party and
family games, and big heavy boxes, in a range of sizes.

    python scripts/build_demo.py

Edit DEMO_GAMES to change what the demo shows, then re-run. Names must match
catalog.json exactly.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog.json")
OUT = os.path.join(ROOT, "demo-data.json")

DEMO_GAMES = [
    # small two-player boxes
    "7 Wonders Duel", "Patchwork", "Jaipur", "Targi", "Splendor Duel",
    # party and light games
    "Codenames", "Just One", "The Crew: Mission Deep Sea",
    # family weight
    "Azul", "Splendor", "Quacks", "Cascadia", "Carcassonne", "Ticket to Ride: Europe",
    "Pandemic", "Dominion", "Everdell", "Wingspan", "Terraforming Mars",
    # heavy, bigger boxes
    "Brass: Birmingham", "Great Western Trail", "Root", "Spirit Island", "Ark Nova", "Scythe",
]
CHECKED_OUT = "Wingspan"  # one game out on loan, so the dashed "checked out" spot shows on the shelf


def main():
    with open(CATALOG, encoding="utf-8") as f:
        catalog = json.load(f)
    by_name = {}
    for g in catalog["games"]:  # sorted by rank, so the best-ranked match wins
        by_name.setdefault(g["n"], g)

    missing = [n for n in DEMO_GAMES if n not in by_name]
    if missing:
        sys.exit("not in catalog.json (top 500 only): " + ", ".join(missing))

    games = []
    for i, name in enumerate(DEMO_GAMES, 1):
        c = by_name[name]
        dims = c.get("dims") or [0, 0, 0]
        games.append({
            "id": f"demo_{i}",
            "status": "checked_out" if name == CHECKED_OUT else "shelved",
            "homeSlot": None, "slotIndex": 0,
            "checkedOutAt": "2026-10-20T19:30:00.000Z" if name == CHECKED_OUT else None,
            "name": c["n"], "editionName": "", "photo": "",
            "rating": c["r"] or 0, "numRatings": c["u"] or 0, "complexity": c["w"] or 0,
            "yearPublished": c["y"] or 0,
            "minPlayers": c["mn"] or 0, "maxPlayers": c["mx"] or 0,
            "bestPlayers": c.get("best") or "", "playTime": str(c["t"] or ""),
            "category": (c.get("c") or ["Uncategorized"])[0],
            "bggCategories": c.get("c") or [], "bggMechanics": c.get("m") or [],
            "publisher": c.get("p") or "", "designer": c.get("d") or "", "bggRank": c["rk"],
            "dims": {"a": dims[0], "b": dims[1], "c": dims[2]},
            "orientation": "auto",
            "bggUrl": "https://boardgamegeek.com/boardgame/" + str(c["id"]),
            "isExpansion": False, "expandsOf": "", "parentGameId": "", "storedInParent": False,
        })

    state = {
        "version": 1,
        "units": [
            {"id": "unit_demo1", "presetKey": "kallax_2x4", "label": "Kallax 2×4", "rows": 2, "cols": 4,
             "cubeW": 13, "cubeH": 13, "cubeD": 15.25},
        ],
        "games": games,
        "pending": [],
        "priorityOrder": ["playerCount", "complexity", "category"],
        "groupTogether": False,  # pack each cube full, so the first view shows several games per cube
        "shelfOrientation": "best",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}: {len(games)} real games from the top 500 (catalog snapshot {catalog['source']['snapshot']})")


if __name__ == "__main__":
    main()
