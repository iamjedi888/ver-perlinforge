from flask import Blueprint, request, jsonify, session
from oracle_db import get_all_members, create_post, like_post

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/members")
def members():
    return jsonify([dict(r) for r in (get_all_members() or [])])

@api_bp.route("/post", methods=["POST"])
def post():
    data = request.get_json(silent=True) or request.form
    epic_id = session.get("epic_id") or data.get("epic_id","anonymous")
    display_name = session.get("display_name") or data.get("display_name","Player")
    caption = (data.get("caption") or "").strip()[:1000]
    embed_url = (data.get("embed_url") or "").strip()
    skin_img = (data.get("skin_img") or "").strip()
    if not caption and not embed_url:
        return jsonify({"error":"caption or embed_url required"}), 400
    post_id = create_post(epic_id=epic_id, display_name=display_name, skin_img=skin_img, caption=caption, embed_url=embed_url)
    return jsonify({"ok":True,"id":post_id})

@api_bp.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):
    return jsonify({"ok":True,"likes":like_post(post_id)})
