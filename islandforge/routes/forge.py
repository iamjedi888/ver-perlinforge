"""
routes/forge.py — Island Forge + Audio + Fortnite API endpoints
Restored from server_old.py.
"""
import io, base64, json, os, re, sys, traceback, secrets
from datetime import datetime
import urllib.parse, urllib.request
import numpy as np

from flask import Blueprint, request, jsonify, send_file, session, redirect, render_template

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
        classify_biomes, classify_biomes_themed, find_plot_positions, build_layout,
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

try:
    from compression_utils import create_verse_package_zip
except ImportError:
    def create_verse_package_zip(*a, **k):
        return b""

try:
    from verse_export_generator import integrate_with_forge
    VERSE_EXPORT_AVAILABLE = True
except ImportError:
    VERSE_EXPORT_AVAILABLE = False

    def integrate_with_forge(result_data, theme="Chapter 1", seed=0):
        return result_data

_state = {
    "heightmap_bytes": None, "layout": None, "preview_bytes": None,
    "audio_path": None, "audio_filename": None, "audio_weights": None,
    "output_dir": None, "output_folder_name": None, "download_prefix": "Island",
    "verse_package": None, "verse_zip_bytes": None,
}
DEFAULT_WEIGHTS = {
    "sub_bass":0.5,"bass":0.5,"midrange":0.5,
    "presence":0.5,"brilliance":0.5,"tempo_bpm":120.0,"duration_s":0.0,
}
_cosmetics_cache = None
THEME_ALIASES = {
    "chapter1": "Chapter 1",
    "chapter2": "Chapter 2",
    "chapter3": "Chapter 3",
    "chapter4": "Chapter 4",
    "chapter5": "Chapter 5",
    "chapter6": "Chapter 6",
}


