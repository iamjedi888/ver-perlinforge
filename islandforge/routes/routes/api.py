"""
routes/api.py — JSON REST endpoints
  GET  /api/members          Member list
  POST /api/post             Submit a social feed post
  POST /api/like/<id>        Like a feed post
  POST /api/forge/generate   Trigger island generation (async)
"""

from flask import Blueprint, request, jsonify, session
from oracle_db import get_members, save_post, like_post

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/members")
def members():
    limit = min(int(request.args.get("limit", 50)), 200)
    rows  = get_members(limit=limit)
    return jsonify([dict(r) for r in rows])


@api_bp.route("/post", methods=["POST"])
def post():
    data        = request.get_json(silent=True) or request.form
    epic_id     = session.get("epic_id") or data.get("epic_id", "anonymous")
    display_name= session.get("display_name") or data.get("display_name", "Player")
    caption     = (data.get("caption") or "").strip()[:1000]
    embed_url   = (data.get("embed_url") or "").strip()
    skin_img    = (data.get("skin_img") or "").strip()

    if not caption and not embed_url:
        return jsonify({"error": "caption or embed_url required"}), 400

    post_id = save_post(
        epic_id      = epic_id,
        display_name = display_name,
        caption      = caption,
        embed_url    = embed_url,
        skin_img     = skin_img,
    )
    return jsonify({"ok": True, "id": post_id})


@api_bp.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):
    new_count = like_post(post_id)
    return jsonify({"ok": True, "likes": new_count})
