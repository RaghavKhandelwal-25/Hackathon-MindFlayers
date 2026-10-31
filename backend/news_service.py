"""Live RBI and SEBI news feeds for FinGuide.

Fetches the official RSS feeds, parses them, and caches results in memory so we
do not hit the (often slow) government sites on every page view.

Design notes
- Each source is cached on its own, so one feed failing never hides the other.
- If a refresh fails, the last good copy is served and marked ``stale``.
- Sources are plain ``FeedSource`` entries; add another RSS feed (or a new
  provider such as NewsData.io) by adding one entry or one function.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("finguide.news")

CACHE_SECONDS = int(float(os.getenv("NEWS_CACHE_MINUTES", "30")) * 60)
MIN_REFRESH_SECONDS = 60  # a manual refresh cannot hit the source more often than this
REQUEST_TIMEOUT = 12.0
MAX_ITEMS_PER_SOURCE = 40
SUMMARY_CHARS = 220

HEADERS = {
    # Some government sites reject the default python user agent.
    "User-Agent": "Mozilla/5.0 (compatible; FinGuideNews/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}


@dataclass(frozen=True)
class FeedSource:
    key: str
    name: str
    url: str
    default_type: str


SOURCES: Dict[str, FeedSource] = {
    "rbi": FeedSource("rbi", "RBI", "https://rbi.org.in/pressreleases_rss.xml", "Press Release"),
    "sebi": FeedSource("sebi", "SEBI", "https://www.sebi.gov.in/sebirss.xml", "Update"),
}

# key -> {"items": [...], "fetched": epoch seconds, "error": str | None}
_cache: Dict[str, Dict[str, Any]] = {}


# ------------------------------------------------------------------ parsing
def _local(tag: str) -> str:
    """Strip any XML namespace: '{ns}title' -> 'title'."""
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(node: ET.Element, *names: str) -> str:
    for child in node:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return ""


def _atom_link(node: ET.Element) -> str:
    for child in node:
        if _local(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
            if (child.text or "").strip():
                return child.text.strip()
    return ""


def _clean_text(raw: str, limit: int = SUMMARY_CHARS) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(raw or ""))
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _parse_date(raw: str) -> Optional[datetime]:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        dt = None
    if dt is None:
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"):
            try:
                dt = datetime.strptime(raw.replace("Z", "+0000"), fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    # Feeds from India usually carry an offset; if one is missing assume IST (+05:30).
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    return dt.astimezone(timezone.utc)


def _sebi_type(link: str, title: str) -> str:
    """Label a SEBI item (the feed mixes press releases, circulars and orders)."""
    path = urlparse(link).path.lower()
    low = title.lower()
    if "circular" in path or "circular" in low:
        return "Circular"
    if "/orders/" in path or "/enforcement/" in path:
        return "Order"
    if "press-release" in path:
        return "Press Release"
    return "Update"


def parse_feed(xml_bytes: bytes, source: FeedSource) -> List[Dict[str, Any]]:
    """Parse RSS 2.0 or Atom bytes into a list of normalised article dicts."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        # Some feeds contain stray control characters; strip them and retry once.
        cleaned = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", xml_bytes)
        root = ET.fromstring(cleaned)

    items: List[Dict[str, Any]] = []
    seen = set()
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        title = _clean_text(_child_text(node, "title"), 300)
        link = _child_text(node, "link") or _atom_link(node)
        if not title or not link.lower().startswith(("http://", "https://")):
            continue  # only accept clickable http(s) links
        if link in seen:
            continue
        seen.add(link)
        published = _parse_date(_child_text(node, "pubdate", "published", "updated", "date"))
        summary = _clean_text(_child_text(node, "description", "summary", "content"))
        if summary.lower() == title.lower():
            summary = ""
        kind = _sebi_type(link, title) if source.key == "sebi" else source.default_type
        items.append(
            {
                "id": f"{source.key}-{hashlib.md5(link.encode()).hexdigest()[:10]}",
                "title": title,
                "link": link,
                "summary": summary,
                "published": published.isoformat() if published else None,
                "source": source.name,
                "sourceKey": source.key,
                "type": kind,
            }
        )
    items.sort(key=lambda a: a["published"] or "", reverse=True)
    return items[:MAX_ITEMS_PER_SOURCE]


# ------------------------------------------------------------------ fetching
async def fetch_bytes(url: str) -> bytes:
    """HTTP GET with a timeout. Kept separate so tests can replace it."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def _load_source(source: FeedSource, force: bool) -> Dict[str, Any]:
    """Return cache entry for a source, refreshing it when needed."""
    now = time.time()
    entry = _cache.get(source.key)
    if entry:
        age = now - entry["fetched"]
        fresh = age < CACHE_SECONDS
        too_soon = age < MIN_REFRESH_SECONDS
        if (fresh and not force) or (force and too_soon):
            return {**entry, "stale": False}
    try:
        data = await fetch_bytes(source.url)
        items = parse_feed(data, source)
        entry = {"items": items, "fetched": time.time(), "error": None}
        _cache[source.key] = entry
        return {**entry, "stale": False}
    except Exception as exc:  # network error, bad status, bad XML...
        logger.warning("News fetch failed for %s: %s", source.key, exc)
        message = "Source is not responding right now."
        if entry:  # serve the last good copy
            return {**entry, "stale": True, "error": message}
        return {"items": [], "fetched": None, "error": message, "stale": False}


async def get_news(source: str = "all", limit: int = 30, refresh: bool = False) -> Dict[str, Any]:
    keys = list(SOURCES) if source == "all" else [source]
    results = await asyncio.gather(*(_load_source(SOURCES[k], refresh) for k in keys))

    items: List[Dict[str, Any]] = []
    status: Dict[str, Any] = {}
    for key, res in zip(keys, results):
        items.extend(res["items"])
        status[key] = {
            "name": SOURCES[key].name,
            "ok": res["error"] is None,
            "stale": res["stale"],
            "error": res["error"],
            "fetchedAt": (
                datetime.fromtimestamp(res["fetched"], tz=timezone.utc).isoformat() if res["fetched"] else None
            ),
        }
    items.sort(key=lambda a: a["published"] or "", reverse=True)
    return {
        "items": items[:limit],
        "sources": status,
        "cacheMinutes": CACHE_SECONDS // 60,
        "disclaimer": "News is shown for general awareness only and is not investment advice.",
    }


def clear_cache() -> None:
    _cache.clear()
