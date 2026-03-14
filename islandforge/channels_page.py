"""
Channel page view-model helpers.

The live channels UI now renders from Jinja instead of building HTML in Python.
This module keeps only the URL normalization and grouping logic.
"""

from collections import OrderedDict


CHANNEL_ICONS = {
    "Fortnite Competitive": "\u2b21",
    "Game Developers": "\u25c8",
    "Esports": "\u25c9",
    "Creative / UEFN": "\u25b3",
    "Chill / Music": "\u266b",
    "Gaming News": "\u25c7",
}


def detect_embed(url: str) -> str:
    """Convert a channel URL to an embeddable iframe src when supported."""
    if not url:
        return ""
    value = url.strip()

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

    if "youtu.be/" in value:
        video_id = value.split("youtu.be/")[-1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}?autoplay=0"

    if "youtube.com/@" in value or "youtube.com/c/" in value or "youtube.com/channel/" in value:
        return value

    if "kick.com/" in value:
        channel = value.split("kick.com/")[-1].split("?")[0].split("/")[0]
        return f"https://player.kick.com/{channel}?autoplay=false"

    if "streamable.com/" in value:
        video_id = value.split("streamable.com/")[-1].split("?")[0]
        return f"https://streamable.com/e/{video_id}"

    return value


def build_channels_context(channels: list) -> dict:
    groups = OrderedDict()

    for channel in channels:
        category = channel.get("category", "Other") or "Other"
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
                "name": channel.get("name", "Unnamed"),
                "description": channel.get("description", ""),
                "embed": detect_embed(channel.get("embed_url", "")),
            }
        )

    return {
        "channel_groups": list(groups.values()),
        "channel_total": len(channels),
        "category_total": len(groups),
    }
