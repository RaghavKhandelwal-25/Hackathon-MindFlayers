"""Tests for the Scam or Legit game (card bank, round builder, endpoint)."""
import os
import tempfile
import unittest

os.environ["FINGUIDE_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_game.db")

from fastapi.testclient import TestClient  # noqa: E402

import game_service  # noqa: E402
from api import app  # noqa: E402
from game_cards import CARDS, validate_cards  # noqa: E402


class TestCards(unittest.TestCase):
    def test_card_bank_is_valid(self):
        validate_cards()  # raises on any problem

    def test_enough_cards_for_a_round(self):
        scams = [c for c in CARDS if c["verdict"] == "scam"]
        legit = [c for c in CARDS if c["verdict"] == "legit"]
        self.assertGreaterEqual(len(scams), game_service.SCAMS_PER_ROUND)
        self.assertGreaterEqual(len(legit), game_service.LEGIT_PER_ROUND)

    def test_validation_catches_bad_cards(self):
        bad = [{**CARDS[0], "verdict": "maybe"}]
        with self.assertRaises(ValueError):
            validate_cards(bad)
        with self.assertRaises(ValueError):
            validate_cards([CARDS[0], CARDS[0]])  # duplicate id


class TestRounds(unittest.TestCase):
    def test_daily_is_same_for_same_date_and_mixed(self):
        a = game_service.build_round("daily", "2026-10-31")
        b = game_service.build_round("daily", "2026-10-31")
        self.assertEqual([c["id"] for c in a["cards"]], [c["id"] for c in b["cards"]])
        self.assertEqual(len(a["cards"]), 7)
        verdicts = [c["verdict"] for c in a["cards"]]
        self.assertEqual(verdicts.count("scam"), 4)
        self.assertEqual(verdicts.count("legit"), 3)

    def test_daily_changes_across_days(self):
        ids = {tuple(c["id"] for c in game_service.build_round("daily", f"2026-11-{d:02d}")["cards"]) for d in range(1, 11)}
        self.assertGreater(len(ids), 1)

    def test_practice_has_no_repeats_inside_a_round(self):
        r = game_service.build_round("practice")
        ids = [c["id"] for c in r["cards"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_bad_mode(self):
        with self.assertRaises(ValueError):
            game_service.build_round("hard")


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app)

    def test_daily_round(self):
        r = self.c.get("/api/game/round")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["mode"], "daily")
        self.assertEqual(len(d["cards"]), 7)
        self.assertEqual(d["secondsPerCard"], 25)
        self.assertIn("disclaimer", d)

    def test_practice_round_and_bad_mode(self):
        self.assertEqual(self.c.get("/api/game/round?mode=practice").status_code, 200)
        self.assertEqual(self.c.get("/api/game/round?mode=hard").status_code, 400)


if __name__ == "__main__":
    unittest.main()
