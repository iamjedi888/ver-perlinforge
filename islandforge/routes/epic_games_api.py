"""
Fortnite and ecosystem API helpers.
"""

import json
import os
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session


epic_api_bp = Blueprint("epic_api", __name__, url_prefix="/api")
_CACHE = {}


# Curated list of well-known Fortnite skins with working fortnite-api.com art.
KNOWN_SKINS = [
    {"id": "CID_028_Athena_Commando_F", "name": "Renegade Raider", "img": "https://fortnite-api.com/images/cosmetics/br/CID_028_Athena_Commando_F/icon.png"},
    {"id": "CID_017_Athena_Commando_M", "name": "Aerial Assault Trooper", "img": "https://fortnite-api.com/images/cosmetics/br/CID_017_Athena_Commando_M/icon.png"},
    {"id": "CID_030_Athena_Commando_M_Halloween", "name": "Skull Trooper", "img": "https://fortnite-api.com/images/cosmetics/br/CID_030_Athena_Commando_M_Halloween/icon.png"},
    {"id": "CID_116_Athena_Commando_M_BlueAce", "name": "Blue Squire", "img": "https://fortnite-api.com/images/cosmetics/br/CID_116_Athena_Commando_M_BlueAce/icon.png"},
    {"id": "CID_315_Athena_Commando_M_TeriyakiFishShtick", "name": "Fishstick", "img": "https://fortnite-api.com/images/cosmetics/br/CID_315_Athena_Commando_M_TeriyakiFishShtick/icon.png"},
    {"id": "CID_162_Athena_Commando_M_Celestial", "name": "Brite Bomber", "img": "https://fortnite-api.com/images/cosmetics/br/CID_162_Athena_Commando_M_Celestial/icon.png"},
    {"id": "CID_175_Athena_Commando_M_Celestial", "name": "Ravage", "img": "https://fortnite-api.com/images/cosmetics/br/CID_175_Athena_Commando_M_Celestial/icon.png"},
    {"id": "CID_342_Athena_Commando_F_IceBrute", "name": "Ice Queen", "img": "https://fortnite-api.com/images/cosmetics/br/CID_342_Athena_Commando_F_IceBrute/icon.png"},
    {"id": "CID_441_Athena_Commando_F_BunnyMaiden", "name": "Bunny Brawler", "img": "https://fortnite-api.com/images/cosmetics/br/CID_441_Athena_Commando_F_BunnyMaiden/icon.png"},
    {"id": "CID_516_Athena_Commando_M_Viper", "name": "Chaos Agent", "img": "https://fortnite-api.com/images/cosmetics/br/CID_516_Athena_Commando_M_Viper/icon.png"},
    {"id": "CID_A_065_Athena_Commando_M_ScholarFestive", "name": "The Mandalorian", "img": "https://fortnite-api.com/images/cosmetics/br/CID_A_065_Athena_Commando_M_ScholarFestive/icon.png"},
    {"id": "CID_605_Athena_Commando_F_RocketLeague", "name": "Renegade Racer", "img": "https://fortnite-api.com/images/cosmetics/br/CID_605_Athena_Commando_F_RocketLeague/icon.png"},
    {"id": "CID_A_321_Athena_Commando_M_SpiderMan_NWH", "name": "Spider-Man", "img": "https://fortnite-api.com/images/cosmetics/br/CID_A_321_Athena_Commando_M_SpiderMan_NWH/icon.png"},
    {"id": "CID_784_Athena_Commando_M_BountyHunterSw", "name": "The Mandalorian (Alt)", "img": "https://fortnite-api.com/images/cosmetics/br/CID_784_Athena_Commando_M_BountyHunterSw/icon.png"},
    {"id": "CID_A_025_Athena_Commando_M_HenchmanVisor", "name": "Shadow Midas", "img": "https://fortnite-api.com/images/cosmetics/br/CID_A_025_Athena_Commando_M_HenchmanVisor/icon.png"},
    {"id": "CID_A_168_Athena_Commando_F_SummerDrift", "name": "Drift", "img": "https://fortnite-api.com/images/cosmetics/br/CID_A_168_Athena_Commando_F_SummerDrift/icon.png"},
    {"id": "CID_VIP_Athena_Commando_M_GalileoSuit", "name": "Omega", "img": "https://fortnite-api.com/images/cosmetics/br/CID_VIP_Athena_Commando_M_GalileoSuit/icon.png"},
    {"id": "CID_434_Athena_Commando_M_StealthHeist", "name": "Luxe", "img": "https://fortnite-api.com/images/cosmetics/br/CID_434_Athena_Commando_M_StealthHeist/icon.png"},
    {"id": "CID_296_Athena_Commando_F_SoccerGirl", "name": "Poised Playmaker", "img": "https://fortnite-api.com/images/cosmetics/br/CID_296_Athena_Commando_F_SoccerGirl/icon.png"},
    {"id": "CID_313_Athena_Commando_F_KpopFashion", "name": "K-Pop Fashion", "img": "https://fortnite-api.com/images/cosmetics/br/CID_313_Athena_Commando_F_KpopFashion/icon.png"},
]


