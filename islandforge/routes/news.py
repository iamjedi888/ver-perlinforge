"""
Curated TriptokForge news backend.

The feed mix prioritizes gaming, tech, nature, maker culture, and positive
world coverage instead of conflict-heavy headline loops.
"""

from datetime import datetime
from html import unescape
import re

import feedparser
from flask import Blueprint, jsonify, request, session


news_bp = Blueprint("news", __name__)


CATEGORY_META = {
    "all": {"label": "All Signal"},
    "gaming": {"label": "Gaming"},
    "tech": {"label": "Tech"},
    "science": {"label": "Science"},
    "culture": {"label": "Culture"},
    "food": {"label": "Food"},
    "creative": {"label": "Creative"},
    "nature": {"label": "Nature"},
    "world": {"label": "Positive World"},
}


INTEREST_META = {
    "pokemon": {"name": "Pokemon", "category": "gaming", "default": True},
    "mtg": {"name": "Magic", "category": "gaming", "default": True},
    "anime": {"name": "Anime", "category": "culture", "default": True},
    "japan": {"name": "Japan Culture", "category": "culture", "default": True},
    "tech": {"name": "Tech Radar", "category": "tech", "default": True},
    "space": {"name": "Space and Science", "category": "science", "default": True},
    "positive_world": {"name": "Positive World", "category": "world", "default": True},
    "nature": {"name": "Nature", "category": "nature", "default": True},
    "art": {"name": "Art and Design", "category": "creative", "default": True},
    "baking": {"name": "Baking", "category": "food", "default": True},
    "ramen": {"name": "Ramen", "category": "food", "default": False},
    "restoration": {"name": "Restoration", "category": "creative", "default": True},
}


NEWS_FEEDS = {
    "pokemon": {
        "name": "Pokemon",
        "url": "https://www.pokemon.com/us/pokemon-news/rss",
        "category": "gaming",
        "interest": "pokemon",
    },
    "mtg": {
        "name": "Magic: The Gathering",
        "url": "https://magic.wizards.com/en/rss/rss.xml",
        "category": "gaming",
        "interest": "mtg",
    },
    "anime": {
        "name": "Anime News Network",
        "url": "https://www.animenewsnetwork.com/news/rss.xml",
        "category": "culture",
        "interest": "anime",
    },
    "japan": {
        "name": "Japan Today Lifestyle",
        "url": "https://japantoday.com/category/features/lifestyle/feed",
        "category": "culture",
        "interest": "japan",
    },
    "techcrunch": {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "tech",
        "interest": "tech",
    },
    "nasa_tech": {
        "name": "NASA Technology",
        "url": "https://www.nasa.gov/technology/feed/",
        "category": "tech",
        "interest": "tech",
    },
    "jpl": {
        "name": "JPL News",
        "url": "https://www.jpl.nasa.gov/feeds/news/",
        "category": "science",
        "interest": "space",
    },
    "good_science": {
        "name": "Good News Science",
        "url": "https://www.goodnewsnetwork.org/category/news/science/feed",
        "category": "science",
        "interest": "space",
    },
    "good_world": {
        "name": "Good News World",
        "url": "https://www.goodnewsnetwork.org/category/news/world/feed",
        "category": "world",
        "interest": "positive_world",
    },
    "nature": {
        "name": "Earth.org",
        "url": "https://earth.org/feed/",
        "category": "nature",
        "interest": "nature",
    },
    "art": {
        "name": "This Is Colossal",
        "url": "https://www.thisiscolossal.com/feed/",
        "category": "creative",
        "interest": "art",
    },
    "baking": {
        "name": "King Arthur Baking",
        "url": "https://www.kingarthurbaking.com/blog/feed",
        "category": "food",
        "interest": "baking",
    },
    "ramen": {
        "name": "Ramen Adventures",
        "url": "https://www.ramenadventures.com/feed/",
        "category": "food",
        "interest": "ramen",
    },
    "restoration": {
        "name": "This Old House",
        "url": "https://www.thisoldhouse.com/feed",
        "category": "creative",
        "interest": "restoration",
    },
}


