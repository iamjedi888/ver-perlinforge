from flask import Blueprint, request, jsonify, render_template
from oracle_db import get_channels, suggest_channel as db_suggest
from channels_page import build_channels_context

channels_bp = Blueprint("channels", __name__)

@channels_bp.route("/channels")
def channels():
    return render_template("channels.html", **build_channels_context(get_channels()))

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