def _mock_stats(display_name: str) -> dict:
    seed = sum(ord(c) for c in display_name)
    rng = random.Random(seed)

    matches = rng.randint(200, 4500)
    wins = rng.randint(10, int(matches * 0.25))
    kills = rng.randint(matches * 2, matches * 8)
    kd = round(kills / max(matches - wins, 1), 2)
    win_pct = round((wins / matches) * 100, 1)
    score = rng.randint(800, 4200)
    top5 = wins + rng.randint(20, 150)
    top10 = top5 + rng.randint(30, 200)
    avg_elim = round(kills / matches, 1)

    def mode_slice(match_range, win_cap):
        mode_matches = rng.randint(*match_range)
        mode_wins = rng.randint(0, max(1, min(win_cap, mode_matches // 4)))
        mode_kills = rng.randint(mode_matches, max(mode_matches + 1, mode_matches * 5))
        mode_kd = round(mode_kills / max(mode_matches - mode_wins, 1), 2)
        return {
            "wins": str(mode_wins),
            "kd": str(mode_kd),
            "matches": str(mode_matches),
            "kills": str(mode_kills),
            "winPct": f"{round((mode_wins / mode_matches) * 100, 1) if mode_matches else 0}%",
        }

    return {
        "wins": str(wins),
        "kd": str(kd),
        "matches": str(matches),
        "kills": str(kills),
        "winPct": f"{win_pct}%",
        "score": str(score),
        "top5": str(top5),
        "top10": str(top10),
        "avgElim": str(avg_elim),
        "modes": {
            "overall": {
                "wins": str(wins),
                "kd": str(kd),
                "matches": str(matches),
                "kills": str(kills),
                "winPct": f"{win_pct}%",
                "score": str(score),
                "top5": str(top5),
                "top10": str(top10),
                "avgElim": str(avg_elim),
            },
            "solo": mode_slice((40, 900), wins),
            "duo": mode_slice((40, 1200), wins),
            "squad": mode_slice((40, 1500), wins),
        },
        "_mock": True,
    }


def _mode_snapshot(bucket: dict | None) -> dict:
    bucket = bucket or {}
    matches = _safe_int(bucket.get("matches"))
    wins = _safe_int(bucket.get("wins"))
    kills = _safe_int(bucket.get("kills"))
    kd = _safe_float(bucket.get("kd"))
    win_rate = _safe_float(bucket.get("winRate"))
    avg_elims = _safe_float(bucket.get("killsPerMatch"))
    if not avg_elims and matches:
        avg_elims = kills / matches

    snapshot = {
        "wins": str(wins),
        "kd": _format_float(kd),
        "matches": str(matches),
        "kills": str(kills),
        "winPct": f"{_format_float(win_rate, 1)}%",
        "score": str(_safe_int(bucket.get("score"))),
        "top5": str(_safe_int(bucket.get("top5") or bucket.get("top6"))),
        "top10": str(_safe_int(bucket.get("top10") or bucket.get("top12"))),
        "avgElim": _format_float(avg_elims, 1),
    }

    if not any(value not in {"0", "0%", "0.0", ""} for value in snapshot.values()):
        return {}
    return snapshot


def _fetch_json(url: str, headers: dict | None = None, timeout: int = 6, cache_key: str = "", ttl: int = 0) -> dict:
    now = time.time()
    if cache_key and ttl:
        cached = _CACHE.get(cache_key)
        if cached and (now - cached["time"]) < ttl:
            return cached["value"]

    req = urllib.request.Request(url, headers=headers or {"User-Agent": "TriptokForge/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        value = json.loads(response.read().decode())

    if cache_key and ttl:
        _CACHE[cache_key] = {"time": now, "value": value}

    return value


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_float(value: float, digits: int = 2) -> str:
    text = f"{value:.{digits}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _live_stats_for_name(display_name: str) -> dict | None:
    api_key = os.environ.get("FORTNITE_API_KEY", "").strip()
    if not api_key:
        return None

    requested_name = (display_name or "").strip()
    if not requested_name:
        return None

    query = {"name": requested_name}
    session_name = str(session.get("display_name", "")).strip()
    session_account_id = (
        session.get("epic_account_id")
        or session.get("account_id")
        or session.get("epic_id")
        or ""
    )
    if session_account_id and session_name and session_name.casefold() == requested_name.casefold():
        query = {"account": session_account_id}

    payload = _fetch_json(
        f"https://fortnite-api.com/v2/stats/br/v2?{urllib.parse.urlencode(query)}",
        headers={
            "Authorization": api_key,
            "User-Agent": "TriptokForge/1.0",
        },
        timeout=8,
        cache_key=f"stats:{query.get('account') or requested_name.casefold()}",
        ttl=120,
    )
    data = payload.get("data") or {}
    all_modes = ((data.get("stats") or {}).get("all") or {})
    overall = (all_modes.get("overall") or {})
    if not overall:
        return None

    overall_snapshot = _mode_snapshot(overall)
    modes = {
        "overall": overall_snapshot,
        "solo": _mode_snapshot(all_modes.get("solo")),
        "duo": _mode_snapshot(all_modes.get("duo")),
        "squad": _mode_snapshot(all_modes.get("squad")),
    }

    return {
        **overall_snapshot,
        "modes": modes,
        "_mock": False,
    }


def _platform_snapshot() -> dict:
    snapshot = {
        "db_online": False,
        "members": 0,
        "announcements": 0,
        "channels": 0,
        "posts": 0,
        "islands": 0,
    }
    try:
        from oracle_db import (
            db_available,
            get_all_members,
            get_announcements,
            get_channels,
            get_posts,
            get_recent_islands,
        )

        snapshot["db_online"] = bool(db_available())
        snapshot["members"] = len(get_all_members() or [])
        snapshot["announcements"] = len(get_announcements() or [])
        snapshot["channels"] = len(get_channels() or [])
        snapshot["posts"] = len(get_posts(limit=250) or [])
        snapshot["islands"] = len(get_recent_islands(limit=250) or [])
    except Exception:
        pass
    return snapshot


def _shop_signal() -> dict:
    try:
        payload = _fetch_json(
            "https://fortnite-api.com/v2/shop",
            cache_key="fortnite-shop",
            ttl=300,
        )
        data = payload.get("data") or {}
        entries = data.get("entries") or []
        featured = ((data.get("featured") or {}).get("entries") or [])
        special = ((data.get("specialFeatured") or {}).get("entries") or [])
        daily = ((data.get("daily") or {}).get("entries") or [])
        if not entries:
            entries = featured + special + daily
        return {
            "ok": True,
            "source": "fortnite-api",
            "entries": len(entries),
            "featured": len(featured),
            "special": len(special),
            "daily": len(daily),
            "lastUpdate": data.get("lastUpdate") or data.get("date") or "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "source": "unavailable",
            "entries": 0,
            "featured": 0,
            "special": 0,
            "daily": 0,
            "lastUpdate": "",
            "error": str(exc),
        }


def _cosmetics_signal() -> dict:
    try:
        payload = _fetch_json(
            "https://fortnite-api.com/v2/cosmetics/br?language=en",
            cache_key="fortnite-cosmetics-br",
            ttl=900,
        )
        items = payload.get("data") or []
        outfits = [
            item for item in items
            if (item.get("type") or {}).get("value") == "outfit"
        ]
        return {
            "ok": True,
            "source": "fortnite-api",
            "total": len(items),
            "outfits": len(outfits),
        }
    except Exception:
        return {
            "ok": False,
            "source": "curated",
            "total": len(KNOWN_SKINS),
            "outfits": len(KNOWN_SKINS),
        }


def _ecosystem_services(platform: dict, shop: dict) -> list[dict]:
    try:
        from routes.epic_auth_config import epic_auth_ready, get_epic_auth_config

        epic_ready = epic_auth_ready(get_epic_auth_config())
    except Exception:
        epic_ready = False

    stats_ready = bool(os.environ.get("FORTNITE_API_KEY", "").strip())
    island_code = os.environ.get("FORTNITE_DATA_ISLAND_CODE", "").strip()

    return [
        {
            "id": "oracle-core",
            "label": "Oracle Core",
            "status": "live" if platform["db_online"] else "degraded",
            "value": platform["members"],
            "unit": "members",
            "detail": "Members, channels, islands, and announcements.",
        },
        {
            "id": "epic-oauth",
            "label": "Epic OAuth",
            "status": "ready" if epic_ready else "pending",
            "value": "ON" if epic_ready else "WAIT",
            "unit": "auth",
            "detail": "Site identity and account linking for member login.",
        },
        {
            "id": "fortnite-stats",
            "label": "Fortnite Stats",
            "status": "ready" if stats_ready else "key-needed",
            "value": "LIVE" if stats_ready else "KEY",
            "unit": "players",
            "detail": "Battle Royale player stats via fortnite-api.com when keyed.",
        },
        {
            "id": "fortnite-data-api",
            "label": "Fortnite Data API",
            "status": "ready" if island_code else "watch-ready",
            "value": island_code or "ADD",
            "unit": "island",
            "detail": "Official public island performance once a published island code is set.",
        },
        {
            "id": "fortnite-public",
            "label": "Fortnite Public",
            "status": "live" if shop["ok"] else "degraded",
            "value": shop["entries"],
            "unit": "shop items",
            "detail": "Public shop and cosmetics feeds that do not need private player data.",
        },
    ]


def _coerce_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _rolling_daily_series(rows, key: str, days: int = 7) -> dict:
    today = datetime.utcnow().date()
    dates = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    counts = {date: 0 for date in dates}

    for row in rows or []:
        dt = _coerce_datetime((row or {}).get(key))
        if not dt:
            continue
        day = dt.date()
        if day in counts:
            counts[day] += 1

    labels = [f"{date.strftime('%b')} {date.day}" for date in dates]
    values = [counts[date] for date in dates]
    return {"labels": labels, "values": values}


def _channel_mix(channels, limit: int = 6) -> list[dict]:
    counts = {}
    for channel in channels or []:
        label = (channel.get("category") or "Other").strip() or "Other"
        counts[label] = counts.get(label, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    total = sum(count for _, count in ranked) or 1
    return [
        {
            "label": label,
            "value": count,
            "share": round((count / total) * 100, 1),
        }
        for label, count in ranked
    ]


def _volume_mix(platform: dict, uploads_total: int) -> list[dict]:
    items = [
        ("Members", platform.get("members", 0)),
        ("Channels", platform.get("channels", 0)),
        ("Posts", platform.get("posts", 0)),
        ("Islands", platform.get("islands", 0)),
        ("Uploads", uploads_total),
        ("Announcements", platform.get("announcements", 0)),
    ]
    return [{"label": label, "value": int(value or 0)} for label, value in items]


def _forge_spectrum(account_id: str) -> dict:
    try:
        from oracle_db import get_audio_tracks

        uploads = get_audio_tracks(account_id) if account_id else []
        scope = "member"
        if not uploads:
            uploads = (get_audio_tracks() or [])[:24]
            scope = "site"
    except Exception:
        uploads = []
        scope = "site"

    labels = [
        ("sub_bass", "Sub Bass"),
        ("bass", "Bass"),
        ("midrange", "Midrange"),
        ("presence", "Presence"),
        ("brilliance", "Brilliance"),
    ]
    if not uploads:
        return {
            "scope": scope,
            "sample_size": 0,
            "metrics": [{"id": key, "label": label, "value": 0} for key, label in labels],
        }

    sample_size = len(uploads)
    metrics = []
    for key, label in labels:
        total = 0.0
        for item in uploads:
            weights = item.get("weights") or {}
            total += _safe_float(weights.get(key), 0.0)
        average = total / sample_size if sample_size else 0.0
        metrics.append(
            {
                "id": key,
                "label": label,
                "value": round(max(0.0, min(average, 1.0)) * 100),
            }
        )
    return {"scope": scope, "sample_size": sample_size, "metrics": metrics}


def _system_matrix(platform: dict, shop: dict) -> list[dict]:
    try:
        from oracle_db import status as oracle_status

        system = oracle_status()
    except Exception:
        system = {}

    try:
        from routes.epic_auth_config import epic_auth_ready, get_epic_auth_config

        epic_ready = epic_auth_ready(get_epic_auth_config())
    except Exception:
        epic_ready = False

    stats_ready = bool(os.environ.get("FORTNITE_API_KEY", "").strip())
    island_code = os.environ.get("FORTNITE_DATA_ISLAND_CODE", "").strip()

    return [
        {
            "label": "Oracle",
            "value": "LIVE" if system.get("oracle_online") else "WAIT",
            "status": "ready" if system.get("oracle_online") else "degraded",
            "detail": "Core member, feed, channel, and island data.",
        },
        {
            "label": "OCI",
            "value": "READY" if system.get("oci_config") else "SETUP",
            "status": "ready" if system.get("oci_config") else "pending",
            "detail": "Storage path for media and generated outputs.",
        },
        {
            "label": "Epic Auth",
            "value": "READY" if epic_ready else "PEND",
            "status": "ready" if epic_ready else "pending",
            "detail": "Production Epic login handoff and member auth.",
        },
        {
            "label": "BR Stats",
            "value": "LIVE" if stats_ready else "KEY",
            "status": "ready" if stats_ready else "watch-ready",
            "detail": "Player stat lookups through keyed Fortnite data.",
        },
        {
            "label": "Island API",
            "value": island_code or "ADD",
            "status": "ready" if island_code else "watch-ready",
            "detail": "Official public island analytics after publish.",
        },
        {
            "label": "Shop Feed",
            "value": str(shop.get("entries") or 0),
            "status": "ready" if shop.get("ok") else "degraded",
            "detail": "Public Fortnite item shop and cosmetics feed.",
        },
    ]


def _dashboard_telemetry(account_id: str) -> dict:
    try:
        from oracle_db import (
            get_all_members,
            get_announcements,
            get_audio_tracks,
            get_channels,
            get_posts,
            get_recent_islands,
        )

        members = get_all_members() or []
        uploads = get_audio_tracks() or []
        channels = get_channels() or []
        posts = get_posts(limit=250) or []
        islands = get_recent_islands(limit=250) or []
        announcements = get_announcements() or []
    except Exception:
        members = []
        uploads = []
        channels = []
        posts = []
        islands = []
        announcements = []

    platform = {
        "members": len(members),
        "announcements": len(announcements),
        "channels": len(channels),
        "posts": len(posts),
        "islands": len(islands),
    }
    shop = _shop_signal()

    member_series = _rolling_daily_series(
        [{"created_at": item.get("last_seen")} for item in members],
        "created_at",
    )
    upload_series = _rolling_daily_series(uploads, "created_at")
    island_series = _rolling_daily_series(islands, "created_at")
    post_series = _rolling_daily_series(posts, "created_at")

    return {
        "timeline": {
            "labels": upload_series["labels"],
            "series": [
                {"id": "members", "label": "Member activity", "values": member_series["values"], "color": "#31d0ff"},
                {"id": "uploads", "label": "Audio uploads", "values": upload_series["values"], "color": "#ff7431"},
                {"id": "islands", "label": "Island saves", "values": island_series["values"], "color": "#8aff80"},
                {"id": "posts", "label": "Feed posts", "values": post_series["values"], "color": "#ffd166"},
            ],
        },
        "volume_mix": _volume_mix(platform, len(uploads)),
        "channel_mix": _channel_mix(channels),
        "forge_spectrum": _forge_spectrum(account_id),
        "system_matrix": _system_matrix(platform, shop),
        "notes": [
            "Timeline is built from recent site activity already stored in Oracle.",
            "Forge spectrum averages the current member uploads first, then falls back to site audio.",
            "Readiness cards follow live backend config instead of static copy.",
        ],
    }


@epic_api_bp.route("/stats")
def stats():
    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name required"}), 400

    try:
        live_stats = _live_stats_for_name(name)
        if live_stats:
            return jsonify({"ok": True, "stats": live_stats, "source": "fortnite-api"})
    except Exception:
        pass

    return jsonify({"ok": True, "stats": _mock_stats(name), "source": "mock"})


@epic_api_bp.route("/cosmetics")
def cosmetics():
    try:
        raw = _fetch_json(
            "https://fortnite-api.com/v2/cosmetics/br?language=en",
            cache_key="fortnite-cosmetics-br",
            ttl=900,
        )
        items = raw.get("data", [])
        skins = [
            {
                "id": item["id"],
                "name": item.get("name", "Unknown"),
                "img": (item.get("images") or {}).get("icon", ""),
            }
            for item in items
            if (item.get("type") or {}).get("value") == "outfit"
            and (item.get("images") or {}).get("icon")
        ]
        if skins:
            return jsonify({"ok": True, "skins": skins[:200], "source": "live"})
    except Exception:
        pass

    return jsonify({"ok": True, "skins": KNOWN_SKINS, "source": "curated"})


@epic_api_bp.route("/ecosystem/summary")
def ecosystem_summary():
    platform = _platform_snapshot()
    shop = _shop_signal()
    cosmetics = _cosmetics_signal()

    return jsonify(
        {
            "ok": True,
            "identity": {
                "display_name": session.get("display_name") or (session.get("user") or {}).get("display_name") or "",
                "epic_connected": bool(
                    session.get("epic_access_token")
                    or session.get("access_token")
                    or session.get("epic_id")
                    or session.get("user")
                ),
            },
            "site": {
                "members": platform["members"],
                "announcements": platform["announcements"],
                "channels": platform["channels"],
                "posts": platform["posts"],
                "islands": platform["islands"],
            },
            "signals": {
                "shop": shop,
                "cosmetics": cosmetics,
            },
            "services": _ecosystem_services(platform, shop),
            "notes": [
                "Public Fortnite content feeds are available now.",
                "Live player stats need FORTNITE_API_KEY.",
                "Official island analytics become more useful once your published island code is set.",
            ],
        }
    )


@epic_api_bp.route("/dashboard/telemetry")
def dashboard_telemetry():
    account_id = (
        session.get("epic_account_id")
        or session.get("account_id")
        or session.get("epic_id")
        or ""
    )
    return jsonify({"ok": True, **_dashboard_telemetry(account_id)})


@epic_api_bp.route("/set_skin", methods=["POST"])
def set_skin():
    data = request.get_json(silent=True) or {}
    skin_id = str(data.get("id", "")).strip()[:64]
    skin_name = str(data.get("name", "")).strip()[:128]
    skin_img = str(data.get("img", "")).strip()[:512]

    if not skin_id:
        return jsonify({"ok": False, "error": "id required"}), 400

    session["skin_img"] = skin_img
    session["skin_name"] = skin_name

    epic_id = session.get("epic_id")
    if epic_id:
        try:
            from oracle_db import upsert_member

            upsert_member(
                epic_id=epic_id,
                display_name=session.get("display_name", epic_id),
                skin_img=skin_img,
                skin_name=skin_name,
            )
        except Exception:
            pass

    return jsonify({"ok": True})


@epic_api_bp.route("/suggest_channel", methods=["POST"])
def suggest_channel():
    data = request.get_json(silent=True) or request.form
    name = str(data.get("name", "")).strip()[:128]
    category = str(data.get("category", "Other")).strip()[:64]
    url = str(data.get("embed_url", "")).strip()[:512]
    desc = str(data.get("description", "")).strip()[:256]

    if not name or not url:
        return jsonify({"ok": False, "error": "name and embed_url required"}), 400

    try:
        from oracle_db import get_db

        with get_db() as db:
            db.execute(
                "INSERT INTO channel_suggestions (name, category, embed_url, description) VALUES (?,?,?,?)",
                (name, category, url, desc),
            )
            db.commit()
    except Exception:
        import sys

        print(f"[suggest] {name} | {category} | {url} | {desc}", file=sys.stderr)

    return jsonify({"ok": True})
