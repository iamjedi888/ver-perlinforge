"""
routes/leaderboard.py - /leaderboard and leaderboard data APIs
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import os

from flask import Blueprint, jsonify, render_template, session


leaderboard_bp = Blueprint("leaderboard", __name__)


try:
    from oracle_db import (
        db_available,
        get_all_members,
        get_channels,
        get_member_room,
        get_posts,
        get_recent_islands,
    )

    HAS_DB = True
except ImportError:
    HAS_DB = False

    def db_available():
        return False

    def get_all_members():
        return []

    def get_channels(approved_only=True):
        return []

    def get_member_room(epic_id):
        return {"theme": "", "tickets": 0}

    def get_posts(limit=50, approved_only=True):
        return []

    def get_recent_islands(limit=20):
        return []


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _member_board_payload():
    if not HAS_DB or not db_available():
        return {
            "members": [],
            "summary": {
                "members": 0,
                "islands": 0,
                "posts": 0,
                "channels": 0,
                "local_signal_ready": False,
                "competitive_ready": False,
            },
            "notes": [
                "Oracle member data is not available yet.",
                "When the database is live, this board ranks TriptokForge creators by local platform activity.",
            ],
        }

    raw_members = get_all_members() or []
    islands = get_recent_islands(limit=250) or []
    posts = get_posts(limit=250) or []
    channels = get_channels(approved_only=False) or []

    island_counts = Counter()
    plot_totals = defaultdict(int)
    for island in islands:
        creator_id = str(island.get("creator_id") or island.get("epic_id") or "").strip()
        if not creator_id:
            continue
        island_counts[creator_id] += 1
        plot_totals[creator_id] += _safe_int(island.get("plots_count"))

    post_counts = Counter()
    like_totals = defaultdict(int)
    for post in posts:
        author_id = str(post.get("epic_id") or "").strip()
        if not author_id:
            continue
        post_counts[author_id] += 1
        like_totals[author_id] += _safe_int(post.get("likes"))

    channel_counts = Counter()
    for channel in channels:
        suggested_by = str(channel.get("suggested_by") or "").strip()
        if suggested_by:
            channel_counts[suggested_by] += 1

    members = []
    competitive_ready = False
    local_signal_ready = False

    for member in raw_members:
        epic_id = str(member.get("epic_id") or "").strip()
        room = get_member_room(epic_id) if epic_id else {"theme": "", "tickets": 0}

        wins = _safe_int(member.get("wins"))
        kd = round(_safe_float(member.get("kd")), 2)
        tickets = _safe_int(member.get("tickets")) or _safe_int(room.get("tickets"))
        islands_created = island_counts[epic_id]
        plots_total = plot_totals[epic_id]
        posts_created = post_counts[epic_id]
        likes_received = like_totals[epic_id]
        channels_submitted = channel_counts[epic_id]

        forge_score = int(
            (tickets * 6)
            + (islands_created * 30)
            + (plots_total * 2)
            + (posts_created * 10)
            + (likes_received * 2)
            + (channels_submitted * 14)
            + (wins * 3)
            + round(kd * 8)
        )

        if wins or kd:
            competitive_ready = True
        if tickets or islands_created or posts_created or likes_received or channels_submitted:
            local_signal_ready = True

        members.append(
            {
                "epic_id": epic_id,
                "display_name": member.get("display_name") or "Unknown",
                "skin_img": member.get("skin_img") or member.get("avatar_url") or "",
                "skin_name": member.get("skin_name") or "",
                "last_seen": member.get("last_seen") or "",
                "tickets": tickets,
                "wins": wins,
                "kd": kd,
                "islands_created": islands_created,
                "plots_total": plots_total,
                "posts_created": posts_created,
                "likes_received": likes_received,
                "channels_submitted": channels_submitted,
                "forge_score": forge_score,
            }
        )

    summary = {
        "members": len(members),
        "islands": len(islands),
        "posts": len(posts),
        "channels": len([item for item in channels if _safe_int(item.get("approved"), 1) == 1])
        if channels
        else 0,
        "local_signal_ready": local_signal_ready,
        "competitive_ready": competitive_ready,
    }

    notes = [
        "Local ranking is weighted toward TriptokForge activity until a real competitive season exists.",
        "Tickets, saved islands, total plots built, posts, and approved channel submissions are live local signals.",
        "Battle Royale stat lookup is separate and stays available through Player Lookup when Fortnite API access is configured.",
    ]

    return {"members": members, "summary": summary, "notes": notes}


def _ecosystem_payload():
    from routes.epic_games_api import (
        _cosmetics_signal,
        _ecosystem_services,
        _platform_snapshot,
        _shop_signal,
    )

    platform = _platform_snapshot()
    shop = _shop_signal()
    cosmetics = _cosmetics_signal()
    island_code = os.environ.get("FORTNITE_DATA_ISLAND_CODE", "").strip()
    stats_key_ready = bool(os.environ.get("FORTNITE_API_KEY", "").strip())

    scope = [
        {
            "label": "TriptokForge Local",
            "status": "live" if platform.get("db_online") else "degraded",
            "value": f"{platform.get('members', 0)} members",
            "detail": "Oracle-backed member, island, post, and channel activity that we control directly.",
        },
        {
            "label": "Fortnite-API",
            "status": "ready" if stats_key_ready else "key-needed",
            "value": "BR lookup",
            "detail": "Player Battle Royale stat search plus public shop and cosmetics surfaces.",
        },
        {
            "label": "Epic Official",
            "status": "ready" if island_code else "watch-ready",
            "value": island_code or "Publish first",
            "detail": "Public island analytics become useful once a published island code is configured.",
        },
    ]

    signals = [
        {
            "label": "Shop Entries",
            "value": shop.get("entries", 0),
            "detail": "Current public item shop inventory size.",
        },
        {
            "label": "Featured Rows",
            "value": shop.get("featured", 0) + shop.get("special", 0),
            "detail": "Featured and special featured clusters from the public shop feed.",
        },
        {
            "label": "Cosmetics",
            "value": cosmetics.get("total", 0),
            "detail": "Public cosmetic records available from Fortnite-API.",
        },
        {
            "label": "Outfits",
            "value": cosmetics.get("outfits", 0),
            "detail": "Subset of cosmetics that are character outfits.",
        },
        {
            "label": "Site Islands",
            "value": platform.get("islands", 0),
            "detail": "Forge outputs or saved islands currently stored by the site.",
        },
        {
            "label": "Feed Posts",
            "value": platform.get("posts", 0),
            "detail": "Approved feed activity available for local creator rankings.",
        },
        {
            "label": "Channels",
            "value": platform.get("channels", 0),
            "detail": "Curated TV-guide channel inventory available now.",
        },
    ]

    notes = [
        "Epic official public scope is strongest for published island engagement analytics after launch.",
        "Fortnite-API is the current route for keyed Battle Royale account lookup plus public shop and cosmetics feeds.",
        "This page does not pretend there is a trusted global top-player feed wired right now. Use Player Lookup for account-level BR stats and the local board for TriptokForge activity.",
    ]

    return {
        "scope": scope,
        "services": _ecosystem_services(platform, shop),
        "signals": signals,
        "notes": notes,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@leaderboard_bp.route("/leaderboard")
def leaderboard():
    user = session.get("user") or {}
    current_user = {
        "account_id": user.get("account_id") or session.get("epic_id") or "",
        "display_name": user.get("display_name") or session.get("display_name") or "",
    }
    return render_template("leaderboard.html", current_user=current_user)


@leaderboard_bp.route("/api/leaderboard/members")
def api_leaderboard_members():
    payload = _member_board_payload()
    return jsonify({"ok": True, **payload})


@leaderboard_bp.route("/api/leaderboard/global")
def api_leaderboard_global():
    payload = _ecosystem_payload()
    return jsonify({"ok": True, **payload})
