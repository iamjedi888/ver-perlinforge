"""
routes/platform.py — Core platform pages
  /        /home     Homepage
  /forge             Island Forge UI
  /gallery           Island gallery
  /feed              TikTok-style social feed
  /community         Members + announcements
  /dashboard         Member dashboard (requires Epic login)
  /admin             Admin panel
  /health            JSON health check
"""

import os
from flask import Blueprint, render_template, request, redirect, session, jsonify
from oracle_db import (
    get_member_count, get_island_count, get_audio_count,
    get_islands, get_members, get_announcements, get_posts,
    get_member, save_announcement, oracle_online, oci_sdk_available
)

platform_bp = Blueprint("platform", __name__)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "triptokadmin2026")


# ── SHARED HEAD BUILDER ─────────────────────────────────────────
def _head(title="TriptokForge", description="Fortnite Creative Community Platform"):
    return f"""
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{title}</title>
    <meta name="description" content="{description}"/>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg"/>
    <link rel="shortcut icon" href="/favicon.svg"/>
    <link rel="apple-touch-icon" href="/favicon.svg"/>
    <link rel="manifest" href="/manifest.json"/>
    <meta name="theme-color" content="#07090d"/>
    <meta property="og:title" content="{title}"/>
    <meta property="og:description" content="{description}"/>
    <meta property="og:image" content="https://triptokforge.org/static/og.png"/>
    <meta property="og:url" content="https://triptokforge.org"/>
    <meta name="twitter:card" content="summary_large_image"/>
    """


# ── HOME ────────────────────────────────────────────────────────
@platform_bp.route("/")
@platform_bp.route("/home")
def home():
    n_members = get_member_count()
    n_islands = get_island_count()
    n_audio   = get_audio_count()
    return render_template(
        "home.html",
        head=_head("TriptokForge — Fortnite Creative Community"),
        n_members=n_members,
        n_islands=n_islands,
        n_audio=n_audio,
    )


# ── FORGE ───────────────────────────────────────────────────────
@platform_bp.route("/forge")
def forge():
    return render_template(
        "forge.html",
        head=_head("Island Forge — Generate UEFN Islands from Audio"),
    )


# ── GALLERY ─────────────────────────────────────────────────────
@platform_bp.route("/gallery")
def gallery():
    islands = get_islands(limit=50)
    return render_template(
        "gallery.html",
        head=_head("Island Gallery — TriptokForge"),
        islands=islands,
    )


# ── FEED ────────────────────────────────────────────────────────
@platform_bp.route("/feed")
def feed():
    posts = get_posts(limit=50)
    return render_template(
        "feed.html",
        head=_head("Community Feed — TriptokForge"),
        posts=posts,
    )


# ── COMMUNITY ───────────────────────────────────────────────────
@platform_bp.route("/community")
def community():
    members       = get_members(limit=50)
    announcements = get_announcements()
    return render_template(
        "community.html",
        head=_head("Community — TriptokForge"),
        members=members,
        announcements=announcements,
    )


# ── DASHBOARD ───────────────────────────────────────────────────
@platform_bp.route("/dashboard")
def dashboard():
    epic_id = session.get("epic_id")
    if not epic_id:
        return redirect("/auth/epic")
    member  = get_member(epic_id)
    islands = get_islands(epic_id=epic_id, limit=20)
    return render_template(
        "dashboard.html",
        head=_head("My Dashboard — TriptokForge"),
        member=member,
        islands=islands,
    )


# ── ADMIN ───────────────────────────────────────────────────────
@platform_bp.route("/admin", methods=["GET", "POST"])
def admin():
    authed = session.get("admin_authed")

    if request.method == "POST":
        action = request.form.get("action")

        # Login
        if action == "login":
            if request.form.get("password") == ADMIN_PASSWORD:
                session["admin_authed"] = True
                authed = True
            else:
                return render_template("admin.html", head=_head("Admin"), error="Wrong password", authed=False)

        # Post announcement
        if action == "announce" and authed:
            save_announcement(
                title  = request.form.get("title", ""),
                body   = request.form.get("body", ""),
                pinned = bool(request.form.get("pinned")),
            )

    members       = get_members(limit=100) if authed else []
    announcements = get_announcements()    if authed else []
    return render_template(
        "admin.html",
        head=_head("Admin — TriptokForge"),
        authed=authed,
        members=members,
        announcements=announcements,
    )


# ── HEALTH ──────────────────────────────────────────────────────
@platform_bp.route("/health")
def health():
    return jsonify({
        "status":       "ok",
        "oracle_online": oracle_online(),
        "oci_sdk":       oci_sdk_available(),
        "members":       get_member_count(),
        "islands":       get_island_count(),
        "audio":         get_audio_count(),
    })
