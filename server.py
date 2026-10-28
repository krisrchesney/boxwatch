"""
Boxwatch local server — a small standalone backend for the board game shelf app.

Runs entirely on the Python standard library (no pip installs needed):
  - Serves index.html and the local JSON data file.
  - Proxies BoardGameGeek's public XML API so the browser can search by name
    and pull real stats/cover art/edition dimensions live (no chat round-trip).

Run it with:
    python server.py
Then open:
    http://localhost:8787
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "boxwatch-data.json")
APP_FILE = os.path.join(HERE, "index.html")
TOKEN_FILE = os.path.join(HERE, "bgg_token.txt")
PORT = int(os.environ.get("BOXWATCH_PORT", "8787"))

# The server only ever answers requests addressed to this machine. Without a Host
# check, a hostile web page could rebind its own domain to 127.0.0.1 and read or
# overwrite your collection through your browser. Add extra names (e.g. a LAN IP
# when you expose the server to your phone) via BOXWATCH_ALLOWED_HOSTS=a,b.
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "[::1]"} | {
    h.strip().lower() for h in os.environ.get("BOXWATCH_ALLOWED_HOSTS", "").split(",") if h.strip()
}
MAX_BODY_BYTES = 50 * 1024 * 1024  # a collection with queued photos is a few MB at most

BGG_BASE = "https://boardgamegeek.com/xmlapi2"


def bgg_headers():
    """BGG now requires a registered application's auth token on every XML API
    request (see https://boardgamegeek.com/using_the_xml_api). Register at
    https://boardgamegeek.com/applications, then save the token as the sole
    contents of bgg_token.txt next to this script — never hardcode it here."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BoxwatchLocal/1.0; personal use)"}
    token = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
    token = token or os.environ.get("BGG_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

DEFAULT_STATE = {
    "version": 1,
    "units": [
        {"id": "unit_seed1", "presetKey": "kallax_2x4", "label": "Kallax 2×4", "rows": 2, "cols": 4, "cubeW": 13, "cubeH": 13, "cubeD": 15.25},
        {"id": "unit_seed2", "presetKey": "kallax_5x5", "label": "Kallax 5×5 (1)", "rows": 5, "cols": 5, "cubeW": 13, "cubeH": 13, "cubeD": 15.25},
        {"id": "unit_seed3", "presetKey": "kallax_5x5", "label": "Kallax 5×5 (2)", "rows": 5, "cols": 5, "cubeW": 13, "cubeH": 13, "cubeD": 15.25},
    ],
    "games": [],
    "pending": [],
    "priorityOrder": ["playerCount", "complexity", "category"],
    "groupTogether": True,
}


def load_state():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_STATE


def save_state(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def bgg_get(path):
    """GET a BGG XML API path, retrying while BGG queues the request (202)."""
    last_err = None
    for _ in range(5):
        req = urllib.request.Request(BGG_BASE + path, headers=bgg_headers())
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 202:
                    time.sleep(1.5)
                    continue
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 202:
                time.sleep(1.5)
                continue
            if e.code == 401:
                raise RuntimeError(
                    "BGG requires a registered app token now. Register at "
                    "https://boardgamegeek.com/applications, then save the token "
                    "(only the token, nothing else) into bgg_token.txt next to server.py "
                    "and restart the server."
                ) from e
            body = e.read().decode("utf-8", "ignore") if e.fp else ""
            raise RuntimeError(f"BGG returned HTTP {e.code}: {body[:200]}") from e
        except urllib.error.URLError as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"BGG API did not respond after retries ({last_err})")


def _text(el):
    return el.text.strip() if el is not None and el.text else None


def _num(el, attr="value"):
    if el is None:
        return None
    try:
        return float(el.get(attr))
    except (TypeError, ValueError):
        return None


def parse_best_player_count(item):
    poll = None
    for p in item.findall("poll"):
        if p.get("name") == "suggested_numplayers":
            poll = p
            break
    if poll is None:
        return None
    best_count, best_votes = None, -1
    for results in poll.findall("results"):
        numplayers = results.get("numplayers")
        votes = 0
        for r in results.findall("result"):
            if r.get("value") == "Best":
                votes = int(r.get("numvotes") or 0)
                break
        if votes > best_votes:
            best_votes, best_count = votes, numplayers
    return best_count if best_votes > 0 else None


def parse_thing_item(item):
    name = None
    for n in item.findall("name"):
        if n.get("type") == "primary":
            name = n.get("value")
            break
    if not name:
        n0 = item.find("name")
        name = n0.get("value") if n0 is not None else "?"

    ratings = item.find("statistics/ratings")
    rating = _num(ratings.find("average")) if ratings is not None else None
    numratings = _num(ratings.find("usersrated")) if ratings is not None else None
    weight = _num(ratings.find("averageweight")) if ratings is not None else None

    # The item's own `type` attribute (from /thing, not /search) is the
    # authoritative signal for base game vs. expansion — BGG's search type
    # filter is unreliable and can return the same id typed either way.
    item_type = item.get("type") or "boardgame"
    expands_id, expands_name = None, None
    if item_type == "boardgameexpansion":
        for l in item.findall("link"):
            if l.get("type") == "boardgameexpansion" and l.get("inbound") == "true":
                expands_id, expands_name = l.get("id"), l.get("value")
                break

    categories = [l.get("value") for l in item.findall("link") if l.get("type") == "boardgamecategory"]
    mechanics = [l.get("value") for l in item.findall("link") if l.get("type") == "boardgamemechanic"]
    publishers = [l.get("value") for l in item.findall("link") if l.get("type") == "boardgamepublisher"]
    designers = [l.get("value") for l in item.findall("link") if l.get("type") == "boardgamedesigner"]

    rank_el = None
    for r in item.findall("statistics/ratings/ranks/rank"):
        if r.get("name") == "boardgame":
            rank_el = r
            break
    rank = None
    if rank_el is not None:
        try:
            rank = int(rank_el.get("value"))
        except (TypeError, ValueError):
            rank = None  # BGG sends the literal string "Not Ranked" here for unranked items

    return {
        "id": item.get("id"),
        "itemType": item_type,
        "expandsId": expands_id,
        "expandsName": expands_name,
        "name": name,
        "categories": categories,
        "mechanics": mechanics,
        "publishers": publishers[:2],
        "designers": designers[:2],
        "rank": rank,
        "yearpublished": item.find("yearpublished").get("value") if item.find("yearpublished") is not None else None,
        "minplayers": item.find("minplayers").get("value") if item.find("minplayers") is not None else None,
        "maxplayers": item.find("maxplayers").get("value") if item.find("maxplayers") is not None else None,
        "playingtime": item.find("playingtime").get("value") if item.find("playingtime") is not None else None,
        "thumbnail": _text(item.find("thumbnail")),
        "image": _text(item.find("image")),
        "rating": round(rating, 1) if rating else None,
        "numratings": int(numratings) if numratings else None,
        "complexity": round(weight, 2) if weight else None,
        "bestPlayers": parse_best_player_count(item),
        "bggUrl": f"https://boardgamegeek.com/{'boardgameexpansion' if item_type == 'boardgameexpansion' else 'boardgame'}/{item.get('id')}",
    }


def parse_version_item(item):
    # `name` on a version is often just a generic label ("English edition") shared
    # across multiple versions of the same game — `canonicalname` carries the actual
    # distinguishing product name (e.g. "... Ultimate Tanares Adventures") that BGG's
    # own site displays, so prefer it and fall back only if it's missing.
    canonical = item.find("canonicalname")
    name = canonical.get("value") if canonical is not None else None
    if not name:
        n0 = item.find("name")
        name = n0.get("value") if n0 is not None else None
    edition_label = item.find("name").get("value") if item.find("name") is not None else None
    languages = [l.get("value") for l in item.findall("link") if l.get("type") == "language"]
    return {
        "id": item.get("id"),
        "name": name,
        "editionLabel": edition_label if edition_label != name else None,
        "yearpublished": item.find("yearpublished").get("value") if item.find("yearpublished") is not None else None,
        "thumbnail": _text(item.find("thumbnail")),
        "image": _text(item.find("image")),
        "width": _num(item.find("width")),
        "length": _num(item.find("length")),
        "depth": _num(item.find("depth")),
        "productcode": item.find("productcode").get("value") if item.find("productcode") is not None else None,
        "languages": languages,
    }


def pick_best_version(versions, base_name=None):
    """Best-effort guess at "the edition most people would have on their shelf":
    prefer versions with real submitted dimensions (skip the many that have none),
    prefer English releases among those, then prefer versions whose name matches
    the game's CURRENT title — a reprinted game (e.g. Brass -> Brass: Lancashire)
    has old out-of-print versions at low ids that would otherwise win on
    "earliest id" alone, which is backwards; matching today's title corrects for
    that. Only after all of that does lowest id break remaining ties. Returns
    None if no version has usable dimensions at all."""
    with_dims = [v for v in versions if v.get("width") and v.get("length") and v.get("depth")]
    if not with_dims:
        return None
    english = [v for v in with_dims if "English" in (v.get("languages") or [])]
    pool = english or with_dims
    if base_name:
        exact = [v for v in pool if (v.get("name") or "").strip().lower() == base_name.strip().lower()]
        if exact:
            pool = exact
    pool = sorted(pool, key=lambda v: int(v["id"]))
    return pool[0]


def bgg_search(query):
    # Search both base games and expansions — /search's type filter mistypes
    # some items, but every id it returns gets re-resolved to its true type
    # via /thing right after, so over-including here is harmless.
    data = bgg_get(f"/search?query={urllib.parse.quote(query)}&type=boardgame,boardgameexpansion")
    root = ET.fromstring(data)
    out = []
    seen = set()
    for item in root.findall("item"):
        id_ = item.get("id")
        if id_ in seen:  # same id can appear twice (once per type) in this combined search
            continue
        seen.add(id_)
        name_el = item.find("name")
        year_el = item.find("yearpublished")
        out.append({
            "id": id_,
            "name": name_el.get("value") if name_el is not None else "?",
            "yearpublished": year_el.get("value") if year_el is not None else None,
        })
    return out


def bgg_things(ids):
    ids = [i for i in ids if i]
    if not ids:
        return {}
    data = bgg_get(f"/thing?id={','.join(ids)}&stats=1")
    root = ET.fromstring(data)
    return {item.get("id"): parse_thing_item(item) for item in root.findall("item")}


def bgg_thing_versions(base_id):
    """BGG only returns version data when versions=1 is set, and nests the full
    version items two levels deep (item > versions > item), not as top-level
    siblings — a plain root.findall("item") misses them entirely. Also returns
    the base item's own current primary name, used to bias version selection
    toward reprints that share today's title over old out-of-print namings."""
    data = bgg_get(f"/thing?id={base_id}&versions=1")
    root = ET.fromstring(data)
    base_item = root.find("item")
    base_name = None
    if base_item is not None:
        for n in base_item.findall("name"):
            if n.get("type") == "primary":
                base_name = n.get("value")
                break
    versions = [parse_version_item(item) for item in root.findall(".//versions/item") if item.get("type") == "boardgameversion"]
    return versions, base_name


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the console quiet

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            self.send_error(404, "Not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _host_allowed(self):
        host = (self.headers.get("Host") or "").strip().lower()
        host = host.split("]")[0] + "]" if host.startswith("[") else host.split(":")[0]
        return host in ALLOWED_HOSTS

    def do_GET(self):
        if not self._host_allowed():
            self.send_error(403, "Host not allowed")
            return
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            self.serve_file(APP_FILE, "text/html; charset=utf-8")
            return

        if parsed.path == "/powered-by-bgg.png":  # BGG's attribution logo, if you've added it
            self.serve_file(os.path.join(HERE, "powered-by-bgg.png"), "image/png")
            return

        if parsed.path == "/api/state":
            self.send_json(load_state())
            return

        if parsed.path == "/api/search":
            q = (qs.get("q", [""])[0]).strip()
            if not q:
                self.send_json({"ok": True, "results": []})
                return
            try:
                candidates = bgg_search(q)[:8]
                things = bgg_things([c["id"] for c in candidates])
                merged = []
                for c in candidates:
                    t = things.get(c["id"])
                    if t:
                        merged.append(t)
                    else:
                        merged.append({**c, "thumbnail": None, "image": None})
                self.send_json({"ok": True, "results": merged})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, status=502)
            return

        if parsed.path == "/api/versions":
            base_id = (qs.get("id", [""])[0]).strip()
            if not base_id:
                self.send_json({"ok": True, "versions": []})
                return
            try:
                versions, base_name = bgg_thing_versions(base_id)
                best = pick_best_version(versions, base_name)
                self.send_json({"ok": True, "versions": versions, "bestGuessId": best["id"] if best else None})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, status=502)
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        if not self._host_allowed():
            self.send_error(403, "Host not allowed")
            return
        if self.path == "/api/state":
            # Requiring a JSON content type forces browsers to preflight any
            # cross-site request, and this server never answers preflights, so a
            # random web page can't overwrite the collection via a "simple" POST.
            if not (self.headers.get("Content-Type") or "").lower().startswith("application/json"):
                self.send_json({"ok": False, "error": "Content-Type must be application/json"}, status=415)
                return
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_BODY_BYTES:
                self.send_json({"ok": False, "error": "Request body too large"}, status=413)
                return
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                save_state(data)
                self.send_json({"ok": True})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, status=400)
            return
        self.send_error(404, "Not found")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Boxwatch running at http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
