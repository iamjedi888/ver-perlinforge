"""
routes/forge_upgrades.py — Forge Phase 5 upgrades
  /api/presets          GET  — list public presets
  /api/presets/save     POST — save a preset
  /api/presets/load/<id> GET — load one preset
  /api/presets/delete/<id> DELETE — delete own preset
  /api/save_island      POST — save island to gallery/room
"""
import os
from flask import Blueprint, session, jsonify, request

forge_upgrades_bp = Blueprint("forge_upgrades", __name__)

try:
    from oracle_db import (
        get_presets, save_preset, delete_preset, get_preset_by_id,
        save_island_to_gallery, db_available,
    )
    HAS_DB = True
except ImportError:
    HAS_DB = False
    def get_presets(): return []
    def save_preset(*a, **k): return None
    def delete_preset(*a): return False
    def get_preset_by_id(id): return None
    def save_island_to_gallery(*a, **k): return None

# ── PRESETS ───────────────────────────────────────────────

@forge_upgrades_bp.route("/api/presets")
def api_get_presets():
    try:
        presets = get_presets()
        return jsonify({"ok": True, "presets": presets})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "presets": []})

@forge_upgrades_bp.route("/api/presets/save", methods=["POST"])
def api_save_preset():
    user = session.get("user")
    data = request.get_json(force=True)
    name = data.get("name", "").strip()[:64]
    if not name:
        return jsonify({"ok": False, "error": "Name required"})
    config = {
        "seed":         data.get("seed"),
        "size":         data.get("size"),
        "plots":        data.get("plots"),
        "spacing":      data.get("spacing"),
        "world_size":   data.get("world_size"),
        "world_size_cm":data.get("world_size_cm"),
        "weights":      data.get("weights", {}),
        "biome_overrides": data.get("biome_overrides", {}),
    }
    epic_id      = user.get("account_id", "anonymous") if user else "anonymous"
    display_name = user.get("display_name", "Anonymous") if user else "Anonymous"
    is_public    = bool(data.get("is_public", True))
    try:
        pid = save_preset(
            epic_id=epic_id,
            display_name=display_name,
            name=name,
            config=config,
            is_public=is_public,
        )
        return jsonify({"ok": True, "id": pid, "name": name})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@forge_upgrades_bp.route("/api/presets/load/<int:preset_id>")
def api_load_preset(preset_id):
    try:
        p = get_preset_by_id(preset_id)
        if not p:
            return jsonify({"ok": False, "error": "Not found"})
        return jsonify({"ok": True, "preset": p})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@forge_upgrades_bp.route("/api/presets/delete/<int:preset_id>", methods=["DELETE","POST"])
def api_delete_preset(preset_id):
    user = session.get("user")
    if not user:
        return jsonify({"ok": False, "error": "Not logged in"})
    epic_id = user.get("account_id", "")
    try:
        ok = delete_preset(preset_id, epic_id)
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

# ── GALLERY SAVE ──────────────────────────────────────────

@forge_upgrades_bp.route("/api/save_island", methods=["POST"])
def api_save_island():
    user   = session.get("user")
    data   = request.get_json(force=True)
    epic_id      = user.get("account_id", "") if user else ""
    display_name = user.get("display_name", "Anonymous") if user else "Anonymous"
    name         = data.get("name", "Unnamed Island")[:128]
    seed         = data.get("seed")
    dominant_biome = data.get("dominant_biome", "")
    preview_b64  = data.get("preview_b64", "")
    config       = data.get("config", {})
    verse_data   = data.get("verse_data", {})
    stickers     = data.get("stickers", [])
    is_public    = bool(data.get("is_public", True))
    try:
        iid = save_island_to_gallery(
            epic_id=epic_id,
            display_name=display_name,
            name=name,
            seed=seed,
            dominant_biome=dominant_biome,
            preview_b64=preview_b64,
            config=config,
            verse_data=verse_data,
            stickers=stickers,
            is_public=is_public,
        )
        return jsonify({"ok": True, "id": iid, "name": name})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
