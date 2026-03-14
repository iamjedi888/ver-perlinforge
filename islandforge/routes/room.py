"""
routes/room.py — /room  card wall + theme API
"""
import os
from flask import Blueprint, render_template, session, redirect, request, jsonify

room_bp = Blueprint("room", __name__)

try:
    from oracle_db import (
        get_all_members, get_recent_islands,
        get_member_room, set_room_theme, get_member_tickets,
    )
    ROOM_DB = True
except ImportError:
    ROOM_DB = False
    def get_member_room(epic_id): return {"theme": "", "tickets": 0}
    def set_room_theme(epic_id, theme): pass
    def get_member_tickets(epic_id): return 0

try:
    from oracle_db import get_member_islands
    HAS_ISLANDS = True
except ImportError:
    HAS_ISLANDS = False
    def get_member_islands(epic_id, limit=50): return []

@room_bp.route("/room")
def room():
    user = session.get("user")
    if not user:
        return redirect("/home")

    epic_id   = user.get("account_id", "")
    name      = user.get("display_name", "Player")
    skin_img  = user.get("skin_img", "")
    wins      = user.get("wins", 0)
    kd        = user.get("kd", 0.0)

    # Room data
    room_data  = get_member_room(epic_id) if ROOM_DB else {"theme": "", "tickets": 0}
    tickets    = get_member_tickets(epic_id) if ROOM_DB else 0
    room_theme = room_data.get("theme", "") if room_data else ""

    # Islands for this member
    islands = get_member_islands(epic_id, limit=50) if HAS_ISLANDS else []

    return render_template("room.html",
        name=name,
        skin_img=skin_img,
        wins=wins,
        kd=kd,
        tickets=tickets,
        room_theme=room_theme,
        islands=islands,
    )

@room_bp.route("/api/set_room_theme", methods=["POST"])
def api_set_room_theme():
    user = session.get("user")
    if not user:
        return jsonify({"ok": False, "error": "Not logged in"})
    data  = request.get_json(force=True)
    theme = data.get("theme", "")
    allowed = ["", "tokyo", "miami", "marble", "forest", "retro"]
    if theme not in allowed:
        return jsonify({"ok": False, "error": "Invalid theme"})
    if ROOM_DB:
        set_room_theme(user.get("account_id", ""), theme)
    return jsonify({"ok": True, "theme": theme})

