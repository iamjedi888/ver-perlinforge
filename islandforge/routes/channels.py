from flask import Blueprint, request, jsonify, session
from oracle_db import get_channels, suggest_channel as db_suggest
from channels_page import build_channels_page

channels_bp = Blueprint("channels", __name__)

@channels_bp.route("/channels")
def channels():
    logged_in = bool(session.get("user") or session.get("epic_id"))
    return build_channels_page(
        get_channels(),
        portal_exit_href="/dashboard" if logged_in else "/home",
        portal_exit_label="Dashboard" if logged_in else "Home",
    )

@channels_bp.route("/api/suggest_channel", methods=["POST"])
def suggest_channel_route():
    data = request.get_json(silent=True) or request.form
    name = data.get("name","").strip()
    embed_url = data.get("embed_url","").strip()
    category = data.get("category","Other").strip()
    if not name or not embed_url:
        return jsonify({"error":"required"}), 400
    db_suggest(name=name, category=category, embed_url=embed_url, description="", suggested_by="anonymous")
    return jsonify({"ok": True})
