"""
TriptokForge Main Server
All route logic lives in routes/ as Blueprints.
"""

import os

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

DISALLOWED_HOSTING_ENV_KEYS = (
    "VERCEL",
    "CF_PAGES",
    "CF_PAGES_BRANCH",
)


def _assert_supported_hosting():
    if os.environ.get("ALLOW_NON_ORACLE_DEPLOY") == "1":
        return
    detected = [key for key in DISALLOWED_HOSTING_ENV_KEYS if os.environ.get(key)]
    if not detected:
        return
    raise RuntimeError(
        "TriptokForge is configured for Oracle-hosted deployment only. "
        "Disconnect Vercel/Cloudflare Git deploys or set ALLOW_NON_ORACLE_DEPLOY=1 explicitly."
    )


_assert_supported_hosting()


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

PUBLIC_PATHS = {
    "/",
    "/home",
    "/privacy",
    "/health",
    "/favicon.svg",
    "/favicon.ico",
    "/manifest.json",
    "/sitemap.xml",
}

PUBLIC_GET_ONLY_PATHS = {
    "/whitepages",
    "/api/whitepages/tracks",
}

PUBLIC_PREFIXES = (
    "/static/",
    "/auth/",
    "/admin",
    "/ops",
)

PROTECTED_PAGE_ROOTS = (
    "/forge",
    "/gallery",
    "/feed",
    "/channels",
    "/community",
    "/esports",
    "/arena",
    "/dashboard",
    "/leaderboard",
    "/news",
    "/cardgame",
    "/room",
    "/generate",
    "/upload_audio",
    "/audio",
    "/download",
    "/random_seed",
)

PROTECTED_API_ROOTS = (
    "/api/members",
    "/api/post",
    "/api/like",
    "/api/whitepages",
    "/api/suggest_channel",
    "/api/channel_queue",
    "/api/leaderboard",
    "/api/news",
    "/api/presets",
    "/api/save_island",
    "/api/set_room_theme",
    "/api/stats",
    "/api/cosmetics",
    "/api/set_skin",
    "/api/ecosystem",
    "/api/dashboard",
    "/api/forge",
)


def _path_matches(path: str, roots: tuple[str, ...]) -> bool:
    normalized = (path or "/").rstrip("/") or "/"
    for root in roots:
        if normalized == root or normalized.startswith(f"{root}/"):
            return True
    return False


def _epic_logged_in() -> bool:
    return bool(session.get("user") or session.get("epic_id"))


def _admin_logged_in() -> bool:
    return bool(session.get("admin_authed") or session.get("staff_role"))


def _has_portal_access() -> bool:
    return _epic_logged_in() or _admin_logged_in()


def _is_public_path(path: str) -> bool:
    normalized = (path or "/").rstrip("/") or "/"
    if normalized in PUBLIC_PATHS:
        return True
    if request.method == "GET" and normalized in PUBLIC_GET_ONLY_PATHS:
        return True
    return any(normalized.startswith(prefix) for prefix in PUBLIC_PREFIXES)

try:
    from oracle_db import init_schema, ensure_channel_schema, ensure_ops_schema, get_site_broadcasts
except ImportError:
    init_schema = None
    ensure_channel_schema = None
    ensure_ops_schema = None
    get_site_broadcasts = None

if init_schema is not None:
    try:
        init_schema()
        if ensure_channel_schema is not None:
            ensure_channel_schema()
        if ensure_ops_schema is not None:
            ensure_ops_schema()
    except Exception as exc:
        print(f"[server] schema init skipped: {exc}")


@app.context_processor
def inject_portal_nav():
    epic_logged_in = _epic_logged_in()
    admin_authed = _admin_logged_in()
    member_access = epic_logged_in or admin_authed
    broadcasts = []
    if get_site_broadcasts is not None:
        try:
            broadcasts = get_site_broadcasts(active_only=True, limit=12) or []
        except Exception:
            broadcasts = []
    if epic_logged_in:
        exit_href = "/dashboard"
        exit_label = "Dashboard"
    elif admin_authed:
        exit_href = "/ops"
        exit_label = "Ops"
    else:
        exit_href = "/home"
        exit_label = "Home"
    return {
        "portal_logged_in": member_access,
        "portal_epic_logged_in": epic_logged_in,
        "portal_admin_authed": admin_authed,
        "portal_member_access": member_access,
        "portal_exit_href": exit_href,
        "portal_exit_label": exit_label,
        "site_broadcasts": broadcasts,
    }


@app.before_request
def enforce_member_gate():
    path = request.path or "/"
    if request.method == "OPTIONS" or _is_public_path(path):
        return None
    if not _has_portal_access() and (
        _path_matches(path, PROTECTED_PAGE_ROOTS)
        or _path_matches(path, PROTECTED_API_ROOTS)
    ):
        if path.startswith("/api/"):
            return jsonify({"ok": False, "error": "login_required", "login_url": "/auth/epic"}), 401
        return redirect("/home")
    return None

# Import all blueprints
from routes.platform import platform_bp
from routes.channels import channels_bp
from routes.auth import auth_bp
from routes.api import api_bp
from routes.whitepages import whitepages_bp
from routes.forge import forge_bp
from routes.forge_routes import forge_downloads_bp
from routes.leaderboard import leaderboard_bp
from routes.forge_upgrades import forge_upgrades_bp
from routes.news import news_bp
from routes.epic_games_api import epic_api_bp
from routes.room import room_bp

# Register blueprints
app.register_blueprint(platform_bp)
app.register_blueprint(channels_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(whitepages_bp)
app.register_blueprint(forge_bp)
app.register_blueprint(forge_downloads_bp)
app.register_blueprint(leaderboard_bp)
app.register_blueprint(forge_upgrades_bp)
app.register_blueprint(news_bp)
app.register_blueprint(epic_api_bp)
app.register_blueprint(room_bp)


@app.route("/favicon.svg")
@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.svg", mimetype="image/svg+xml")


@app.route("/manifest.json")
def manifest():
    return jsonify(
        {
            "name": "TriptokForge",
            "short_name": "TriptokForge",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#07090d",
            "theme_color": "#00e5a0",
            "icons": [
                {"src": "/static/favicon.svg", "sizes": "any", "type": "image/svg+xml"},
                {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        }
    )


@app.route("/news")
def news_page():
    return render_template("news.html")


@app.route("/cardgame")
def cardgame():
    return render_template("cardgame.html")


@app.route("/sitemap.xml")
def sitemap():
    base = "https://triptokforge.org"
    pages = ["", "/home", "/forge", "/gallery", "/feed", "/channels", "/arena", "/esports", "/community", "/whitepages", "/cardgame"]
    urls = "\n".join(f"  <url><loc>{base}{page}</loc></url>" for page in pages)
    return (
        f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>""",
        200,
        {"Content-Type": "application/xml"},
    )


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
