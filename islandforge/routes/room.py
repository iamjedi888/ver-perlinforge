"""Member room routes and theme controls."""

from __future__ import annotations

import json

from flask import Blueprint, jsonify, redirect, render_template, request, session

room_bp = Blueprint("room", __name__)

ROOM_THEME_CATALOG = [
    {
        "slug": "coastal",
        "label": "Coastal Relay",
        "biome": "Coastal / Harbor",
        "ambient": "Sea mist, blue hour, harbor glass",
        "summary": "Dockside command suite with salt-air lighting, panoramic waterline glass, and a clean broadcast deck.",
        "setup": [
            "panoramic harbor backdrop",
            "brushed concrete floor with light reflection",
            "cool cyan tactical lighting",
        ],
        "accent": "#67f0ff",
        "assets": [
            {
                "title": "Massive Nordic Coastal Cliff",
                "kind": "cliff set",
                "url": "https://www.fab.com/listings/08fc1d81-3d5b-463c-9110-bb95dfa6c53f",
            },
            {
                "title": "Nordic Coastal Boulders",
                "kind": "rock kit",
                "url": "https://www.fab.com/listings/d76ef4ef-82d1-4e5e-a90c-b8ec1f21af33",
            },
        ],
    },
    {
        "slug": "canopy",
        "label": "Canopy Habitat",
        "biome": "Forest / Jungle",
        "ambient": "Wet foliage, canopy haze, layered moss",
        "summary": "A lush member loft with hanging growth, forest-shadow walls, and a living display rail behind the main screen.",
        "setup": [
            "mossy floor accents",
            "green-cast canopy lighting",
            "tropical cliff and foliage references",
        ],
        "accent": "#6cff9b",
        "assets": [
            {
                "title": "Tropical Mossy Forest Ground",
                "kind": "ground surface",
                "url": "https://www.fab.com/listings/053e7d26-86f4-44bb-846d-4f6743edf1aa",
            },
            {
                "title": "Tropical Cliff Overhang",
                "kind": "cliff set",
                "url": "https://www.fab.com/listings/e8386e4d-880e-470f-bc60-68f4f25693a0",
            },
        ],
    },
    {
        "slug": "desert",
        "label": "Desert Circuit",
        "biome": "Desert / Badlands",
        "ambient": "Hot wind, amber edge light, carved stone",
        "summary": "A high-contrast rally bay with sandstone geometry, sun-bleached floor tones, and a sharper pit-lane silhouette.",
        "setup": [
            "sandstone feature wall",
            "warm amber tracking lights",
            "dry terrain display shelf",
        ],
        "accent": "#ffb15c",
        "assets": [
            {
                "title": "Sandstone Rock Formations",
                "kind": "rock kit",
                "url": "https://www.fab.com/listings/6f5627d1-6bc0-4380-8c22-2af9bceab07a",
            },
            {
                "title": "Desert Buttes and Dunes",
                "kind": "terrain cluster",
                "url": "https://www.fab.com/listings/b4d33c7e-3767-4e5d-92d3-0202ad387dab",
            },
        ],
    },
    {
        "slug": "alpine",
        "label": "Alpine Watch",
        "biome": "Alpine / Snow",
        "ambient": "Cold air, frost glow, high-altitude glass",
        "summary": "A mountain watch room with frozen light bands, brighter telemetry contrast, and a clean ice-blue operator deck.",
        "setup": [
            "frosted panorama wall",
            "snow-reflective floor sheen",
            "glacial side-light and sparse pine detail",
        ],
        "accent": "#b6e4ff",
        "assets": [
            {
                "title": "Snow Covered Branches",
                "kind": "foliage kit",
                "url": "https://www.fab.com/listings/198d75ef-20d9-4c42-a2ed-c9e8d91f81ee",
            },
            {
                "title": "Snowy Cliff Pack",
                "kind": "cliff set",
                "url": "https://www.fab.com/listings/6034cc5c-7f41-4d77-9f1c-54e02616553e",
            },
        ],
    },
    {
        "slug": "volcanic",
        "label": "Volcanic Forge",
        "biome": "Volcanic / Nightmare",
        "ambient": "Basalt, ember glow, high heat warning",
        "summary": "A hotter forge chamber with black stone surfaces, ember seams, and the most aggressive room treatment in the suite.",
        "setup": [
            "basalt wall ribs",
            "ember backlight and warning bars",
            "lava-zone display shelf",
        ],
        "accent": "#ff6a4f",
        "assets": [
            {
                "title": "Volcanic Rock Shelf",
                "kind": "rock shelf",
                "url": "https://www.fab.com/listings/6e61e8db-6021-4543-a518-1718c80ad470",
            },
            {
                "title": "Basalt Cliff Formations",
                "kind": "cliff set",
                "url": "https://www.fab.com/listings/bd7332de-c8c0-47fe-bc94-5899930a1b24",
            },
        ],
    },
    {
        "slug": "wetlands",
        "label": "Wetlands Signal",
        "biome": "Wetlands / Marsh",
        "ambient": "Marsh fog, moss water, muted field light",
        "summary": "A softer biolab suite with misty backplates, wet-ground reflections, and a calmer habitat-forward atmosphere.",
        "setup": [
            "mist-panel rear wall",
            "marsh-toned floor reflections",
            "moss and wet stone side bay",
        ],
        "accent": "#8fe0c1",
        "assets": [
            {
                "title": "Marsh Ground Surface",
                "kind": "ground surface",
                "url": "https://www.fab.com/listings/cfd31b6e-6d6f-47f1-b2b0-6aeb430cc6a5",
            },
            {
                "title": "Swamp Rock Cluster",
                "kind": "rock kit",
                "url": "https://www.fab.com/listings/0915f2f6-5a9b-4347-9a33-9bf1835e24a7",
            },
        ],
    },
]