def _sanitize_world_name(value: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*#]+', " ", str(value or "")).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean[:64] or "Island"


def _allocate_output_run(world_name: str) -> tuple[str, str, str]:
    base_name = _sanitize_world_name(world_name)
    pattern = re.compile(rf"^{re.escape(base_name)}#(\d+)$", re.IGNORECASE)
    next_index = 1

    for entry in os.listdir(OUTPUT_DIR):
        full_path = os.path.join(OUTPUT_DIR, entry)
        if not os.path.isdir(full_path):
            continue
        match = pattern.match(entry)
        if match:
            next_index = max(next_index, int(match.group(1)) + 1)

    while True:
        folder_name = f"{base_name}#{next_index}"
        run_dir = os.path.join(OUTPUT_DIR, folder_name)
        if not os.path.exists(run_dir):
            os.makedirs(run_dir, exist_ok=False)
            return base_name, folder_name, run_dir
        next_index += 1


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _write_text(path: str, payload: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _download_name(suffix: str) -> str:
    prefix = (_state.get("download_prefix") or "Island").strip() or "Island"
    return f"{prefix}_{suffix}"


def _session_output_path(filename: str) -> str | None:
    folder_name = os.path.basename(str(session.get("forge_output_folder") or "").strip())
    if not folder_name:
        return None
    path = os.path.join(OUTPUT_DIR, folder_name, filename)
    return path if os.path.exists(path) else None


def _session_download_name(suffix: str) -> str:
    prefix = str(session.get("forge_download_prefix") or "").strip()
    if not prefix:
        return _download_name(suffix)
    return f"{prefix}_{suffix}"


def _normalize_theme_name(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "Chapter 1"
    compact = re.sub(r"[\s_-]+", "", text).lower()
    if compact in THEME_ALIASES:
        return THEME_ALIASES[compact]
    for label in THEME_ALIASES.values():
        if text.lower() == label.lower():
            return label
    return "Chapter 1"


def _theme_lookup_key(value: str) -> str:
    compact = re.sub(r"[^0-9a-z]+", "", str(value or "").lower())
    return compact or "chapter1"

# ── FORGE PAGE ───────────────────────────────────────────────
@forge_bp.route("/forge")
def forge():
    return render_template("forge.html")

# ── GENERATE ─────────────────────────────────────────────────
@forge_bp.route("/generate", methods=["POST"])
def generate():
    if not AUDIO_AVAILABLE:
        return jsonify({"ok": False, "error": "audio_to_heightmap not available"}), 500
    try:
        data           = request.get_json(force=True)
        island_name    = (data.get("island_name") or data.get("world_name") or "").strip()
        seed           = int(data.get("seed", 42))
        size           = int(data.get("size", 2017))
        n_plots        = int(data.get("plots", 32))
        spacing        = int(data.get("spacing", 40))
        incoming_weights = data.get("weights") or {}
        weights        = DEFAULT_WEIGHTS.copy()
        if isinstance(_state.get("audio_weights"), dict):
            weights.update(_state["audio_weights"])
        if isinstance(incoming_weights, dict):
            weights.update(incoming_weights)
        water_level    = float(data.get("water_level", 0.20))
        world_wrap     = bool(data.get("world_wrap", True))
        cluster_angle  = float(data.get("cluster_angle", 135.0))
        cluster_spread = float(data.get("cluster_spread", 1.0))
        theme_name     = _normalize_theme_name(data.get("theme"))
        theme_key      = _theme_lookup_key(theme_name)
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
        themed_colours = BIOME_COLOURS
        try:
            biome, themed_colours, _ = classify_biomes_themed(
                height,
                moisture,
                water_level=water_level,
                theme_name=theme_key,
            )
        except Exception:
            biome = classify_biomes(height, moisture, water_level)
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
        layout["meta"]["theme"] = theme_name
        layout["meta"]["theme_key"] = theme_key
        layout["meta"]["uefn_asset_binding"] = "Bind generated Verse slot names to builtin Fortnite assets in UEFN editor"
        run_name, output_folder_name, output_run_dir = _allocate_output_run(island_name)
        layout["meta"]["island_name"] = run_name
        layout["meta"]["output_folder_name"] = output_folder_name
        layout["meta"]["generated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        if town_data:
            layout["town_data"] = town_data
            layout["town_center"] = {"pixel": town_data["center_pixel"], "world_x_cm": town_data["center_world_x"], "world_z_cm": town_data["center_world_z"]}

        verse_package = {}
        if VERSE_EXPORT_AVAILABLE:
            verse_result = integrate_with_forge(
                {
                    "heightmap_normalized": height.tolist(),
                    "biome_map": biome.tolist(),
                    "plots_found": layout.get("plots", []),
                    "town_center": layout.get("town_center"),
                    "world_size_cm": world_size_cm,
                },
                theme=theme_name,
                seed=seed,
            )
            verse_package = verse_result.get("verse_package") or {}

        from PIL import Image
        hm_16 = (height * 65535).astype(np.uint16)
        hm_img = Image.fromarray(hm_16)
        heightmap_path = os.path.join(output_run_dir, "heightmap.png")
        hm_img.save(heightmap_path)
        hm_buf = io.BytesIO(); hm_img.save(hm_buf, format="PNG")
        _state["heightmap_bytes"] = hm_buf.getvalue()
        _write_json(os.path.join(output_run_dir, "layout.json"), layout)
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
        prev_rgb = build_preview(h_dn, b_dn, p_dn, prev_size, rm_dn, biome_colours=themed_colours)
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
        preview_path = os.path.join(output_run_dir, "preview.png")
        prev_img.save(preview_path)
        prev_buf = io.BytesIO(); prev_img.save(prev_buf, format="PNG")
        _state["preview_bytes"] = prev_buf.getvalue()
        prev_b64 = base64.b64encode(_state["preview_bytes"]).decode("utf-8")
        total = size * size
        biome_stats = [{"name": BIOME_NAMES.get(b, "?"), "pct": round(float(np.sum(biome == b)) / total * 100, 1), "colour": "rgb({},{},{})".format(*BIOME_COLOURS.get(b, (100,100,100)))} for b in sorted(BIOME_NAMES.keys()) if np.any(biome == b)]

        if verse_package:
            for filename, content in verse_package.items():
                _write_text(os.path.join(output_run_dir, filename), content)
            verse_zip_bytes = create_verse_package_zip(verse_package, seed)
            if verse_zip_bytes:
                with open(os.path.join(output_run_dir, "verse_package.zip"), "wb") as handle:
                    handle.write(verse_zip_bytes)
                _state["verse_zip_bytes"] = verse_zip_bytes
            else:
                _state["verse_zip_bytes"] = None
        else:
            _state["verse_zip_bytes"] = None

        manifest = {
            "island_name": run_name,
            "output_folder_name": output_folder_name,
            "seed": seed,
            "theme": theme_name,
            "world_size_cm": world_size_cm,
            "world_wrap": world_wrap,
            "water_level": water_level,
            "cluster_angle": cluster_angle,
            "cluster_spread": cluster_spread,
            "plots_found": len(plots),
            "audio_filename": _state.get("audio_filename"),
            "audio_weights": weights,
            "files": {
                "heightmap": "heightmap.png",
                "layout": "layout.json",
                "preview": "preview.png",
                "placement_plan": "placement_plan.json" if "placement_plan.json" in verse_package else "",
                "verse_zip": "verse_package.zip" if _state.get("verse_zip_bytes") else "",
                "verse_files": sorted(list(verse_package.keys())),
            },
            "meta": layout["meta"],
        }
        _write_json(os.path.join(output_run_dir, "manifest.json"), manifest)

        _state["output_dir"] = output_run_dir
        _state["output_folder_name"] = output_folder_name
        _state["download_prefix"] = output_folder_name
        _state["verse_package"] = verse_package or None
        session["forge_output_folder"] = output_folder_name
        session["forge_download_prefix"] = output_folder_name

        return jsonify({
            "ok": True,
            "preview_b64": prev_b64,
            "plots_found": len(plots),
            "biome_stats": biome_stats,
            "verse_constants": layout["verse_constants"],
            "verse_file_count": len(verse_package),
            "town_center": layout.get("town_center"),
            "meta": layout["meta"],
            "world_wrap": world_wrap,
            "water_level": water_level,
            "world_size_cm": world_size_cm,
            "saved_to": output_run_dir,
            "output_folder_name": output_folder_name,
            "island_name": run_name,
            "manifest": manifest,
        })
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
    if _state["heightmap_bytes"]:
        return send_file(io.BytesIO(_state["heightmap_bytes"]), mimetype="image/png", as_attachment=True, download_name=_download_name("heightmap.png"))
    path = _session_output_path("heightmap.png")
    if not path:
        return "No heightmap yet", 404
    return send_file(path, mimetype="image/png", as_attachment=True, download_name=_session_download_name("heightmap.png"))

@forge_bp.route("/download/layout")
def download_layout():
    if _state["layout"]:
        return send_file(io.BytesIO(json.dumps(_state["layout"],indent=2).encode()), mimetype="application/json", as_attachment=True, download_name=_download_name("layout.json"))
    path = _session_output_path("layout.json")
    if not path:
        return "No layout yet", 404
    return send_file(path, mimetype="application/json", as_attachment=True, download_name=_session_download_name("layout.json"))

@forge_bp.route("/download/preview")
def download_preview():
    if _state["preview_bytes"]:
        return send_file(io.BytesIO(_state["preview_bytes"]), mimetype="image/png", as_attachment=True, download_name=_download_name("preview.png"))
    path = _session_output_path("preview.png")
    if not path:
        return "No preview yet", 404
    return send_file(path, mimetype="image/png", as_attachment=True, download_name=_session_download_name("preview.png"))

@forge_bp.route("/download/verse_package")
def download_verse_package():
    if _state["verse_zip_bytes"]:
        return send_file(io.BytesIO(_state["verse_zip_bytes"]), mimetype="application/zip", as_attachment=True, download_name=_download_name("verse_package.zip"))
    path = _session_output_path("verse_package.zip")
    if not path:
        return "No verse package yet", 404
    return send_file(path, mimetype="application/zip", as_attachment=True, download_name=_session_download_name("verse_package.zip"))

@forge_bp.route("/random_seed")
def random_seed():
    import random; return jsonify({"seed": random.randint(1, 99999)})

# ── FORTNITE API ─────────────────────────────────────────────
@forge_bp.route("/api/stats")
def api_stats():
    name = (request.args.get("name", "") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "No name"})
    try:
        from routes.epic_games_api import _live_stats_for_name, _mock_stats

        stats_key_ready = bool(os.environ.get("FORTNITE_API_KEY", "").strip())
        live_stats = _live_stats_for_name(name)
        if live_stats:
            return jsonify(
                {
                    "ok": True,
                    "player": {"name": name},
                    "stats": live_stats,
                    "source": "fortnite-api",
                }
            )

        if stats_key_ready:
            return jsonify(
                {
                    "ok": False,
                    "error": "Player not found or live stats are unavailable.",
                }
            )

        return jsonify(
            {
                "ok": True,
                "player": {"name": name},
                "stats": _mock_stats(name),
                "source": "mock",
            }
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

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
