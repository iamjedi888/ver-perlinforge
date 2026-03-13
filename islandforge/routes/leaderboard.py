"""
routes/leaderboard.py — /leaderboard  +  /api/leaderboard/*
"""
import os, requests
from flask import Blueprint, render_template, session, jsonify, request

leaderboard_bp = Blueprint("leaderboard", __name__)

FORTNITE_API_KEY = os.environ.get("FORTNITE_API_KEY", "")
FORTNITE_API_BASE = "https://fortnite-api.com"

try:
    from oracle_db import get_all_members, db_available
    HAS_DB = True
except ImportError:
    HAS_DB = False
    def get_all_members(): return []
    def db_available(): return False

# ── PAGE ─────────────────────────────────────────────────

@leaderboard_bp.route("/leaderboard")
def leaderboard():
    user = session.get("user")
    current_user = {
        "account_id":   user.get("account_id", ""),
        "display_name": user.get("display_name", ""),
    } if user else None
    return render_template("leaderboard.html", current_user=current_user)

# ── API: MEMBERS ─────────────────────────────────────────

@leaderboard_bp.route("/api/leaderboard/members")
def api_leaderboard_members():
    """Return all TriptokForge members sorted by wins."""
    if not HAS_DB:
        return jsonify({"members": [], "error": "DB unavailable"})
    try:
        raw = get_all_members()
        members = []
        for m in raw:
            members.append({
                "epic_id":      m.get("epic_id", ""),
                "display_name": m.get("display_name", "Unknown"),
                "skin_img":     m.get("skin_img", ""),
                "wins":         int(m.get("wins") or 0),
                "kd":           float(m.get("kd") or 0.0),
                "tickets":      int(m.get("tickets") or 0),
                "ranked_division": m.get("ranked_division", ""),
            })
        return jsonify({"members": members, "count": len(members)})
    except Exception as e:
        return jsonify({"members": [], "error": str(e)})

# ── API: GLOBAL ───────────────────────────────────────────

@leaderboard_bp.route("/api/leaderboard/global")
def api_leaderboard_global():
    """Proxy fortnite-api.com global stats leaderboard."""
    if not FORTNITE_API_KEY:
        return jsonify({"players": [], "error": "No API key configured"})

    stat = request.args.get("stat", "wins")
    # fortnite-api.com uses different stat names
    stat_map = {"wins": "wins", "kd": "kd", "kills": "kills"}
    api_stat = stat_map.get(stat, "wins")

    try:
        headers = {
            "Authorization": FORTNITE_API_KEY,
            "User-Agent":    "TriptokForge/1.0",
        }
        # v2/stats endpoint — top players by lifetime stat
        url = f"{FORTNITE_API_BASE}/v2/stats/br/v2"
        # fortnite-api.com doesn't have a global leaderboard endpoint directly
        # but we can hit /v1/leaderboards if available, else return empty with note
        # Use the bulk stats approach or fall back gracefully
        # For now return placeholder — wire real endpoint when confirmed
        return jsonify({
            "players": [],
            "note": "Global leaderboard requires fortnite-api.com bulk endpoint — coming soon",
            "stat": stat
        })
    except Exception as e:
        return jsonify({"players": [], "error": str(e)})
