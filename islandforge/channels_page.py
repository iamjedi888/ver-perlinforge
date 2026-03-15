"""
Channel page view-model helpers.

The live channels UI now renders from Jinja instead of building HTML in Python.
This module keeps the URL normalization, feed classification, queue resolution,
and grouping logic.
"""

from collections import OrderedDict
import json
import random
import re
import time
import urllib.request
import xml.etree.ElementTree as ET


CHANNEL_ICONS = {
    "Fortnite Competitive": "\u2b21",
    "Game Developers": "\u25c8",
    "Esports": "\u25c9",
    "Creative / UEFN": "\u25b3",
    "Chill Gaming": "\u266b",
    "Chill / Music": "\u266b",
    "Gaming News": "\u25c7",
    "Community Picks": "\u2605",
}

CATEGORY_SCOPES = {
    "Fortnite Competitive": "Fortnite",
    "Game Developers": "Builders",
    "Esports": "Arena",
    "Creative / UEFN": "Builders",
    "Chill Gaming": "Chill",
    "Chill / Music": "Chill",
    "Gaming News": "Signal",
    "Community Picks": "Community",
}

SCOPE_ORDER = [
    "Fortnite",
    "Builders",
    "Arena",
    "Signal",
    "Community",
    "Chill",
]

MODE_ORDER = {
    "replay": 0,
    "live": 1,
    "feed": 2,
}

CHANNEL_META = {
    "Fortnite Competitive": {"official": True, "priority": 10},
    "Epic Games Fortnite": {"official": True, "priority": 11},
    "Fortnite World Cup Archive": {"official": True, "priority": 12},
    "FNCS Highlights 24/7": {"official": True, "priority": 13},
    "Epic Games": {"official": True, "priority": 20},
    "Unreal Engine": {"official": True, "priority": 21},
    "Unity": {"official": True, "priority": 22},
    "GDC - Game Developers Conference": {"official": True, "priority": 23},
    "GDC \u2014 Game Developers Conference": {"official": True, "priority": 23},
    "Naughty Dog": {"official": True, "priority": 24},
    "Bungie": {"official": True, "priority": 25},
    "Riot Games": {"official": True, "priority": 26},
    "Xbox": {"official": True, "priority": 27},
    "PlayStation": {"official": True, "priority": 28},
    "Nintendo": {"official": True, "priority": 29},
    "ESL Counter-Strike": {"official": True, "priority": 30},
    "PGL Esports": {"official": True, "priority": 31},
    "LCK - League of Legends Champions Korea": {"official": True, "priority": 32},
    "LCK \u2014 League of Legends Champions Korea": {"official": True, "priority": 32},
    "Valorant Champions Tour": {"official": True, "priority": 33},
    "Rocket League Esports": {"official": True, "priority": 34},
    "Overwatch League": {"official": True, "priority": 35},
    "UEFN & Creative 2.0 Tutorials": {"official": True, "priority": 40},
    "Unreal Sensei": {"priority": 41},
    "William Faucher": {"priority": 42},
    "Lofi Gaming Radio 24/7": {"priority": 50},
    "Chillhop Music 24/7": {"priority": 51},
    "Video Game Music 24/7": {"priority": 52},
    "Retro Gaming 24/7": {"priority": 53},
    "IGN": {"priority": 60},
    "GameSpot": {"priority": 61},
    "Kotaku": {"priority": 62},
    "Digital Foundry": {"priority": 63},
    "Gameranx": {"priority": 64},
    "Mythpat Gaming": {"priority": 70},
    "SypherPK": {"priority": 71},
    "Lachlan": {"priority": 72},
    "Ali-A": {"priority": 73},
}

CHANNEL_OVERRIDES = {
    "Video Game Music 24/7": {
        "embed_url": "https://youtube.com/live/svb-FVtbDf8",
        "description": "Official Square Enix 24/7 chill game-music video stream with a real live visual feed.",
    },
    "Retro Gaming 24/7": {
        "embed_url": "https://www.youtube.com/channel/UCjFaPUcJU1vwk193mnW_w1w/videos",
        "description": "Retro systems, emulation, and hardware preservation video feed anchored by Modern Vintage Gamer.",
    },
}

