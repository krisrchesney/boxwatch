"""Guards for the public repo: the published files stay valid, the demo only
uses catalog games, BGG credit stays on the page, and personal files never get
committed. These encode the rules in CLAUDE.md so an agent can't quietly break them.
"""

import json
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def bgg_id(url):
    m = re.search(r"/(?:boardgame|boardgameexpansion)/(\d+)", url or "")
    return m.group(1) if m else None


class PublishedDataTests(unittest.TestCase):
    def test_catalog_shape(self):
        cat = load("catalog.json")
        self.assertEqual(cat["count"], len(cat["games"]))
        self.assertTrue(all("id" in g and "n" in g for g in cat["games"]))

    def test_demo_games_all_come_from_catalog(self):
        # The demo must be real top-500 games, never the user's own collection.
        catalog_ids = {str(g["id"]) for g in load("catalog.json")["games"]}
        for g in load("demo-data.json")["games"]:
            self.assertIn(bgg_id(g.get("bggUrl")), catalog_ids, g.get("name"))

    def test_demo_has_version_stamp(self):
        self.assertTrue(load("demo-data.json").get("demoVersion"))


class PageTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            self.html = f.read()

    def test_bgg_credit_and_logo_present(self):
        self.assertIn("powered-by-bgg.png", self.html)
        self.assertIn("BoardGameGeek", self.html)

    def test_script_tags_balanced(self):
        self.assertEqual(self.html.count("<script"), self.html.count("</script>"))


class SecretsTests(unittest.TestCase):
    def test_personal_files_not_tracked(self):
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
        for name in ("bgg_token.txt", "boxwatch-data.json"):
            self.assertNotIn(name, tracked)


if __name__ == "__main__":
    unittest.main()
