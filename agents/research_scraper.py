"""Research Scraper Agent (masterplan §25.7).

Pulls 1of10's blog RSS for new findings, stores in DB.
"""
from __future__ import annotations

import datetime as dt

import feedparser

from data.db import db

# 1of10's Ghost blog. Adjust if their RSS path changes.
FEEDS = [
    "https://1of10.com/blog/rss",
    "https://1of10.com/rss",
]


class ResearchScraperAgent:
    def __init__(self) -> None:
        self.db = db()

    def update(self) -> dict:
        new_count = 0
        for url in FEEDS:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                continue
            for entry in feed.entries:
                link = entry.get("link", "")
                if not link:
                    continue
                if list(self.db["research"].rows_where("url = ?", [link])):
                    continue
                self.db["research"].insert({
                    "source": "1of10 blog",
                    "url": link,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:1000],
                    "key_findings": "[]",
                    "published_at": entry.get("published", ""),
                    "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
                }, alter=True)
                new_count += 1
            if feed.entries:
                break  # First feed that worked
        return {"new_articles": new_count}

    def list_recent(self, limit: int = 20) -> list[dict]:
        return list(self.db["research"].rows_where(
            order_by="fetched_at desc", limit=limit,
        ))
