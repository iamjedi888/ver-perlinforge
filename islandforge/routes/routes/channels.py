"""
routes/channels.py — Live channels TV guide
  /channels              Roku-style channel guide + embedded player
  /api/suggest_channel   POST — suggest a new channel
"""

from flask import Blueprint, request, jsonify
from oracle_db import get_channels, save_channel_suggestion
from channels_page import build_channels_page

channels_bp = Blueprint("channels", __name__)


@channels_bp.route("/channels")
def channels():
    rows = get_channels()
    return build_channels_page(rows)


@channels_bp.route("/api/suggest_channel", methods=["POST"])
def suggest_channel():
    data = request.get_json(silent=True) or request.form
    name      = data.get("name", "").strip()
    embed_url = data.get("embed_url", "").strip()
    category  = data.get("category", "Other").strip()

    if not name or not embed_url:
        return jsonify({"error": "name and embed_url required"}), 400

    save_channel_suggestion(name=name, embed_url=embed_url, category=category)
    return jsonify({"ok": True, "message": f"Thanks! '{name}' submitted for review."})
