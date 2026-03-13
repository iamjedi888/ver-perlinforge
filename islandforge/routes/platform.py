from flask import Blueprint, render_template, request, redirect, session, jsonify, send_from_directory, Response
import os
from oracle_db import get_all_members, get_recent_islands, get_audio_tracks, get_announcements, get_posts, post_announcement, db_available, upsert_member, status

platform_bp = Blueprint("platform", __name__)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "triptokadmin2026")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def serve_index():
    return send_from_directory(ROOT, "index.html")

@platform_bp.route("/")
@platform_bp.route("/home")
def home():
    return serve_index()

@platform_bp.route("/forge")
def forge():
    return serve_index()

@platform_bp.route("/gallery")
def gallery():
    return serve_index()

@platform_bp.route("/feed")
def feed():
    posts = get_posts(limit=50)
    t = os.path.join(ROOT, "templates", "feed.html")
    if os.path.exists(t):
        return render_template("feed.html", posts=posts)
    return serve_index()

@platform_bp.route("/community")
def community():
    t = os.path.join(ROOT, "templates", "community.html")
    if os.path.exists(t):
        return render_template("community.html", members=get_all_members(), announcements=get_announcements())
    return serve_index()

@platform_bp.route("/dashboard")
def dashboard():
    epic_id = session.get("epic_id")
    if not epic_id:
        return redirect("/auth/epic")
    t = os.path.join(ROOT, "templates", "dashboard.html")
    if os.path.exists(t):
        return render_template("dashboard.html", member={"epic_id":epic_id,"display_name":session.get("display_name")}, islands=get_recent_islands(limit=20))
    return serve_index()

@platform_bp.route("/admin", methods=["GET","POST"])
def admin():
    authed = session.get("admin_authed")
    if request.method == "POST":
        if request.form.get("action") == "login":
            if request.form.get("password") == ADMIN_PASSWORD:
                session["admin_authed"] = True
                authed = True
            else:
                return Response("Wrong password", 403)
        if request.form.get("action") == "announce" and authed:
            post_announcement(title=request.form.get("title",""), body=request.form.get("body",""), pinned=bool(request.form.get("pinned")))
    t = os.path.join(ROOT, "templates", "admin.html")
    if os.path.exists(t):
        return render_template("admin.html", authed=authed, members=get_all_members() if authed else [], announcements=get_announcements() if authed else [])
    return serve_index()

@platform_bp.route("/health")
def health():
    st = status()
    members = get_all_members() or []
    islands = get_recent_islands(limit=999) or []
    audio = get_audio_tracks() or []
    return jsonify({**st, "service":"triptokforge","version":"4.0","members":len(members),"islands":len(islands),"audio":len(audio)})
