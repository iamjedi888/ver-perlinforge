"""
routes/forge.py — Island Forge + Audio + Fortnite API endpoints
Restored from server_old.py.
"""
import io, base64, json, os, sys, traceback, secrets
import urllib.parse, urllib.request

import numpy as np
from flask import Blueprint, request, jsonify, send_file, session, redirect

forge_bp = Blueprint("forge", __name__)

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR  = os.path.join(BASE_DIR, "saved_audio")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPPORTED_EXTS = (".wav",".mp3",".flac",".ogg",".aac",".m4a",".aiff",".opus")
FORTNITE_STATS_URL = "https://fortnite-api.com/v2/stats/br/v2"
FORTNITE_COSMETICS = "https://fortnite-api.com/v2/cosmetics/br"

try:
    from audio_to_heightmap import (
        analyse_audio, generate_terrain, generate_moisture,
        classify_biomes, find_plot_positions, build_layout,
        build_preview, paint_farm_biome, get_farm_cluster_info,
        BIOME_NAMES, BIOME_COLOURS,
        WORLD_SIZE_PRESETS, DEFAULT_WORLD_SIZE_CM,
    )
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

try:
    from town_generator import generate_town, BIOME_TOWN
    TOWN_GEN_AVAILABLE = True
except ImportError:
    TOWN_GEN_AVAILABLE = False

try:
    from oracle_db import update_member_skin
except ImportError:
    def update_member_skin(*a, **k): pass

_state = {
    "heightmap_bytes": None, "layout": None, "preview_bytes": None,
    "audio_path": None, "audio_filename": None, "audio_weights": None,
}
DEFAULT_WEIGHTS = {
    "sub_bass":0.5,"bass":0.5,"midrange":0.5,
    "presence":0.5,"brilliance":0.5,"tempo_bpm":120.0,"duration_s":0.0,
}
_cosmetics_cache = None

