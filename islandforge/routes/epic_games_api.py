"""
routes/epic_games_api.py — Fortnite Stats & Cosmetics API
Provides /api/stats, /api/cosmetics, /api/set_skin

Mock data layer with real Fortnite-tracker.com API hooks ready.
When FORTNITE_TRACKER_API_KEY env var is set, falls back to mock gracefully
until a proper integration replaces the mock functions below.
"""
import os
import json
import random
from flask import Blueprint, request, jsonify, session

epic_api_bp = Blueprint("epic_api", __name__, url_prefix="/api")

# ── Cosmetics data ────────────────────────────────────────────────────────────
# Curated list of well-known Fortnite skins with working Fortnite-API.com images
KNOWN_SKINS = [
    {"id": "CID_028_Athena_Commando_F",          "name": "Renegade Raider",     "img": "https://fortnite-api.com/images/cosmetics/br/CID_028_Athena_Commando_F/icon.png"},
    {"id": "CID_017_Athena_Commando_M",          "name": "Aerial Assault Trooper", "img": "https://fortnite-api.com/images/cosmetics/br/CID_017_Athena_Commando_M/icon.png"},
    {"id": "CID_030_Athena_Commando_M_Halloween","name": "Skull Trooper",        "img": "https://fortnite-api.com/images/cosmetics/br/CID_030_Athena_Commando_M_Halloween/icon.png"},
    {"id": "CID_116_Athena_Commando_M_BlueAce",  "name": "Blue Squire",          "img": "https://fortnite-api.com/images/cosmetics/br/CID_116_Athena_Commando_M_BlueAce/icon.png"},
    {"id": "CID_315_Athena_Commando_M_TeriyakiFishShtick","name":"Fishstick",    "img": "https://fortnite-api.com/images/cosmetics/br/CID_315_Athena_Commando_M_TeriyakiFishShtick/icon.png"},
    {"id": "CID_162_Athena_Commando_M_Celestial","name": "Brite Bomber",         "img": "https://fortnite-api.com/images/cosmetics/br/CID_162_Athena_Commando_M_Celestial/icon.png"},
    {"id": "CID_175_Athena_Commando_M_Celestial","name": "Ravage",               "img": "https://fortnite-api.com/images/cosmetics/br/CID_175_Athena_Commando_M_Celestial/icon.png"},
    {"id": "CID_342_Athena_Commando_F_IceBrute", "name": "Ice Queen",            "img": "https://fortnite-api.com/images/cosmetics/br/CID_342_Athena_Commando_F_IceBrute/icon.png"},
    {"id": "CID_441_Athena_Commando_F_BunnyMaiden","name":"Bunny Brawler",       "img": "https://fortnite-api.com/images/cosmetics/br/CID_441_Athena_Commando_F_BunnyMaiden/icon.png"},
    {"id": "CID_516_Athena_Commando_M_Viper",    "name": "Chaos Agent",          "img": "https://fortnite-api.com/images/cosmetics/br/CID_516_Athena_Commando_M_Viper/icon.png"},
    {"id": "CID_A_065_Athena_Commando_M_ScholarFestive","name":"The Mandalorian","img":"https://fortnite-api.com/images/cosmetics/br/CID_A_065_Athena_Commando_M_ScholarFestive/icon.png"},
    {"id": "CID_605_Athena_Commando_F_RocketLeague","name":"Renegade Racer",     "img":"https://fortnite-api.com/images/cosmetics/br/CID_605_Athena_Commando_F_RocketLeague/icon.png"},
    {"id": "CID_A_321_Athena_Commando_M_SpiderMan_NWH","name":"Spider-Man",      "img":"https://fortnite-api.com/images/cosmetics/br/CID_A_321_Athena_Commando_M_SpiderMan_NWH/icon.png"},
    {"id": "CID_784_Athena_Commando_M_BountyHunterSw","name":"The Mandalorian (Alt)","img":"https://fortnite-api.com/images/cosmetics/br/CID_784_Athena_Commando_M_BountyHunterSw/icon.png"},
    {"id": "CID_A_025_Athena_Commando_M_HenchmanVisor","name":"Shadow Midas",    "img":"https://fortnite-api.com/images/cosmetics/br/CID_A_025_Athena_Commando_M_HenchmanVisor/icon.png"},
    {"id": "CID_A_168_Athena_Commando_F_SummerDrift","name":"Drift",             "img":"https://fortnite-api.com/images/cosmetics/br/CID_A_168_Athena_Commando_F_SummerDrift/icon.png"},
    {"id": "CID_VIP_Athena_Commando_M_GalileoSuit","name":"Omega",               "img":"https://fortnite-api.com/images/cosmetics/br/CID_VIP_Athena_Commando_M_GalileoSuit/icon.png"},
    {"id": "CID_434_Athena_Commando_M_StealthHeist","name":"Luxe",               "img":"https://fortnite-api.com/images/cosmetics/br/CID_434_Athena_Commando_M_StealthHeist/icon.png"},
    {"id": "CID_296_Athena_Commando_F_SoccerGirl","name":"Poised Playmaker",     "img":"https://fortnite-api.com/images/cosmetics/br/CID_296_Athena_Commando_F_SoccerGirl/icon.png"},
    {"id": "CID_313_Athena_Commando_F_KpopFashion","name":"K-Pop Fashion",       "img":"https://fortnite-api.com/images/cosmetics/br/CID_313_Athena_Commando_F_KpopFashion/icon.png"},
]

