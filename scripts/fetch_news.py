#!/usr/bin/env python3
"""
fetch_news.py

Pulls the latest articles from the RSS feeds listed in feeds.json, extracts
each article's lead image (if any), runs that image through the filter in
image_filter.py, and writes the result to data/news.json for the static
site to display.

Run manually:
    python scripts/fetch_news.py

Run automatically:
    see .github/workflows/update-news.yml (runs this on a schedule and
    commits data/news.json so the static site always shows fresh news).
"""
import json
import os
import re
import sys
import html
import datetime
from email.utils import parsedate_to_datetime

import feedparser
import requests

sys.path.insert(0, os.path.dirname(__file__))
from image_filter import should_keep_image  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDS_PATH = os.path.join(ROOT, "feeds.json")
OUTPUT_PATH = os.path.join(ROOT, "data", "news.json")

REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (compatible; SimpleNewsBot/1.0; +https://example.com)"


def load_config():
    with open(FEEDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_image_url(entry):
    """Look in the usual RSS/Atom spots for a lead image URL."""
    # media:content / media:thumbnail (most common for news feeds)
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key)
        if media:
            url = media[0].get("url")
            if url:
                return url

    # enclosure links with an image type
    for link in entry.get("links", []):
        if link.get("type", "").startswith("image/") and link.get("href"):
            return link["href"]

    # fall back to sniffing an <img> tag out of the summary/content HTML
    html_blob = entry.get("summary", "") or ""
    if "content" in entry and entry["content"]:
        html_blob += " " + entry["content"][0].get("value", "")
    match = re.search(r'<img[^>]+src="([^"]+)"', html_blob)
    if match:
        return match.group(1)

    return None


def parse_published(entry):
    for key in ("published", "updated"):
        val = entry.get(key)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(datetime.timezone.utc)
            except Exception:
                pass
    return datetime.datetime.now(datetime.timezone.utc)


def matches_keywords(text, keywords):
    """Case-insensitive substring match against any keyword in the list."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def fetch_feed(feed_config, max_articles):
    name = feed_config["name"]
    url = feed_config["url"]
    include_keywords = feed_config.get("include_keywords")  # only keep articles matching one of these
    exclude_keywords = feed_config.get("exclude_keywords")  # drop articles matching any of these

    print(f"Fetching {name} ({url})...")
    try:
        parsed = feedparser.parse(url, agent=USER_AGENT)
    except Exception as exc:
        print(f"  ERROR parsing {name}: {exc}")
        return []

    if getattr(parsed, "bozo", False) and not parsed.entries:
        print(f"  WARNING: {name} returned no usable entries ({parsed.get('bozo_exception')})")

    articles = []
    skipped_by_filter = 0
    for entry in parsed.entries[:max_articles]:
        title = strip_html(entry.get("title", "")).strip()
        link = entry.get("link", "")
        if not title or not link:
            continue

        summary = strip_html(entry.get("summary", ""))[:280]

        searchable = f"{title} {summary}"
        if include_keywords and not matches_keywords(searchable, include_keywords):
            skipped_by_filter += 1
            continue
        if exclude_keywords and matches_keywords(searchable, exclude_keywords):
            skipped_by_filter += 1
            continue

        image_url = extract_image_url(entry)
        published = parse_published(entry)

        keep_image = should_keep_image(image_url) if image_url else False

        articles.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": name,
            "published": published.isoformat(),
            "image": image_url if keep_image else None,
        })

    if skipped_by_filter:
        print(f"  ({skipped_by_filter} articles skipped by keyword filter)")
    return articles


def main():
    config = load_config()
    max_per_feed = config.get("max_articles_per_feed", 15)
    max_total = config.get("max_total_articles", 60)

    all_articles = []
    for feed in config["feeds"]:
        all_articles.extend(fetch_feed(feed, max_per_feed))

    # newest first
    all_articles.sort(key=lambda a: a["published"], reverse=True)
    all_articles = all_articles[:max_total]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    output = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "article_count": len(all_articles),
        "articles": all_articles,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(all_articles)} articles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
