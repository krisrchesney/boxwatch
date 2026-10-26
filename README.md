# Boxwatch

Plan where your board games go on the shelf.

Boxwatch keeps a collection of board games, pulls their stats from
[BoardGameGeek](https://boardgamegeek.com), and works out how to fit them onto
IKEA Kallax / Eket / Billy shelving, sorted by the priorities you choose
(player count, then complexity, then category, or any order you like). Check a
game out and it remembers which cube it came from.

**[Live demo](https://krisrchesney.github.io/boxwatch/)** uses invented sample games and keeps your edits in your own browser only. It has no BGG search, because search needs the local server described below.

## What it does

- **Search BGG by name** and add a game with its rating, complexity, player counts, best player count, category, publisher and cover art.
- **Pick the right edition.** Browse a game's editions (newest first, filterable by language) and take its real box dimensions. If you add without choosing, it auto-picks the most likely retail edition: English, with dimensions on file, and a name matching the game's current title.
- **Shelf layout to scale.** Presets for Kallax, Eket and Billy plus custom cubes. Boxes are placed by spine width, and each box can be forced to stand up or lie flat.
- **Auto-arrange** the whole collection by your priority order, or let new games find a spot beside their group without disturbing the rest.
- **Check out / check in.** A checked-out game keeps its cube reserved on the shelf view.
- **Expansions.** Mark an expansion as stored inside its base game's box and it takes no shelf space of its own.
- **Export / import** your collection as JSON.

## Run it locally (full version, with BGG search)

You need Python 3.8+ and nothing else; the server uses only the standard library.

```
git clone https://github.com/krisrchesney/boxwatch.git
cd boxwatch
python server.py
```

Then open <http://localhost:8787>. Your collection is saved to `boxwatch-data.json` next to `server.py`.

### BGG token (needed for Search)

BoardGameGeek requires every XML API request to carry an application token.

1. Register an application at <https://boardgamegeek.com/applications>. Approval takes a few days.
2. Save the token it issues, and nothing else, into a file named `bgg_token.txt` next to `server.py`. (Or set the `BGG_API_TOKEN` environment variable.)
3. Restart the server.

Both `bgg_token.txt` and `boxwatch-data.json` are in `.gitignore`. Never commit them.

BGG's terms apply to your use of their data. Read <https://boardgamegeek.com/using_the_xml_api> before you share anything built on it, and use your own token rather than someone else's.

### Options

| Environment variable | Default | What it does |
|---|---|---|
| `BOXWATCH_PORT` | `8787` | Port to listen on |
| `BOXWATCH_ALLOWED_HOSTS` | *(none)* | Extra `Host` names to accept, comma separated. Needed only if you reach the server from another device, which also means changing the bind address in `server.py` from `127.0.0.1`. |
| `BGG_API_TOKEN` | *(none)* | BGG token, if you would rather not use `bgg_token.txt` |

## How it's put together

- `server.py` is a small local server. It serves the page, stores the collection as JSON, and proxies BGG (so the token never reaches the browser).
- `index.html` is the whole app: plain HTML, CSS and JavaScript, no build step. If it can't find the server (as on the hosted demo) it loads `demo-data.json` and saves to the browser's `localStorage` instead.
- The server only answers requests addressed to localhost and only accepts writes with a JSON content type, so a web page you happen to have open can't read or overwrite your collection through it.
- `.github/workflows/pages.yml` publishes only `index.html` and `demo-data.json` to GitHub Pages. The server, your data and your token are never uploaded.

## Limits

- BGG only has box dimensions for some editions. When none are on file you can enter them by hand or follow the "search web" link on the card.
- Dimensions from a different language edition are used as an estimate when no English edition has any; the app does not show that edition's foreign title or cover.
- Shelf placement is a greedy fit, not an optimal bin-packing, and it treats each cube as one row of upright boxes.
