"""Tests for scripts/build_demo.py, run offline against a tiny fake catalog.

build_demo.main() reads the module-level CATALOG and DEMO_GAMES and writes OUT, so each
test points those at a temp directory (and restores them after). The real catalog.json
and demo-data.json are never read or written.
"""

import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_demo  # noqa: E402


def make_game(gid, name, rank, dims=(10.0, 8.0, 2.0), **extra):
    g = {"id": gid, "n": name, "y": 2015, "mn": 2, "mx": 4, "best": "3", "t": 45,
         "r": 7.5 + rank / 100, "u": 1000 + rank, "w": 2.1, "rk": rank,
         "c": ["Card Game"], "m": ["Drafting"], "p": "Pub " + name, "d": "Des " + name,
         "dims": list(dims), "img": "https://example.test/%d.jpg" % gid}
    g.update(extra)
    return g


def fake_catalog():
    return {
        "source": {"name": "Fake", "snapshot": "2000-01-01"},
        "count": 4,
        "games": [
            make_game(1, "Alpha", 1),
            make_game(2, "Bravo: Deluxe", 2, dims=(11.0, 9.0, 3.0)),
            make_game(3, "Charlie", 3),
            make_game(4, "Huge Box", 4, dims=(30.0, 30.0, 30.0)),  # won't fit a cube
        ],
    }


class BuildDemoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.saved = (build_demo.CATALOG, build_demo.OUT, build_demo.DEMO_GAMES,
                      build_demo.CHECKED_OUT, build_demo.PLACEMENT_OVERRIDES, build_demo.FILL)
        self.addCleanup(self._restore)
        build_demo.CATALOG = os.path.join(self.tmp, "catalog.json")
        build_demo.OUT = os.path.join(self.tmp, "demo-data.json")
        build_demo.DEMO_GAMES = ["Alpha", "Bravo: Deluxe"]
        build_demo.CHECKED_OUT = "Alpha"
        build_demo.PLACEMENT_OVERRIDES = {}

    def _restore(self):
        (build_demo.CATALOG, build_demo.OUT, build_demo.DEMO_GAMES,
         build_demo.CHECKED_OUT, build_demo.PLACEMENT_OVERRIDES, build_demo.FILL) = self.saved

    def build(self, catalog=None):
        with open(build_demo.CATALOG, "w", encoding="utf-8") as f:
            json.dump(fake_catalog() if catalog is None else catalog, f)
        with contextlib.redirect_stdout(io.StringIO()):
            build_demo.main()
        with open(build_demo.OUT, encoding="utf-8") as f:
            return json.load(f)

    def test_paths_are_temp_not_real_files(self):
        self.assertNotEqual(os.path.abspath(build_demo.OUT), os.path.join(ROOT, "demo-data.json"))
        self.assertNotEqual(os.path.abspath(build_demo.CATALOG), os.path.join(ROOT, "catalog.json"))
        self.build()
        self.assertTrue(os.path.exists(build_demo.OUT))

    def test_every_demo_game_comes_from_catalog(self):
        cat = fake_catalog()
        demo = self.build(cat)
        by_name = {g["n"]: g for g in cat["games"]}
        self.assertTrue(demo["games"])
        for g in demo["games"]:
            self.assertIn(g["name"], by_name, "invented game: " + g["name"])
            c = by_name[g["name"]]
            self.assertEqual(g["bggRank"], c["rk"])
            self.assertEqual(g["rating"], c["r"])
            self.assertEqual(g["numRatings"], c["u"])
            self.assertEqual(g["yearPublished"], c["y"])
            self.assertEqual(g["photo"], c["img"])
            self.assertEqual(g["dims"], dict(zip("abc", c["dims"])))
            self.assertTrue(g["bggUrl"].endswith("/" + str(c["id"])))

    def test_no_duplicates_and_hand_picked_games_included(self):
        demo = self.build()
        names = [g["name"] for g in demo["games"]]
        self.assertEqual(len(names), len(set(names)))
        for n in build_demo.DEMO_GAMES:
            self.assertIn(n, names)

    def test_game_too_big_for_a_cube_is_not_added(self):
        names = [g["name"] for g in self.build()["games"]]
        self.assertNotIn("Huge Box", names)

    def test_demo_version_present_and_stable_for_same_input(self):
        a = self.build()
        b = self.build()
        self.assertTrue(a.get("demoVersion"))
        self.assertEqual(a["demoVersion"], b["demoVersion"])

    def test_demo_version_changes_when_game_set_changes(self):
        build_demo.FILL = 0  # no auto-fill, so the shelf holds exactly DEMO_GAMES
        base = self.build()
        build_demo.DEMO_GAMES = ["Alpha", "Charlie"]
        changed = self.build()
        self.assertNotEqual({g["name"] for g in base["games"]}, {g["name"] for g in changed["games"]})
        self.assertNotEqual(base["demoVersion"], changed["demoVersion"])

    def test_demo_version_changes_when_a_game_stat_changes(self):
        base = self.build()["demoVersion"]
        cat = copy.deepcopy(fake_catalog())
        cat["games"][0]["r"] = 9.9
        self.assertNotEqual(base, self.build(cat)["demoVersion"])

    def test_unknown_demo_game_aborts_instead_of_inventing(self):
        build_demo.DEMO_GAMES = ["Alpha", "Not In Catalog"]
        with open(build_demo.CATALOG, "w", encoding="utf-8") as f:
            json.dump(fake_catalog(), f)
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                build_demo.main()
        self.assertIn("Not In Catalog", str(cm.exception))
        self.assertFalse(os.path.exists(build_demo.OUT))


if __name__ == "__main__":
    unittest.main()
