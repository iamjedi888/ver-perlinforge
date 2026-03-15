from flask import Blueprint, request, jsonify, session
from oracle_db import get_all_members, create_post, like_post, get_wp_tracks, add_wp_track, delete_wp_track

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/members")
def members():
    return jsonify([dict(r) for r in (get_all_members() or [])])

@api_bp.route("/post", methods=["POST"])
def post():
    data = request.get_json(silent=True) or request.form
    epic_id = session.get("epic_id") or ""
    admin_authed = bool(session.get("admin_authed"))
    if not epic_id and not admin_authed:
        return jsonify({"error": "login_required"}), 401
    display_name = session.get("display_name") or ("Admin" if admin_authed else "Player")
    caption = (data.get("caption") or "").strip()[:1000]
    embed_url = (data.get("embed_url") or "").strip()
    skin_img = (session.get("skin_img") or data.get("skin_img") or "").strip()
    if not caption and not embed_url:
        return jsonify({"error":"caption or embed_url required"}), 400
    post_id = create_post(epic_id=epic_id, display_name=display_name, skin_img=skin_img, caption=caption, embed_url=embed_url)
    return jsonify({"ok":True,"id":post_id})

@api_bp.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):
    return jsonify({"ok":True,"likes":like_post(post_id)})

# ── Whitepages Player Tracks ────────────────────────────────

@api_bp.route("/whitepages/tracks", methods=["GET"])
def wp_tracks_get():
    return jsonify(get_wp_tracks() or [])

@api_bp.route("/whitepages/tracks", methods=["POST"])
def wp_tracks_add():
    if not session.get("admin_authed"):
        return jsonify({"error": "unauthorized"}), 403
    data = request.get_json(silent=True) or request.form
    title       = (data.get("title") or "").strip()[:256]
    artist      = (data.get("artist") or "").strip()[:128]
    source_type = (data.get("source_type") or "soundcloud").strip()[:32]
    embed_url   = (data.get("embed_url") or "").strip()[:1024]
    if not title or not embed_url:
        return jsonify({"error": "title and embed_url required"}), 400
    if source_type not in ("soundcloud", "youtube", "audio"):
        source_type = "soundcloud"
    new_id = add_wp_track(title, artist, source_type, embed_url)
    return jsonify({"ok": True, "id": new_id})

@api_bp.route("/whitepages/tracks/<int:track_id>", methods=["DELETE"])
def wp_tracks_delete(track_id):
    if not session.get("admin_authed"):
        return jsonify({"error": "unauthorized"}), 403
    ok = delete_wp_track(track_id)
    return jsonify({"ok": ok})
