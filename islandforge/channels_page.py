"""
Channel page view-model helpers.

The live channels UI now renders from Jinja instead of building HTML in Python.
This module keeps the URL normalization, feed classification, and grouping logic.
"""

from collections import OrderedDict


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


def apply_channel_override(name: str, channel: dict) -> dict:
    if name not in CHANNEL_OVERRIDES:
        return channel

    updated = dict(channel)
    updated.update(CHANNEL_OVERRIDES[name])
    return updated


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
        source_url = normalize_source_url(channel.get("embed_url", ""))
        embed_url = detect_embed(channel.get("embed_url", ""))
        mode = detect_feed_mode(source_url, embed_url)
        player_kind = detect_player_kind(source_url, embed_url)
        meta = CHANNEL_META.get(name, {})
        scope = meta.get("scope") or CATEGORY_SCOPES.get(category, "General")
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
                "playable": is_embeddable(embed_url),
                "player_kind": player_kind,
                "mode": mode,
                "mode_label": label_for_mode(mode),
                "scope": scope,
                "scope_slug": scope.lower().replace(" ", "-"),
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
                    if channel["player_kind"] == "iframe"
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