ROOM_THEME_MAP = {theme["slug"]: theme for theme in ROOM_THEME_CATALOG}
ROOM_THEME_ALIASES = {
    "": "coastal",
    "stock": "coastal",
    "miami": "coastal",
    "forest": "canopy",
    "tokyo": "wetlands",
    "retro": "desert",
    "marble": "alpine",
}

try:
    from oracle_db import (
        get_audio_tracks,
        get_member_islands,
        get_member_room,
        get_member_tickets,
        set_room_theme,
    )

    ROOM_DB = True
except ImportError:
    ROOM_DB = False

    def get_member_room(epic_id):
        return {"theme": "", "tickets": 0}

    def set_room_theme(epic_id, theme):
        return False

    def get_member_tickets(epic_id):
        return 0

    def get_member_islands(epic_id, limit=50):
        return []

    def get_audio_tracks(epic_id=None):
        return []


def _normalize_room_theme(raw_theme: str) -> str:
    slug = str(raw_theme or "").strip().lower()
    slug = ROOM_THEME_ALIASES.get(slug, slug)
    return slug if slug in ROOM_THEME_MAP else "coastal"


def _normalize_stickers(raw_value) -> list[str]:
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = [part.strip() for part in text.split(",")]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def _serialize_islands(islands: list[dict]) -> list[dict]:
    rows = []
    for island in islands or []:
        rows.append(
            {
                "name": str(island.get("name") or "Untitled island"),
                "seed": str(island.get("seed") or "0000"),
                "dominant_biome": str(island.get("dominant_biome") or "Mixed biome"),
                "preview_url": str(island.get("preview_url") or ""),
                "stickers": _normalize_stickers(island.get("stickers")),
            }
        )
    return rows


def _member_cards(epic_connected: bool, wins: int, kd: float, tickets: int, island_count: int, upload_count: int) -> list[dict]:
    return [
        {
            "label": "Epic link",
            "value": "LIVE" if epic_connected else "PENDING",
            "meta": "Identity lane",
        },
        {
            "label": "Ticket bank",
            "value": str(tickets),
            "meta": "Member economy",
        },
        {
            "label": "Forge saves",
            "value": str(island_count),
            "meta": "Island wall",
        },
        {
            "label": "Audio uploads",
            "value": str(upload_count),
            "meta": "Forge intake",
        },
        {
            "label": "Wins",
            "value": str(wins),
            "meta": "Competitive signal",
        },
        {
            "label": "K / D",
            "value": f"{kd:.2f}",
            "meta": "Pressure index",
        },
    ]


@room_bp.route("/room")
def room():
    user = session.get("user") or {}
    admin_authed = bool(session.get("admin_authed"))
    if not user and not admin_authed:
        return redirect("/home")

    epic_id = user.get("account_id") or session.get("epic_id") or ""
    name = user.get("display_name") or session.get("display_name") or ("Admin" if admin_authed else "Player")
    skin_img = user.get("skin_img") or session.get("skin_img") or ""
    wins = int(user.get("wins") or session.get("wins") or 0)
    kd = float(user.get("kd") or session.get("kd") or 0.0)

    room_data = get_member_room(epic_id) if ROOM_DB and epic_id else {"theme": session.get("admin_room_theme", ""), "tickets": 0}
    theme_slug = _normalize_room_theme((room_data or {}).get("theme") or session.get("admin_room_theme", ""))
    active_theme = ROOM_THEME_MAP[theme_slug]
    tickets = get_member_tickets(epic_id) if ROOM_DB and epic_id else int((room_data or {}).get("tickets") or 0)
    islands = _serialize_islands(get_member_islands(epic_id, limit=12) if epic_id else [])
    upload_count = len(get_audio_tracks(epic_id) or []) if epic_id else 0
    island_count = len(islands)
    epic_connected = bool(session.get("epic_access_token") or session.get("access_token") or epic_id)

    bootstrap = {
        "theme": theme_slug,
        "themes": ROOM_THEME_CATALOG,
        "stats": {
            "wins": wins,
            "kd": round(kd, 2),
            "tickets": tickets,
            "islands": island_count,
            "uploads": upload_count,
        },
        "identity": {
            "name": name,
            "epic_connected": epic_connected,
            "admin_authed": admin_authed,
        },
    }

    return render_template(
        "room.html",
        name=name,
        skin_img=skin_img,
        wins=wins,
        kd=round(kd, 2),
        tickets=tickets,
        room_theme=theme_slug,
        room_theme_catalog=ROOM_THEME_CATALOG,
        active_theme=active_theme,
        islands=islands,
        island_count=island_count,
        upload_count=upload_count,
        member_cards=_member_cards(epic_connected, wins, kd, tickets, island_count, upload_count),
        room_bootstrap=bootstrap,
    )


@room_bp.route("/api/set_room_theme", methods=["POST"])
def api_set_room_theme():
    user = session.get("user") or {}
    admin_authed = bool(session.get("admin_authed"))
    if not user and not admin_authed:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    requested_theme = data.get("theme", "")
    theme = _normalize_room_theme(requested_theme)
    if theme not in ROOM_THEME_MAP:
        return jsonify({"ok": False, "error": "Invalid theme"}), 400

    epic_id = user.get("account_id") or session.get("epic_id") or ""
    if ROOM_DB and epic_id:
        set_room_theme(epic_id, theme)
    else:
        session["admin_room_theme"] = theme

    return jsonify({"ok": True, "theme": theme, "active_theme": ROOM_THEME_MAP[theme]})