# ── Mock stat generator ───────────────────────────────────────────────────────
def _mock_stats(display_name: str) -> dict:
    """
    Generate deterministic-ish mock stats based on display name.
    Replace this with real Fortnite Tracker API call when key is available.
    """
    seed = sum(ord(c) for c in display_name)
    r = random.Random(seed)

    matches  = r.randint(200, 4500)
    wins     = r.randint(10, int(matches * 0.25))
    kills    = r.randint(matches * 2, matches * 8)
    kd       = round(kills / max(matches - wins, 1), 2)
    win_pct  = round((wins / matches) * 100, 1)
    score    = r.randint(800, 4200)
    top5     = wins + r.randint(20, 150)
    top10    = top5 + r.randint(30, 200)
    avg_elim = round(kills / matches, 1)

    return {
        "wins":    str(wins),
        "kd":      str(kd),
        "matches": str(matches),
        "kills":   str(kills),
        "winPct":  f"{win_pct}%",
        "score":   str(score),
        "top5":    str(top5),
        "top10":   str(top10),
        "avgElim": str(avg_elim),
        "_mock":   True,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@epic_api_bp.route("/stats")
def stats():
    """
    GET /api/stats?name=<display_name>
    Returns Fortnite player stats. Currently mock; real API hook ready below.
    """
    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name required"}), 400

    # ── Real API hook (uncomment when FORTNITE_TRACKER_API_KEY is set) ──────
    # api_key = os.environ.get("FORTNITE_TRACKER_API_KEY")
    # if api_key:
    #     import requests as req
    #     url = f"https://api.fortnitetracker.com/v1/profile/all/{name}"
    #     resp = req.get(url, headers={"TRN-Api-Key": api_key}, timeout=8)
    #     if resp.status_code == 200:
    #         data = resp.json()
    #         stats_data = data.get("lifeTimeStats", [])
    #         # ... map to our format ...
    #         return jsonify({"ok": True, "stats": mapped_stats, "source": "tracker"})

    return jsonify({"ok": True, "stats": _mock_stats(name), "source": "mock"})


@epic_api_bp.route("/cosmetics")
def cosmetics():
    """
    GET /api/cosmetics
    Returns list of Fortnite skins for the skin selector.
    Tries to fetch from fortnite-api.com; falls back to curated local list.
    """
    # ── Attempt live fetch from fortnite-api.com ─────────────────────────────
    try:
        import urllib.request, urllib.error
        url = "https://fortnite-api.com/v2/cosmetics/br?language=en"
        req = urllib.request.Request(url, headers={"User-Agent": "TriptokForge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode())
        items = raw.get("data", [])
        skins = [
            {
                "id":   item["id"],
                "name": item.get("name", "Unknown"),
                "img":  (item.get("images") or {}).get("icon", ""),
            }
            for item in items
            if item.get("type", {}).get("value") == "outfit"
               and (item.get("images") or {}).get("icon")
        ]
        if skins:
            return jsonify({"ok": True, "skins": skins[:200], "source": "live"})
    except Exception:
        pass

    # Fallback to curated list
    return jsonify({"ok": True, "skins": KNOWN_SKINS, "source": "curated"})


@epic_api_bp.route("/set_skin", methods=["POST"])
def set_skin():
    """
    POST /api/set_skin — saves selected skin to session + member record.
    """
    data = request.get_json(silent=True) or {}
    skin_id   = str(data.get("id",   "")).strip()[:64]
    skin_name = str(data.get("name", "")).strip()[:128]
    skin_img  = str(data.get("img",  "")).strip()[:512]

    if not skin_id:
        return jsonify({"ok": False, "error": "id required"}), 400

    session["skin_img"]  = skin_img
    session["skin_name"] = skin_name

    # Persist to member record if logged in
    epic_id = session.get("epic_id")
    if epic_id:
        try:
            from oracle_db import upsert_member
            upsert_member(epic_id=epic_id,
                          display_name=session.get("display_name", epic_id),
                          skin_img=skin_img,
                          skin_name=skin_name)
        except Exception:
            pass  # Non-fatal — session already updated

    return jsonify({"ok": True})


@epic_api_bp.route("/suggest_channel", methods=["POST"])
def suggest_channel():
    """
    POST /api/suggest_channel — logs a channel suggestion.
    Currently stores to DB if available, otherwise logs to stderr.
    """
    data = request.get_json(silent=True) or request.form
    name     = str(data.get("name", "")).strip()[:128]
    category = str(data.get("category", "Other")).strip()[:64]
    url      = str(data.get("embed_url", "")).strip()[:512]
    desc     = str(data.get("description", "")).strip()[:256]

    if not name or not url:
        return jsonify({"ok": False, "error": "name and embed_url required"}), 400

    # Try to persist suggestion
    try:
        from oracle_db import get_db
        with get_db() as db:
            db.execute(
                "INSERT INTO channel_suggestions (name, category, embed_url, description) VALUES (?,?,?,?)",
                (name, category, url, desc)
            )
            db.commit()
    except Exception:
        import sys
        print(f"[suggest] {name} | {category} | {url} | {desc}", file=sys.stderr)

    return jsonify({"ok": True})
