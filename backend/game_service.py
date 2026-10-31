"""Round builder for "Scam or Legit?".

- daily    : the same 7 cards for everyone on a given India date (seeded by the date)
- practice : a fresh random set of 7 cards each time

Every round mixes cards (4 scams + 3 legit) so spamming "Scam" does not work.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from game_cards import CARDS, validate_cards

IST = timezone(timedelta(hours=5, minutes=30))
SCAMS_PER_ROUND = 4
LEGIT_PER_ROUND = 3
SECONDS_PER_CARD = 25

validate_cards()


def today_ist() -> str:
    return datetime.now(IST).date().isoformat()


def build_round(mode: str = "daily", today: Optional[str] = None) -> Dict[str, Any]:
    if mode not in ("daily", "practice"):
        raise ValueError("mode must be 'daily' or 'practice'")
    date = today or today_ist()
    rng = random.Random(f"scam-or-legit-{date}") if mode == "daily" else random.Random()

    scams = [c for c in CARDS if c["verdict"] == "scam"]
    legit = [c for c in CARDS if c["verdict"] == "legit"]
    picked = rng.sample(scams, SCAMS_PER_ROUND) + rng.sample(legit, LEGIT_PER_ROUND)
    rng.shuffle(picked)

    return {
        "mode": mode,
        "date": date,
        "secondsPerCard": SECONDS_PER_CARD,
        "cards": picked,
        "disclaimer": (
            "Made-up examples for learning. Real scams change often, so when in doubt, "
            "stop and check with your bank or the regulator."
        ),
    }
