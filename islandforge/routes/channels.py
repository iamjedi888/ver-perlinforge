from flask import Blueprint, jsonify, render_template, request, session
from oracle_db import get_channels, suggest_channel as db_suggest
from channels_page import build_channels_context, resolve_channel_rotation, split_source_urls

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
    description = data.get("description", "").strip()
    if not name or not embed_url:
        return jsonify({"error":"required"}), 400
    suggested_by = (
        session.get("display_name")
        or session.get("epic_id")
        or "anonymous"
    )
    ok = db_suggest(
        name=name,
        category=category,
        embed_url=embed_url,
        description=description,
        suggested_by=suggested_by,
    )
    if not ok:
        return jsonify({"error": "save_failed"}), 500
    return jsonify({"ok": True})


@channels_bp.route("/api/channel_queue", methods=["POST"])
def channel_queue_route():
    data = request.get_json(silent=True) or {}
    raw_sources = data.get("source_urls") or []
    raw_terms = data.get("search_terms") or []
    if isinstance(raw_sources, str):
        raw_sources = split_source_urls(raw_sources)
    if isinstance(raw_terms, str):
        raw_terms = [raw_terms]
    sources = [str(item or "").strip() for item in raw_sources if str(item or "").strip()]
    search_terms = [str(item or "").strip() for item in raw_terms if str(item or "").strip()]
    if not sources:
        return jsonify({"error": "required"}), 400
    try:
        resolved = resolve_channel_rotation(sources, search_terms=search_terms)
        if not resolved:
            return jsonify({"error": "unresolved"}), 404
        return jsonify({"ok": True, **resolved})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
