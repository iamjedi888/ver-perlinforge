"""
routes/whitepages.py — Developer documentation hub
  /whitepages              Main docs index
  /whitepages/verse        Verse / UEFN reference
  /whitepages/api          API route reference
  /whitepages/deploy       Deploy & ops guide
  /whitepages/tarkov       Tarkov-Lite game systems

  To add a new article:
    1. Create templates/whitepages/<slug>.html
    2. Add a route below following the existing pattern
    3. Add the sidebar link in templates/whitepages/_sidebar.html
"""

from flask import Blueprint, render_template, send_file
import os

whitepages_bp = Blueprint("whitepages", __name__, url_prefix="/whitepages")

# Shared context injected into every whitepages page
def _ctx(**kwargs):
    return {
        "platform_version": "0.4.1",
        "stack": "Flask · Oracle · OCI",
        "engine": "UEFN + Verse",
        "epic_status": "OAuth Pending",
        **kwargs
    }


@whitepages_bp.route("/")
@whitepages_bp.route("")
def index():
    """Main docs landing — overview + table of contents."""
    return render_template("whitepages/index.html", **_ctx(
        active_page="index",
        title="Whitepages — TriptokForge Developer Docs",
    ))


@whitepages_bp.route("/verse")
def verse():
    """Verse architecture, file reference, patterns & recipes."""
    return render_template("whitepages/verse.html", **_ctx(
        active_page="verse",
        title="Verse Reference — TriptokForge Whitepages",
    ))


@whitepages_bp.route("/api")
def api_docs():
    """Platform API routes, request/response formats, auth."""
    return render_template("whitepages/api.html", **_ctx(
        active_page="api",
        title="API Reference — TriptokForge Whitepages",
    ))


@whitepages_bp.route("/deploy")
def deploy():
    """Deploy guide — Oracle VM, systemd, git flow, env vars."""
    return render_template("whitepages/deploy.html", **_ctx(
        active_page="deploy",
        title="Deploy Guide — TriptokForge Whitepages",
    ))


@whitepages_bp.route("/tarkov")
def tarkov():
    """Tarkov-Lite game systems — vision, zones, economy."""
    return render_template("whitepages/tarkov.html", **_ctx(
        active_page="tarkov",
        title="Tarkov-Lite — TriptokForge Whitepages",
    ))


# ── FUTURE ARTICLES (uncomment as you build them) ───────────────
# @whitepages_bp.route("/island-forge")
# def island_forge():
#     return render_template("whitepages/island_forge.html", **_ctx(active_page="island-forge"))
#
# @whitepages_bp.route("/channels")
# def channels_docs():
#     return render_template("whitepages/channels.html", **_ctx(active_page="channels"))
#
# @whitepages_bp.route("/epic-oauth")
# def epic_oauth():
#     return render_template("whitepages/epic_oauth.html", **_ctx(active_page="epic-oauth"))