# ── FORGE PAGE ───────────────────────────────────────────────
@forge_bp.route("/forge")
def forge():
    path = os.path.join(BASE_DIR, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html"}

# ── GENERATE ─────────────────────────────────────────────────
@forge_bp.route("/generate", methods=["POST"])
def generate():
    if not AUDIO_AVAILABLE:
        return jsonify({"ok": False, "error": "audio_to_heightmap not available"}), 500
    try:
        data           = request.get_json(force=True)
        seed           = int(data.get("seed", 42))
        size           = int(data.get("size", 2017))
        n_plots        = int(data.get("plots", 32))
        spacing        = int(data.get("spacing", 40))
        weights        = data.get("weights", DEFAULT_WEIGHTS)
        water_level    = float(data.get("water_level", 0.20))
        world_wrap     = bool(data.get("world_wrap", True))
        cluster_angle  = float(data.get("cluster_angle", 135.0))
        cluster_spread = float(data.get("cluster_spread", 1.0))
        ws_raw = data.get("world_size", "double_br")
        if isinstance(ws_raw, str) and ws_raw in WORLD_SIZE_PRESETS:
            world_size_cm = WORLD_SIZE_PRESETS[ws_raw]
        else:
            world_size_cm = int(data.get("world_size_cm", DEFAULT_WORLD_SIZE_CM))
        water_level    = max(0.0, min(0.48, water_level))
        cluster_spread = max(0.5, min(2.0, cluster_spread))
        if size not in (505, 1009, 2017, 4033): size = 1009
        for k, v in DEFAULT_WEIGHTS.items(): weights.setdefault(k, v)
        height, road_mask = generate_terrain(size, seed, weights, water_level)
        moisture = generate_moisture(size, seed)
        biome    = classify_biomes(height, moisture, water_level)
        town_data = street_mask = town_mask = farm_mask = None
        if TOWN_GEN_AVAILABLE:
            from audio_to_heightmap import build_island_mask
            island_mask = build_island_mask(size, seed, weights.get("presence", 0.5), weights.get("tempo_bpm", 120.0))
            if BIOME_TOWN not in BIOME_NAMES:
                BIOME_NAMES[BIOME_TOWN] = "Town"; BIOME_COLOURS[BIOME_TOWN] = (158, 148, 132)
            height, biome, plots, town_data, street_mask, town_mask, farm_mask = generate_town(
                height, biome, island_mask, size, seed, weights,
                n_plots=n_plots, cluster_angle_deg=cluster_angle, cluster_spread=cluster_spread * 0.22)
        else:
            plots = find_plot_positions(height, biome, n_plots, size, min_spacing=spacing, cluster_angle_deg=cluster_angle, cluster_spread=cluster_spread)
            biome = paint_farm_biome(biome, plots, size)
        layout = build_layout(height, biome, plots, size, seed, weights, water_level, world_wrap, world_size_cm)
        if town_data:
            layout["town_data"] = town_data
            layout["town_center"] = {"pixel": town_data["center_pixel"], "world_x_cm": town_data["center_world_x"], "world_z_cm": town_data["center_world_z"]}
        from PIL import Image
        hm_16 = (height * 65535).astype(np.uint16)
        hm_img = Image.fromarray(hm_16)
        hm_img.save(os.path.join(OUTPUT_DIR, f"island_{seed}_heightmap.png"))
        hm_buf = io.BytesIO(); hm_img.save(hm_buf, format="PNG")
        _state["heightmap_bytes"] = hm_buf.getvalue()
        with open(os.path.join(OUTPUT_DIR, f"island_{seed}_layout.json"), "w") as jf:
            json.dump(layout, jf, indent=2)
        _state["layout"] = layout
        prev_size = min(size, 1009)
        if prev_size < size:
            factor = size // prev_size
            h_dn = height[::factor, ::factor][:prev_size, :prev_size]
            b_dn = biome[::factor, ::factor][:prev_size, :prev_size]
            rm_dn = road_mask[::factor, ::factor][:prev_size, :prev_size] if road_mask is not None else None
            p_dn = [(r // factor, c // factor) for r, c in plots]
        else:
            h_dn, b_dn, p_dn, rm_dn = height, biome, plots, road_mask
        prev_rgb = build_preview(h_dn, b_dn, p_dn, prev_size, rm_dn)
        if TOWN_GEN_AVAILABLE and town_data and street_mask is not None:
            from town_generator import build_street_grid, classify_blocks, place_lots_in_block, render_town_overlay
            tc = town_data["center_pixel"]; scale = prev_size / size
            tc_s = (int(tc[0]*scale), int(tc[1]*scale)); f = max(1, size // prev_size)
            s_dn = street_mask[::f, ::f][:prev_size, :prev_size]
            tm_dn = town_mask[::f, ::f][:prev_size, :prev_size]
            fm_dn = farm_mask[::f, ::f][:prev_size, :prev_size]
            st, bl = build_street_grid(tc_s[0], tc_s[1], prev_size)
            bl = classify_blocks(bl, tc_s[0], tc_s[1])
            lots = []
            for b in bl: lots.extend(place_lots_in_block(b, prev_size, b.get("type", "residential")))
            p_s = [(int(r*scale), int(c*scale)) for r, c in plots]
            prev_rgb = render_town_overlay(prev_rgb, s_dn, tm_dn, fm_dn, p_s, bl, lots, prev_size)
        prev_img = Image.fromarray(prev_rgb, mode="RGB")
        prev_img.save(os.path.join(OUTPUT_DIR, f"island_{seed}_preview.png"))
        prev_buf = io.BytesIO(); prev_img.save(prev_buf, format="PNG")
        _state["preview_bytes"] = prev_buf.getvalue()
        prev_b64 = base64.b64encode(_state["preview_bytes"]).decode("utf-8")
        total = size * size
        biome_stats = [{"name": BIOME_NAMES.get(b, "?"), "pct": round(float(np.sum(biome == b)) / total * 100, 1), "colour": "rgb({},{},{})".format(*BIOME_COLOURS.get(b, (100,100,100)))} for b in sorted(BIOME_NAMES.keys()) if np.any(biome == b)]
        return jsonify({"ok": True, "preview_b64": prev_b64, "plots_found": len(plots), "biome_stats": biome_stats, "verse_constants": layout["verse_constants"], "town_center": layout.get("town_center"), "meta": layout["meta"], "world_wrap": world_wrap, "water_level": water_level, "world_size_cm": world_size_cm, "saved_to": OUTPUT_DIR})
    except Exception as e:
        traceback.print_exc(); return jsonify({"ok": False, "error": str(e)}), 500

# ── AUDIO ────────────────────────────────────────────────────
@forge_bp.route("/upload_audio", methods=["POST"])
def upload_audio():
    try:
        if "file" not in request.files: return jsonify({"ok":False,"error":"No file"}),400
        f = request.files["file"]; ext = os.path.splitext(f.filename)[1].lower()
        if ext not in SUPPORTED_EXTS: return jsonify({"ok":False,"error":f"Unsupported: {', '.join(SUPPORTED_EXTS)}"}),400
        safe = os.path.basename(f.filename); save_path = os.path.join(AUDIO_DIR, safe)
        stem, sfx = os.path.splitext(safe); c = 1
        while os.path.exists(save_path): save_path = os.path.join(AUDIO_DIR, f"{stem}_{c}{sfx}"); c += 1
        f.save(save_path)
        if AUDIO_AVAILABLE:
            weights = analyse_audio(save_path)
        else:
            weights = DEFAULT_WEIGHTS.copy()
        _state["audio_path"] = save_path; _state["audio_filename"] = os.path.basename(save_path); _state["audio_weights"] = weights
        return jsonify({"ok":True,"filename":os.path.basename(save_path),"weights":weights})
    except Exception as e:
        traceback.print_exc(); return jsonify({"ok":False,"error":str(e)}),500

@forge_bp.route("/audio/list")
def audio_list():
    try:
        files = [{"filename":fn,"size_kb":round(os.path.getsize(os.path.join(AUDIO_DIR,fn))/1024,1),"active":_state["audio_filename"]==fn} for fn in sorted(os.listdir(AUDIO_DIR)) if os.path.splitext(fn)[1].lower() in SUPPORTED_EXTS]
        return jsonify({"ok":True,"files":files})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@forge_bp.route("/audio/select", methods=["POST"])
def audio_select():
    try:
        data = request.get_json(force=True); path = os.path.join(AUDIO_DIR, os.path.basename(data.get("filename","")))
        if not os.path.exists(path): return jsonify({"ok":False,"error":"Not found"}),404
        weights = analyse_audio(path) if AUDIO_AVAILABLE else DEFAULT_WEIGHTS.copy()
        _state["audio_path"] = path; _state["audio_filename"] = os.path.basename(path); _state["audio_weights"] = weights
        return jsonify({"ok":True,"filename":os.path.basename(path),"weights":weights})
    except Exception as e: traceback.print_exc(); return jsonify({"ok":False,"error":str(e)}),500

@forge_bp.route("/audio/<filename>", methods=["DELETE"])
def audio_delete(filename):
    try:
        path = os.path.join(AUDIO_DIR, os.path.basename(filename))
        if not os.path.exists(path): return jsonify({"ok":False,"error":"Not found"}),404
        os.remove(path)
        if _state["audio_filename"] == filename: _state["audio_path"] = _state["audio_filename"] = _state["audio_weights"] = None
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@forge_bp.route("/audio/stream/<filename>")
def audio_stream(filename):
    path = os.path.join(AUDIO_DIR, os.path.basename(filename))
    if not os.path.exists(path): return "Not found", 404
    ext = os.path.splitext(filename)[1].lower()
    mime = {".mp3":"audio/mpeg",".wav":"audio/wav",".ogg":"audio/ogg",".flac":"audio/flac",".aac":"audio/aac",".m4a":"audio/mp4",".aiff":"audio/aiff",".opus":"audio/opus"}.get(ext,"audio/mpeg")
    return send_file(path, mimetype=mime, conditional=True)

# ── DOWNLOADS ────────────────────────────────────────────────
@forge_bp.route("/download/heightmap")
def download_heightmap():
    if not _state["heightmap_bytes"]: return "No heightmap yet", 404
    return send_file(io.BytesIO(_state["heightmap_bytes"]), mimetype="image/png", as_attachment=True, download_name="island_heightmap.png")

@forge_bp.route("/download/layout")
def download_layout():
    if not _state["layout"]: return "No layout yet", 404
    return send_file(io.BytesIO(json.dumps(_state["layout"],indent=2).encode()), mimetype="application/json", as_attachment=True, download_name="island_layout.json")

@forge_bp.route("/download/preview")
def download_preview():
    if not _state["preview_bytes"]: return "No preview yet", 404
    return send_file(io.BytesIO(_state["preview_bytes"]), mimetype="image/png", as_attachment=True, download_name="island_preview.png")

@forge_bp.route("/random_seed")
def random_seed():
    import random; return jsonify({"seed": random.randint(1, 99999)})

# ── FORTNITE API ─────────────────────────────────────────────
@forge_bp.route("/api/stats")
def api_stats():
    name = request.args.get("name","")
    if not name: return jsonify({"ok":False,"error":"No name"})
    try:
        url = f"{FORTNITE_STATS_URL}?name={urllib.parse.quote(name)}"
        req = urllib.request.Request(url, headers={"User-Agent":"TriptokForge/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r: data = json.loads(r.read().decode())
        if data.get("status") != 200: return jsonify({"ok":False,"error":"Player not found"})
        ov = data.get("data",{}).get("stats",{}).get("all",{}).get("overall",{})
        wins=ov.get("wins",0); kills=ov.get("kills",0); matches=ov.get("matches",0)
        kd=ov.get("kd",0.0); score=ov.get("scorePerMatch",0)
        win_pct = f"{round(wins/matches*100,1)}%" if matches else "0%"
        return jsonify({"ok":True,"stats":{"wins":wins,"kills":kills,"matches":matches,"kd":round(kd,2),"winPct":win_pct,"score":round(score,1)}})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@forge_bp.route("/api/cosmetics")
def api_cosmetics():
    global _cosmetics_cache
    if _cosmetics_cache: return jsonify({"ok":True,"skins":_cosmetics_cache})
    try:
        req = urllib.request.Request(FORTNITE_COSMETICS, headers={"User-Agent":"TriptokForge/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r: data = json.loads(r.read().decode())
        skins = []
        for item in data.get("data",[]):
            if item.get("type",{}).get("value") != "outfit": continue
            imgs = item.get("images",{}); img = imgs.get("smallIcon") or imgs.get("icon") or ""
            if not img: continue
            skins.append({"id":item.get("id",""),"name":item.get("name",""),"img":img})
        _cosmetics_cache = skins
        return jsonify({"ok":True,"skins":skins})
    except Exception as e: return jsonify({"ok":False,"error":str(e)})

@forge_bp.route("/api/set_skin", methods=["POST"])
def api_set_skin():
    data = request.get_json(force=True)
    if "user" in session:
        session["user"]["skin"] = data.get("id")
        session["user"]["skin_name"] = data.get("name","")
        session["user"]["skin_img"] = data.get("img","")
        session.modified = True
        update_member_skin(
            epic_id=session["user"].get("account_id",""),
            skin_id=data.get("id",""), skin_name=data.get("name",""), skin_img=data.get("img",""))
    return jsonify({"ok":True})
