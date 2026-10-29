"""Tests for the BGG XML parsers in server.py.

These run offline against small hand-written XML snippets shaped like BGG's
/thing and /version responses, so no token or network is needed.
"""

import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # noqa: E402

THING = """
<item type="boardgame" id="173346">
  <thumbnail>https://example.test/thumb.jpg</thumbnail>
  <image>https://example.test/full.jpg</image>
  <name type="alternate" value="Duel des 7 Merveilles" />
  <name type="primary" value="7 Wonders Duel" />
  <yearpublished value="2015" />
  <minplayers value="2" />
  <maxplayers value="2" />
  <playingtime value="30" />
  <link type="boardgamecategory" id="1050" value="Ancient" />
  <link type="boardgamecategory" id="1002" value="Card Game" />
  <link type="boardgamemechanic" id="2041" value="Open Drafting" />
  <link type="boardgamepublisher" id="1" value="Repos Production" />
  <link type="boardgamepublisher" id="2" value="Asmodee" />
  <link type="boardgamepublisher" id="3" value="Third Publisher" />
  <link type="boardgamedesigner" id="9" value="Antoine Bauza" />
  <poll name="suggested_numplayers">
    <results numplayers="1"><result value="Best" numvotes="0" /></results>
    <results numplayers="2"><result value="Best" numvotes="900" /></results>
    <results numplayers="3+"><result value="Best" numvotes="4" /></results>
  </poll>
  <statistics>
    <ratings>
      <usersrated value="111107" />
      <average value="8.0912" />
      <averageweight value="2.2267" />
      <ranks><rank type="subtype" name="boardgame" value="21" /></ranks>
    </ratings>
  </statistics>
</item>
"""

EXPANSION = """
<item type="boardgameexpansion" id="200">
  <name type="primary" value="Pantheon" />
  <link type="boardgameexpansion" id="173346" value="7 Wonders Duel" inbound="true" />
  <statistics><ratings>
    <ranks><rank type="subtype" name="boardgame" value="Not Ranked" /></ranks>
  </ratings></statistics>
</item>
"""


class ParseThingItemTests(unittest.TestCase):
    def setUp(self):
        self.game = server.parse_thing_item(ET.fromstring(THING))

    def test_uses_primary_name_not_first_name(self):
        self.assertEqual(self.game["name"], "7 Wonders Duel")

    def test_rounds_rating_and_complexity(self):
        self.assertEqual(self.game["rating"], 8.1)
        self.assertEqual(self.game["complexity"], 2.23)

    def test_keeps_only_two_publishers(self):
        self.assertEqual(self.game["publishers"], ["Repos Production", "Asmodee"])

    def test_reads_rank_and_best_players(self):
        self.assertEqual(self.game["rank"], 21)
        self.assertEqual(self.game["bestPlayers"], "2")

    def test_base_game_url(self):
        self.assertEqual(self.game["bggUrl"], "https://boardgamegeek.com/boardgame/173346")

    def test_expansion_links_to_base_and_handles_not_ranked(self):
        exp = server.parse_thing_item(ET.fromstring(EXPANSION))
        self.assertEqual(exp["itemType"], "boardgameexpansion")
        self.assertEqual(exp["expandsId"], "173346")
        self.assertIsNone(exp["rank"])
        self.assertIn("/boardgameexpansion/200", exp["bggUrl"])


class BestPlayerCountTests(unittest.TestCase):
    def test_no_poll_returns_none(self):
        self.assertIsNone(server.parse_best_player_count(ET.fromstring("<item />")))

    def test_all_zero_votes_returns_none(self):
        item = ET.fromstring(
            '<item><poll name="suggested_numplayers">'
            '<results numplayers="2"><result value="Best" numvotes="0" /></results>'
            "</poll></item>"
        )
        self.assertIsNone(server.parse_best_player_count(item))


class PickBestVersionTests(unittest.TestCase):
    def v(self, id_, name, langs=("English",), dims=True):
        d = {"width": 10, "length": 10, "depth": 3} if dims else {}
        return {"id": str(id_), "name": name, "languages": list(langs), **d}

    def test_none_when_no_dimensions(self):
        self.assertIsNone(server.pick_best_version([self.v(1, "A", dims=False)]))

    def test_prefers_english_with_dimensions(self):
        picked = server.pick_best_version([self.v(1, "A", langs=["German"]), self.v(5, "A")])
        self.assertEqual(picked["id"], "5")

    def test_prefers_current_title_over_lower_id(self):
        # Brass -> Brass: Lancashire: the old low-id printing must not win.
        picked = server.pick_best_version(
            [self.v(10, "Brass"), self.v(50, "Brass: Lancashire")], base_name="Brass: Lancashire"
        )
        self.assertEqual(picked["id"], "50")


if __name__ == "__main__":
    unittest.main()