DEFAULT_INTERESTS = [
    interest_id
    for interest_id, meta in INTEREST_META.items()
    if meta.get("default", False)
]

NEGATIVE_KEYWORDS = [
    "war",
    "conflict",
    "violence",
    "attack",
    "death",
    "killed",
    "murder",
    "assault",
    "abuse",
    "scandal",
    "lawsuit",
    "fired",
    "accused",
    "arrested",
    "crime",
    "shooting",
    "missile",
    "bomb",
    "hostage",
    "terror",
    "invasion",
]

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    cleaned = TAG_RE.sub(" ", unescape(value or ""))
    return SPACE_RE.sub(" ", cleaned).strip()


def should_filter(title: str, summary: str, filter_on: bool) -> bool:
    if not filter_on:
        return False
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in NEGATIVE_KEYWORDS)


def iso_from_entry(entry: feedparser.FeedParserDict) -> str:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        return datetime(*published[:6]).isoformat()
    return datetime.utcnow().isoformat()


def fetch_rss(url: str, max_items: int = 8, filter_negative: bool = True) -> list[dict]:
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []

    items = []
    for entry in getattr(feed, "entries", []):
        if len(items) >= max_items:
            break

        title = clean_text(entry.get("title", "Untitled"))
        summary = clean_text(entry.get("summary", entry.get("description", "")))
        if should_filter(title, summary, filter_negative):
            continue

        if len(summary) > 220:
            summary = summary[:217].rstrip() + "..."

        items.append(
            {
                "title": title,
                "summary": summary,
                "link": entry.get("link", ""),
                "published": iso_from_entry(entry),
            }
        )
    return items


def get_enabled_interests() -> list[str]:
    stored = session.get("news_interests")
    if not stored:
        return DEFAULT_INTERESTS[:]
    return [interest for interest in stored if interest in INTEREST_META]


def build_feed_items(category: str | None = None, limit_per_feed: int = 4) -> list[dict]:
    enabled_interests = set(get_enabled_interests())
    filter_negative = session.get("filter_negative", True)
    items = []

    for feed_id, feed_config in NEWS_FEEDS.items():
        if feed_config["interest"] not in enabled_interests:
            continue
        if category and feed_config["category"] != category:
            continue

        for item in fetch_rss(feed_config["url"], max_items=limit_per_feed, filter_negative=filter_negative):
            items.append(
                {
                    **item,
                    "feed_id": feed_id,
                    "source": feed_config["name"],
                    "category": feed_config["category"],
                    "interest": feed_config["interest"],
                }
            )

    items.sort(key=lambda item: item["published"], reverse=True)
    return items


@news_bp.route("/api/news/preferences", methods=["GET", "POST"])
def preferences():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        requested_interests = data.get("interests", [])
        session["news_interests"] = [
            interest for interest in requested_interests if interest in INTEREST_META
        ] or DEFAULT_INTERESTS[:]
        session["filter_negative"] = bool(data.get("filter_negative", True))

    return jsonify(
        {
            "interests": get_enabled_interests(),
            "filter_negative": session.get("filter_negative", True),
            "default_interests": DEFAULT_INTERESTS,
        }
    )


@news_bp.route("/api/news/interests", methods=["GET"])
def interests():
    payload = {}
    for interest_id, meta in INTEREST_META.items():
        payload[interest_id] = {
            "name": meta["name"],
            "category": meta["category"],
            "category_label": CATEGORY_META[meta["category"]]["label"],
            "default": meta.get("default", False),
        }
    return jsonify(payload)


@news_bp.route("/api/news/categories", methods=["GET"])
def categories():
    return jsonify(CATEGORY_META)


@news_bp.route("/api/news/latest", methods=["GET"])
def latest():
    items = build_feed_items(limit_per_feed=4)
    return jsonify({"news": items[:60], "total": len(items)})


@news_bp.route("/api/news/category/<category>", methods=["GET"])
def category_news(category: str):
    if category not in CATEGORY_META or category == "all":
        items = build_feed_items(limit_per_feed=4)
    else:
        items = build_feed_items(category=category, limit_per_feed=8)
    return jsonify({"category": category, "news": items, "total": len(items)})
