"""Tests for the RBI/SEBI news feature. All network calls are mocked."""
import os
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, patch

os.environ["FINGUIDE_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_news.db")

from fastapi.testclient import TestClient  # noqa: E402

import news_service  # noqa: E402
from api import app  # noqa: E402

RBI_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>RBI</title>
<item><title>RBI to conduct 2-day VRR auction</title>
<link>https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=1</link>
<description>&lt;p&gt;Auction under LAF &amp;amp; more&lt;/p&gt;</description>
<pubDate>Fri, 30 Oct 2026 10:00:00 +0530</pubDate></item>
<item><title>Older RBI release</title>
<link>https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=2</link>
<pubDate>Tue, 27 Oct 2026 09:00:00 +0530</pubDate></item>
<item><title>Bad link item</title><link>javascript:alert(1)</link></item>
</channel></rss>"""

SEBI_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>SEBI</title>
<item><title>SEBI launches investor awareness drive</title>
<link>https://www.sebi.gov.in/media-and-notifications/press-releases/oct-2026/awareness_1.html</link>
<pubDate>Sat, 31 Oct 2026 08:00:00 +0530</pubDate></item>
<item><title>Master Circular for Mutual Funds</title>
<link>https://www.sebi.gov.in/legal/circulars/oct-2026/mf_2.html</link>
<pubDate>Thu, 29 Oct 2026 08:00:00 +0530</pubDate></item>
<item><title>Order in the matter of XYZ Ltd</title>
<link>https://www.sebi.gov.in/enforcement/orders/oct-2026/xyz_3.html</link>
<pubDate>Wed, 28 Oct 2026 08:00:00 +0530</pubDate></item>
<item><title>Order in the matter of XYZ Ltd</title>
<link>https://www.sebi.gov.in/enforcement/orders/oct-2026/xyz_3.html</link>
<pubDate>Wed, 28 Oct 2026 08:00:00 +0530</pubDate></item>
</channel></rss>"""


async def fake_fetch(url):
    return RBI_XML if "rbi.org.in" in url else SEBI_XML


class TestParsing(unittest.TestCase):
    def test_rbi_parse_cleans_html_and_skips_bad_links(self):
        items = news_service.parse_feed(RBI_XML, news_service.SOURCES["rbi"])
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "RBI to conduct 2-day VRR auction")  # newest first
        self.assertEqual(items[0]["summary"], "Auction under LAF & more")
        self.assertEqual(items[0]["type"], "Press Release")
        self.assertTrue(items[0]["published"].startswith("2026-10-30T04:30"))  # 10:00 IST -> 04:30 UTC

    def test_sebi_types_and_dedup(self):
        items = news_service.parse_feed(SEBI_XML, news_service.SOURCES["sebi"])
        self.assertEqual([i["type"] for i in items], ["Press Release", "Circular", "Order"])

    def test_atom_feed_and_control_chars(self):
        atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Hello\x01 World</title>'
                b'<link href="https://example.com/a"/><updated>2026-10-30T10:00:00+05:30</updated></entry></feed>')
        items = news_service.parse_feed(atom, news_service.SOURCES["rbi"])
        self.assertEqual(items[0]["title"], "Hello World")
        self.assertEqual(items[0]["link"], "https://example.com/a")


class TestNewsEndpoint(unittest.TestCase):
    def setUp(self):
        news_service.clear_cache()
        self.c = TestClient(app)

    def test_merged_feed_sorted_newest_first(self):
        with patch("news_service.fetch_bytes", new=AsyncMock(side_effect=fake_fetch)):
            d = self.c.get("/api/news").json()
        self.assertEqual(d["items"][0]["source"], "SEBI")  # 31 Oct is newest
        self.assertEqual({i["source"] for i in d["items"]}, {"RBI", "SEBI"})
        self.assertTrue(d["sources"]["rbi"]["ok"] and d["sources"]["sebi"]["ok"])
        self.assertIn("disclaimer", d)

    def test_source_filter_limit_and_validation(self):
        with patch("news_service.fetch_bytes", new=AsyncMock(side_effect=fake_fetch)):
            d = self.c.get("/api/news?source=rbi&limit=1").json()
            self.assertEqual(len(d["items"]), 1)
            self.assertEqual(d["items"][0]["source"], "RBI")
            self.assertEqual(self.c.get("/api/news?source=bogus").status_code, 400)

    def test_cache_prevents_repeat_fetches_and_refresh_is_rate_limited(self):
        mock = AsyncMock(side_effect=fake_fetch)
        with patch("news_service.fetch_bytes", new=mock):
            self.c.get("/api/news")
            self.c.get("/api/news")
            self.assertEqual(mock.call_count, 2)  # one per source, second call served from cache
            self.c.get("/api/news?refresh=true")  # too soon: still cached
            self.assertEqual(mock.call_count, 2)
            for entry in news_service._cache.values():
                entry["fetched"] = time.time() - 120  # pretend 2 minutes passed
            self.c.get("/api/news?refresh=true")
            self.assertEqual(mock.call_count, 4)

    def test_one_source_failing_does_not_break_the_other(self):
        async def half_broken(url):
            if "sebi" in url:
                raise RuntimeError("timeout")
            return RBI_XML

        with patch("news_service.fetch_bytes", new=AsyncMock(side_effect=half_broken)):
            d = self.c.get("/api/news").json()
        self.assertTrue(d["sources"]["rbi"]["ok"])
        self.assertFalse(d["sources"]["sebi"]["ok"])
        self.assertTrue(all(i["source"] == "RBI" for i in d["items"]))
        self.assertNotIn("timeout", str(d))  # internal error text is not leaked

    def test_stale_copy_served_when_refresh_fails(self):
        with patch("news_service.fetch_bytes", new=AsyncMock(side_effect=fake_fetch)):
            self.c.get("/api/news")
        for entry in news_service._cache.values():
            entry["fetched"] = time.time() - 3600  # expired
        with patch("news_service.fetch_bytes", new=AsyncMock(side_effect=RuntimeError("down"))):
            d = self.c.get("/api/news").json()
        self.assertTrue(len(d["items"]) > 0)
        self.assertTrue(d["sources"]["rbi"]["stale"])


if __name__ == "__main__":
    unittest.main()