CHANNEL_ROTATION_POOLS = {
    "Video Game Music 24/7": {
        "source_urls": [
            "https://youtube.com/live/svb-FVtbDf8",
            "https://www.youtube.com/channel/UCMx60HYcw1ieiPlZZagfqXQ/videos",
            "https://youtu.be/MXSaSe1WECg",
            "https://youtube.com/live/t9anxetj3Qg",
        ],
        "search_terms": [
            "final fantasy",
            "nier",
            "kingdom hearts",
            "piano",
            "chill",
            "kawaii",
        ],
        "label": "Square Enix mix",
    },
}

_QUEUE_CACHE = {}
_QUEUE_CACHE_TTL = 900


def apply_channel_override(name: str, channel: dict) -> dict:
    if name not in CHANNEL_OVERRIDES:
        return channel

    updated = dict(channel)
    updated.update(CHANNEL_OVERRIDES[name])
    return updated


def split_source_urls(value) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        items = [str(item or "").strip() for item in value]
    else:
        raw = (value or "").strip()
        if not raw:
            return []

        items = []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    items.extend(str(item or "").strip() for item in parsed)
            except json.JSONDecodeError:
                pass

        if not items:
            items.extend(part.strip() for part in re.split(r"[\r\n|]+", raw))

    unique = []
    seen = set()
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def pool_source_urls(name: str, raw_value: str) -> list[str]:
    items = split_source_urls(raw_value)
    pool = CHANNEL_ROTATION_POOLS.get(name, {})
    items.extend(pool.get("source_urls", []))

    unique = []
    seen = set()
    for item in items:
        normalized = (item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def pool_search_terms(name: str) -> list[str]:
    return [str(item or "").strip() for item in CHANNEL_ROTATION_POOLS.get(name, {}).get("search_terms", []) if str(item or "").strip()]


def is_youtube_channel_feed_source(url: str) -> bool:
    value = (url or "").strip().lower()
    if not value:
        return False
    if not any(
        marker in value
        for marker in (
            "youtube.com/@",
            "youtube.com/c/",
            "youtube.com/channel/",
            "youtube.com/user/",
        )
    ):
        return False
    return not any(
        marker in value
        for marker in (
            "youtube.com/watch",
            "youtube.com/playlist",
            "youtube.com/live/",
            "youtube.com/shorts/",
        )
    )


def youtube_video_id(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""

    if "youtu.be/" in value:
        return value.split("youtu.be/")[-1].split("?")[0].split("/")[0]

    if "youtube.com/watch" in value:
        for part in value.split("?")[-1].split("&"):
            if part.startswith("v="):
                return part[2:].split("/")[0]

    if "youtube.com/live/" in value:
        return value.split("youtube.com/live/")[-1].split("?")[0].split("/")[0]

    if "youtube.com/shorts/" in value:
        return value.split("youtube.com/shorts/")[-1].split("?")[0].split("/")[0]

    return ""


def _fetch_text(url: str, timeout: int = 6) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TriptokForge/1.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="ignore")


def _youtube_channel_id(source_url: str) -> str:
    direct_match = re.search(r"youtube\.com/channel/(UC[\w-]+)", source_url or "", re.IGNORECASE)
    if direct_match:
        return direct_match.group(1)

    html = _fetch_text(source_url, timeout=8)
    for pattern in (
        r'"externalId":"(UC[\w-]+)"',
        r'"channelId":"(UC[\w-]+)"',
        r'https://www\.youtube\.com/channel/(UC[\w-]+)',
    ):
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return ""


def _youtube_feed_items(source_url: str, limit: int = 18) -> list[dict]:
    cache_key = f"yt-feed:{source_url}"
    cached = _QUEUE_CACHE.get(cache_key)
    now = time.time()
    if cached and (now - cached["time"]) < _QUEUE_CACHE_TTL:
        return list(cached["items"])

    try:
        channel_id = _youtube_channel_id(source_url)
        if not channel_id:
            return []

        feed_text = _fetch_text(
            f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
            timeout=8,
        )
        root = ET.fromstring(feed_text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        items = []
        for entry in root.findall("atom:entry", ns)[:limit]:
            video_id = entry.findtext("yt:videoId", default="", namespaces=ns).strip()
            title = entry.findtext("atom:title", default="", namespaces=ns).strip()
            text_blob = title
            if not video_id:
                continue
            items.append(
                {
                    "title": title or "YouTube upload",
                    "source_url": f"https://www.youtube.com/watch?v={video_id}",
                    "search_text": text_blob.casefold(),
                }
            )
        _QUEUE_CACHE[cache_key] = {"time": now, "items": items}
        return list(items)
    except Exception:
        return []


def _matches_search_term(item: dict, term: str) -> bool:
    query = " ".join(str(term or "").casefold().split())
    if not query:
        return False

    text = (item.get("search_text") or item.get("title") or "").casefold()
    if not text:
        return False

    tokens = [token for token in query.split() if len(token) > 1]
    if not tokens:
        return False
    return all(token in text for token in tokens)


def _youtube_embed_from_ids(video_ids: list[str]) -> str:
    clean_ids = []
    seen = set()
    for item in video_ids:
        video_id = (item or "").strip()
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        clean_ids.append(video_id)

    if not clean_ids:
        return ""

    if len(clean_ids) == 1:
        return (
            f"https://www.youtube.com/embed/{clean_ids[0]}"
            "?autoplay=1&rel=0&playsinline=1&modestbranding=1&enablejsapi=1"
        )

    first = clean_ids[0]
    playlist_tail = ",".join(clean_ids[1:] + [first])
    return (
        f"https://www.youtube.com/embed/{first}"
        f"?playlist={playlist_tail}&autoplay=1&loop=1&rel=0&playsinline=1"
        "&modestbranding=1&enablejsapi=1"
    )


def resolve_channel_rotation(source_urls: list[str], search_terms: list[str] | None = None, limit: int = 18) -> dict:
    normalized = [normalize_source_url(url) for url in (source_urls or []) if url]
    if not normalized:
        return {}

    search_terms = [str(item or "").strip() for item in (search_terms or []) if str(item or "").strip()]
    queue_ids = []
    seen_ids = set()

    def add_video_id(video_id: str):
        clean = (video_id or "").strip()
        if not clean or clean in seen_ids:
            return
        seen_ids.add(clean)
        queue_ids.append(clean)

    for source_url in normalized:
        add_video_id(youtube_video_id(source_url))

    matched_term_count = 0
    feed_match_count = 0
    for source_url in normalized:
        if not is_youtube_channel_feed_source(source_url):
            continue
        items = _youtube_feed_items(source_url, limit=max(limit * 2, 24))
        if not items:
            continue

        for item in items[:limit]:
            before = len(queue_ids)
            add_video_id(youtube_video_id(item.get("source_url", "")))
            if len(queue_ids) > before:
                feed_match_count += 1

        for term in search_terms:
            for item in items:
                if not _matches_search_term(item, term):
                    continue
                before = len(queue_ids)
                add_video_id(youtube_video_id(item.get("source_url", "")))
                if len(queue_ids) > before:
                    matched_term_count += 1

    if len(queue_ids) >= 2:
        random.shuffle(queue_ids)
        summary_bits = [f"Random autoplay queue built from {len(queue_ids)} Square Enix-ready videos"]
        if matched_term_count:
            summary_bits.append(f"{matched_term_count} term-matched picks added")
        elif feed_match_count:
            summary_bits.append(f"{feed_match_count} official uploads mixed in")
        return {
            "embed_url": _youtube_embed_from_ids(queue_ids),
            "source_url": normalized[0],
            "mode": "replay",
            "mode_label": "Random Queue",
            "player_kind": "iframe",
            "count": len(queue_ids),
            "summary": ". ".join(summary_bits) + ".",
        }

    playable = []
    for source_url in normalized:
        embed_url = detect_embed(source_url)
        if is_embeddable(embed_url):
            playable.append((source_url, embed_url))
    if playable:
        source_url, embed_url = random.choice(playable)
        return {
            "embed_url": embed_url,
            "source_url": source_url,
            "mode": detect_feed_mode(source_url, embed_url),
            "mode_label": "Random Source" if len(playable) > 1 else label_for_mode(detect_feed_mode(source_url, embed_url)),
            "player_kind": "iframe",
            "count": len(playable),
            "summary": f"Random source selected from {len(playable)} playable links.",
        }

    fallback = normalized[0]
    embed_url = detect_embed(fallback)
    return {
        "embed_url": embed_url,
        "source_url": fallback,
        "mode": detect_feed_mode(fallback, embed_url),
        "mode_label": label_for_mode(detect_feed_mode(fallback, embed_url)),
        "player_kind": detect_player_kind(fallback, embed_url),
        "count": len(normalized),
        "summary": "",
    }


def detect_embed(url: str) -> str:
    """Convert a channel URL to an embeddable iframe src when supported."""
    if not url:
        return ""
    value = url.strip()

    if any(
        marker in value
        for marker in (
            "player.twitch.tv/",
            "youtube.com/embed/",
            "player.kick.com/",
            "streamable.com/e/",
        )
    ):
        return value

    if "twitch.tv/" in value and "/videos/" not in value:
        channel = value.split("twitch.tv/")[-1].split("?")[0].split("/")[0]
        return f"https://player.twitch.tv/?channel={channel}&parent=triptokforge.org&autoplay=false&muted=false"

    if "twitch.tv/videos/" in value:
        video_id = value.split("/videos/")[-1].split("?")[0]
        return f"https://player.twitch.tv/?video={video_id}&parent=triptokforge.org&autoplay=false"

    if "youtube.com/watch" in value:
        video_id = ""
        for part in value.split("?")[-1].split("&"):
            if part.startswith("v="):
                video_id = part[2:]
                break
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}?autoplay=0"

    if "youtube.com/live/" in value:
        video_id = value.split("youtube.com/live/")[-1].split("?")[0].split("/")[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}?autoplay=0"

    if "youtu.be/" in value:
        video_id = value.split("youtu.be/")[-1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}?autoplay=0"

    if "youtube.com/playlist" in value and "list=" in value:
        playlist_id = value.split("list=")[-1].split("&")[0]
        return f"https://www.youtube.com/embed/videoseries?list={playlist_id}"

    if any(
        marker in value
        for marker in (
            "youtube.com/@",
            "youtube.com/c/",
            "youtube.com/channel/",
            "youtube.com/user/",
        )
    ):
        return value

    if "kick.com/" in value:
        channel = value.split("kick.com/")[-1].split("?")[0].split("/")[0]
        return f"https://player.kick.com/{channel}?autoplay=false"

    if "streamable.com/" in value:
        video_id = value.split("streamable.com/")[-1].split("?")[0]
        return f"https://streamable.com/e/{video_id}"

    return value


def is_embeddable(url: str) -> bool:
    if not url:
        return False
    return any(
        marker in url
        for marker in (
            "player.twitch.tv/",
            "youtube.com/embed/",
            "player.kick.com/",
            "streamable.com/e/",
        )
    )


def normalize_source_url(url: str) -> str:
    if not url:
        return ""

    value = url.strip()
    if any(
        marker in value
        for marker in (
            "youtube.com/@",
            "youtube.com/c/",
            "youtube.com/channel/",
            "youtube.com/user/",
        )
    ) and not any(
        suffix in value for suffix in ("/videos", "/streams", "/live", "/featured")
    ):
        return value.rstrip("/") + "/videos"

    return value


def detect_feed_mode(source_url: str, embed_url: str) -> str:
    source = (source_url or "").strip().lower()
    embed = (embed_url or "").strip().lower()

    if "player.twitch.tv/?channel=" in embed or "player.kick.com/" in embed:
        return "live"

    if any(
        marker in source
        for marker in (
            "youtube.com/watch",
            "youtube.com/live/",
            "youtube.com/playlist",
            "youtu.be/",
            "twitch.tv/videos/",
            "streamable.com/",
        )
    ):
        return "replay"

    if any(
        marker in embed
        for marker in (
            "player.twitch.tv/?video=",
            "youtube.com/embed/",
            "streamable.com/e/",
        )
    ):
        return "replay"

    return "feed"


def label_for_mode(mode: str) -> str:
    return {
        "live": "Live",
        "replay": "Replay",
        "feed": "Feed",
    }.get(mode, "Feed")


def detect_player_kind(source_url: str, embed_url: str) -> str:
    if is_embeddable(embed_url):
        return "iframe"
    return "feed"


def ordered_scopes(seen_scopes: set[str]) -> list[str]:
    scopes = [scope for scope in SCOPE_ORDER if scope in seen_scopes]
    extras = sorted(scope for scope in seen_scopes if scope not in SCOPE_ORDER)
    return scopes + extras


def build_channels_context(channels: list) -> dict:
    groups = OrderedDict()
    seen_scopes = set()
    default_channel = None

    for channel in channels:
        name = channel.get("name", "Unnamed")
        channel = apply_channel_override(name, channel)
        category = channel.get("category", "Other") or "Other"
        structured_sources = channel.get("source_urls") or channel.get("source_urls_text") or channel.get("embed_url", "")
        source_urls = [normalize_source_url(url) for url in pool_source_urls(name, structured_sources)]
        search_terms = channel.get("search_terms") or channel.get("search_terms_text") or pool_search_terms(name)
        if isinstance(search_terms, str):
            search_terms = [line.strip() for line in search_terms.splitlines() if line.strip()]
        else:
            search_terms = [str(item or "").strip() for item in search_terms if str(item or "").strip()]
        source_url = source_urls[0] if source_urls else ""
        embed_url = detect_embed(source_url)
        mode = detect_feed_mode(source_url, embed_url)
        player_kind = detect_player_kind(source_url, embed_url)
        meta = CHANNEL_META.get(name, {})
        scope = meta.get("scope") or CATEGORY_SCOPES.get(category, "General")
        stored_rotation_mode = channel.get("rotation_mode", "") or ""
        has_rotation = (
            stored_rotation_mode in {"queue", "random_pool"}
            or len(source_urls) > 1
            or bool(search_terms)
            or any(is_youtube_channel_feed_source(url) for url in source_urls)
        )
        seen_scopes.add(scope)

        group = groups.setdefault(
            category,
            {
                "name": category,
                "icon": CHANNEL_ICONS.get(category, "\u25b6"),
                "channels": [],
            },
        )
        group["channels"].append(
            {
                "name": name,
                "description": channel.get("description", ""),
                "embed": embed_url,
                "source_url": source_url,
                "source_urls": source_urls,
                "source_count": len(source_urls),
                "search_terms": search_terms,
                "playable": is_embeddable(embed_url),
                "player_kind": player_kind,
                "mode": mode,
                "mode_label": label_for_mode(mode),
                "scope": scope,
                "scope_slug": scope.lower().replace(" ", "-"),
                "has_rotation": has_rotation,
                "provider_hint": channel.get("provider_hint", "") or "",
                "rotation_mode": stored_rotation_mode or ("queue" if has_rotation else "single"),
                "autoplay": int(channel.get("autoplay") or 0),
                "transition_title": channel.get("transition_title", "") or "",
                "transition_copy": channel.get("transition_copy", "") or "",
                "transition_seconds": float(channel.get("transition_seconds") or 0.9),
                "official": bool(meta.get("official", False)),
                "priority": int(meta.get("priority", 999)),
            }
        )

    for group in groups.values():
        group["channels"].sort(
            key=lambda item: (
                0 if item["official"] else 1,
                item["priority"],
                MODE_ORDER.get(item["mode"], 99),
                item["name"].lower(),
            )
        )
        if not default_channel:
            default_channel = next(
                (
                    channel
                    for channel in group["channels"]
                    if channel["player_kind"] == "iframe" or channel["has_rotation"]
                ),
                None,
            )

    scope_labels = ordered_scopes(seen_scopes)
    return {
        "channel_groups": list(groups.values()),
        "channel_total": len(channels),
        "category_total": len(groups),
        "channel_scopes": scope_labels,
        "scope_total": len(scope_labels),
        "default_channel": default_channel,
    }
