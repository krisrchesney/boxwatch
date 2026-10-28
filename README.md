# Boxwatch

Plan where your board games go on the shelf.

Boxwatch keeps a collection of board games, pulls their stats from
[BoardGameGeek](https://boardgamegeek.com), and works out how to fit them onto
IKEA Kallax / Eket / Billy shelving, sorted by the priorities you choose
(player count, then complexity, then category, or any order you like). Check a
game out and it remembers which cube it came from.

**[Live demo](https://krisrchesney.github.io/boxwatch/)**: a sample shelf of well-known games from BoardGameGeek's top 500 that you can rearrange, check games out of, and add to. Your edits stay in your own browser. The demo only includes the top 500 games: its search looks them up in a built-in snapshot. The full version runs on your own computer and searches all of BoardGameGeek live (below).

**Light, Medium and Heavy** in the app describe how complex a game's rules are (BGG's 1-5 "weight" rating), not how much the box weighs.

## What it does

- **Search BGG by name** and add a game with its rating, complexity, player counts, best player count, category, publisher and rank.
- **Pick the right edition** (local version). Browse a game's editions (newest first, filterable by language) and take its real box dimensions. If you add without choosing, it auto-picks the most likely retail edition: English, with dimensions on file, and a name matching the game's current title.
- **Shelf layout to scale.** Presets for Kallax, Eket and Billy plus custom cubes. Each box is drawn at its real proportions inside its cube.
- **Choose how boxes sit.** Settings (and a quick switch on the Shelves tab) sets the default for the whole shelf: best fit, standing up (spine out), or lying flat (stacked up to the cube's height). A box that can't sit the default way falls back to best fit. Any single game can override the default from a dropdown on its Collection card or from its Edit form, and the game's own choice always wins.
- **Games behind games.** Each cube has a front row and a back row. A box goes behind others when their depths add up to the cube's depth or less. A standing box must also stand at least 0.75 inches taller than the boxes in front of it, so its spine still shows. Boxes lying flat can stack in the back row and may be completely hidden, and so can any game you set to "Back row only"; the cube's label says how many are hidden. Back boxes are drawn lighter, a little higher and numbered; click any cube for a top-down plan drawn to scale. A switch (Shelves tab and Settings) turns it off, and any single game can be kept to the front or back row from its Collection card or Edit form ("Front row only" keeps a game where you can see it).
- **Collection cards** show the cover, rating, player count, and the fields your shelves are sorted by (player count, complexity, category, in your priority order), each labeled.
- **Auto-arrange** the whole collection by your priority order, or let new games find a spot beside their group without disturbing the rest.
- **Check out / check in.** A checked-out game keeps its cube reserved on the shelf view.
- **Expansions.** Mark an expansion as stored inside its base game's box and it takes no shelf space of its own.
- **Export / import** your collection as JSON.

## Run it locally (full version, with live BGG search)

You need Python 3.8+ and nothing else; the server uses only the standard library.

```
git clone https://github.com/krisrchesney/boxwatch.git
cd boxwatch
python server.py
```

Then open <http://localhost:8787>. Your collection is saved to `boxwatch-data.json` next to `server.py`.

### BGG token (needed for live search)

BoardGameGeek requires every XML API request to carry an application token.

1. Register an application at <https://boardgamegeek.com/applications>. Approval takes a few days.
2. Save the token it issues, and nothing else, into a file named `bgg_token.txt` next to `server.py`. (Or set the `BGG_API_TOKEN` environment variable.)
3. Restart the server.

Both `bgg_token.txt` and `boxwatch-data.json` are in `.gitignore`. Never commit them.

### Options

| Environment variable | Default | What it does |
|---|---|---|
| `BOXWATCH_PORT` | `8787` | Port to listen on |
| `BOXWATCH_ALLOWED_HOSTS` | *(none)* | Extra `Host` names to accept, comma separated. Needed only if you reach the server from another device, which also means changing the bind address in `server.py` from `127.0.0.1`. |
| `BGG_API_TOKEN` | *(none)* | BGG token, if you would rather not use `bgg_token.txt` |

## How it's put together

- `server.py` is a small local server. It serves the page, stores the collection as JSON, and proxies BGG (so the token never reaches the browser).
- `index.html` is the whole app: plain HTML, CSS and JavaScript, no build step. If it can't find the server (as on the hosted demo) it loads `demo-data.json`, searches `catalog.json`, and saves to the browser's `localStorage` instead.
- `catalog.json` is a static snapshot of BGG's top-ranked games (name, year, players, time, rating, weight, rank, top tags, publisher, designer, and a best-guess box size). `scripts/build_catalog.py` regenerates it. It needs your own BGG token, and takes about 25 minutes for 500 games because it makes one request per game, politely spaced.
- `demo-data.json` is the demo's starting shelf: a Kallax 4×4 holding about 50 real games picked from `catalog.json` by `scripts/build_demo.py` (a hand-picked mix first, then the next-highest-ranked games that fit). Edit the script and re-run it to change what the demo opens with.
- The server only answers requests addressed to localhost and only accepts writes with a JSON content type, so a web page you happen to have open can't read or overwrite your collection through it.
- `.github/workflows/pages.yml` publishes only `index.html`, `demo-data.json`, `catalog.json` and the BGG logo to GitHub Pages. The server, your data and your token are never uploaded.

## BoardGameGeek data and credit

Game data comes from BoardGameGeek's XML API, used under BGG's
[terms](https://boardgamegeek.com/wiki/page/XML_API_Terms_of_Use): non-commercial only, no modifying the data, and BGG must be credited. Do not use this data to train AI or language models; BGG's terms forbid it.

The page credits BoardGameGeek by name. BGG also asks public-facing pages to show its
"Powered by BGG" logo. Download it from BGG's wiki ("Powered by BGG Logos") and save it as `powered-by-bgg.png` next to `index.html`; the page and the Pages workflow pick it up automatically.

The catalog is a snapshot and goes stale: ratings and ranks change daily. Cover art is hotlinked: each image loads from BGG's own server when it is shown, using the link BGG's API provides, and no artwork is stored in this repository. The art belongs to its publishers and artists. BGG's terms don't say anything specific about displaying cover art that I could find, so check them (and BGG's image policy) yourself before relying on this.

## Limits

- BGG only has box dimensions for some editions. When none are on file you can enter them by hand or follow the "search web" link on the card.
- Dimensions from a different language edition are used as an estimate when no English edition has any; the app does not show that edition's foreign title or cover.
- A game's category is the first tag BGG lists for it (they are alphabetical), which is sometimes a period or theme rather than a genre. Edit it by hand if grouping by category matters to you.
- **Two rows deep at most.** A cube has a front row and a back row, not three, and a back box only goes where it clears the boxes in front (see above). Boxes lying flat stack on top of each other, in the back row as in the front, up to the cube's height, and a box may overhang the one beneath it by up to 1.5 inches.
- **Hidden boxes aren't flagged on the shelf itself.** A box tucked completely out of sight is counted in the cube's label and listed in its plan, but the shelf drawing can't show it, because there is nothing to see from the front.
- Arrangement fills a cube's front row first and uses its back row only for the next games in order that qualify, so back-row use depends on the order your sorting puts games in.
- Shelf placement is a greedy fit (games are taken in priority order and put in the first cube with room), not an optimal bin-packing.
