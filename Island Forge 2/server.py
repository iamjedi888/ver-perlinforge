"""
server.py
=========
Flask backend for the Island Generator web app.
Serves the UI and exposes generation endpoints.

USAGE:
    python server.py
    Open http://localhost:5000

FOLDER STRUCTURE:
    island_forge/
    ├── server.py               ← this file
    ├── index.html              ← UI
    ├── audio_to_heightmap.py   ← generator core
    ├── saved_audio/            ← uploaded audio persisted here
    └── outputs/                ← generated files saved here

ENDPOINTS:
    GET  /                      — serve index.html
    POST /generate              — generate island
    GET  /download/heightmap    — download last heightmap PNG
    GET  /download/layout       — download last layout JSON
    GET  /download/preview      — download last preview PNG
    POST /upload_audio          — upload audio, analyse, persist
    GET  /audio/list            — list saved audio files
    POST /audio/select          — re-select a saved audio file
    DELETE /audio/<filename>    — delete a saved audio file
    GET  /random_seed           — get a random seed
"""

import io
import base64
import json
import os
import sys
import traceback

import numpy as np
from flask import Flask, request, jsonify, send_file

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_to_heightmap import (
    analyse_audio,
    generate_terrain,
    generate_moisture,
    classify_biomes,
    find_plot_positions,
    build_layout,
    build_preview,
    paint_farm_biome,
    get_farm_cluster_info,
    BIOME_NAMES,
    BIOME_COLOURS,
)

app = Flask(__name__, static_folder=None)

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR  = os.path.join(BASE_DIR, "saved_audio")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(AUDIO_DIR,  exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPPORTED_EXTS = (".wav", ".mp3", ".flac", ".ogg", ".aac", ".m4a", ".aiff", ".opus")

# ─────────────────────────────────────────────────────────────
# SERVER STATE
# ─────────────────────────────────────────────────────────────

_state = {
    # Last generation outputs
    "heightmap_bytes": None,
    "layout":          None,
    "preview_bytes":   None,
    # Active audio
    "audio_path":      None,   # path to saved audio file
    "audio_filename":  None,   # display name
    "audio_weights":   None,   # last analysed weights dict
}

DEFAULT_WEIGHTS = {
    "sub_bass": 0.5, "bass": 0.5, "midrange": 0.5,
    "presence": 0.5, "brilliance": 0.5,
    "tempo_bpm": 120.0, "duration_s": 0.0,
}

# ─────────────────────────────────────────────────────────────
# SERVE UI
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    path = os.path.join(BASE_DIR, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html"}

# ─────────────────────────────────────────────────────────────
# GENERATE
# ─────────────────────────────────────────────────────────────

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data    = request.get_json(force=True)
        seed        = int(data.get("seed", 42))
        size        = int(data.get("size", 513))
        n_plots     = int(data.get("plots", 32))
        spacing     = int(data.get("spacing", 40))
        weights     = data.get("weights", DEFAULT_WEIGHTS)
        water_level     = float(data.get("water_level", 0.20))
        world_wrap      = bool(data.get("world_wrap", True))
        cluster_angle   = float(data.get("cluster_angle", 135.0))
        cluster_spread  = float(data.get("cluster_spread", 1.0))
        water_level     = max(0.0, min(0.48, water_level))
        cluster_spread  = max(0.5, min(2.0, cluster_spread))

        if size not in (513, 1009, 2017):
            size = 513

        # Ensure all weight keys present
        for k, v in DEFAULT_WEIGHTS.items():
            weights.setdefault(k, v)

        # Generate
        height   = generate_terrain(size, seed, weights, water_level)
        moisture = generate_moisture(size, seed)
        biome    = classify_biomes(height, moisture, water_level)
        plots    = find_plot_positions(height, biome, n_plots, size,
                                          spacing, cluster_angle, cluster_spread)
        # Paint farm biome zone on top of terrain biome
        biome    = paint_farm_biome(biome, plots, size)
        layout   = build_layout(height, biome, plots, size, seed, weights, water_level, world_wrap)

        # Save heightmap PNG (16-bit) to outputs/
        from PIL import Image
        hm_16  = (height * 65535).astype(np.uint16)
        hm_img = Image.fromarray(hm_16)
        hm_path = os.path.join(OUTPUT_DIR, f"island_{seed}_heightmap.png")
        hm_img.save(hm_path)
        hm_buf = io.BytesIO()
        hm_img.save(hm_buf, format="PNG")
        _state["heightmap_bytes"] = hm_buf.getvalue()

        # Save layout JSON to outputs/
        layout_path = os.path.join(OUTPUT_DIR, f"island_{seed}_layout.json")
        with open(layout_path, "w") as jf:
            json.dump(layout, jf, indent=2)
        _state["layout"] = layout

        # Preview PNG — downsampled to max 513 for web
        prev_size = min(size, 513)
        if prev_size < size:
            factor = size // prev_size
            h_dn = height[::factor, ::factor][:prev_size, :prev_size]
            b_dn = biome[::factor,  ::factor][:prev_size, :prev_size]
            p_dn = [(r // factor, c // factor) for r, c in plots]
        else:
            h_dn, b_dn, p_dn = height, biome, plots

        prev_rgb = build_preview(h_dn, b_dn, p_dn, prev_size)
        prev_img = Image.fromarray(prev_rgb, mode="RGB")
        prev_path = os.path.join(OUTPUT_DIR, f"island_{seed}_preview.png")
        prev_img.save(prev_path)
        prev_buf = io.BytesIO()
        prev_img.save(prev_buf, format="PNG")
        _state["preview_bytes"] = prev_buf.getvalue()
        prev_b64 = base64.b64encode(_state["preview_bytes"]).decode("utf-8")

        # Biome stats
        total = size * size
        biome_stats = [
            {
                "name":   BIOME_NAMES[b],
                "pct":    round(float(np.sum(biome == b)) / total * 100, 1),
                "colour": "rgb({},{},{})".format(*BIOME_COLOURS[b]),
            }
            for b in sorted(BIOME_NAMES.keys())
        ]

        return jsonify({
            "ok":             True,
            "preview_b64":    prev_b64,
            "plots_found":    len(plots),
            "biome_stats":    biome_stats,
            "verse_constants": layout["verse_constants"],
            "town_center":    layout["town_center"],
            "meta":           layout["meta"],
            "world_wrap":     world_wrap,
            "water_level":    water_level,
            "saved_to":       OUTPUT_DIR,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# AUDIO — UPLOAD & PERSIST
# ─────────────────────────────────────────────────────────────

@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    try:
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "No file in request"}), 400

        f   = request.files["file"]
        ext = os.path.splitext(f.filename)[1].lower()

        if ext not in SUPPORTED_EXTS:
            return jsonify({"ok": False,
                            "error": f"Unsupported format. Supported: {', '.join(SUPPORTED_EXTS)}"}), 400

        # Save to saved_audio/ — keep original filename, avoid collisions
        safe_name = os.path.basename(f.filename)
        save_path = os.path.join(AUDIO_DIR, safe_name)
        # If name collides, add a number suffix
        stem, sfx = os.path.splitext(safe_name)
        counter = 1
        while os.path.exists(save_path):
            save_path = os.path.join(AUDIO_DIR, f"{stem}_{counter}{sfx}")
            counter += 1

        f.save(save_path)
        print(f"[audio] Saved to {save_path}")

        # Analyse
        weights = analyse_audio(save_path)

        # Update state
        _state["audio_path"]     = save_path
        _state["audio_filename"] = os.path.basename(save_path)
        _state["audio_weights"]  = weights

        return jsonify({
            "ok":       True,
            "filename": os.path.basename(save_path),
            "weights":  weights,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# AUDIO — LIST SAVED FILES
# ─────────────────────────────────────────────────────────────

@app.route("/audio/list")
def audio_list():
    try:
        files = []
        for fn in sorted(os.listdir(AUDIO_DIR)):
            if os.path.splitext(fn)[1].lower() in SUPPORTED_EXTS:
                fp   = os.path.join(AUDIO_DIR, fn)
                size = os.path.getsize(fp)
                active = (_state["audio_filename"] == fn)
                files.append({
                    "filename": fn,
                    "size_kb":  round(size / 1024, 1),
                    "active":   active,
                })
        return jsonify({"ok": True, "files": files})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# AUDIO — SELECT A SAVED FILE
# ─────────────────────────────────────────────────────────────

@app.route("/audio/select", methods=["POST"])
def audio_select():
    try:
        data     = request.get_json(force=True)
        filename = data.get("filename", "")
        path     = os.path.join(AUDIO_DIR, os.path.basename(filename))

        if not os.path.exists(path):
            return jsonify({"ok": False, "error": "File not found"}), 404

        weights = analyse_audio(path)
        _state["audio_path"]     = path
        _state["audio_filename"] = os.path.basename(path)
        _state["audio_weights"]  = weights

        return jsonify({"ok": True, "filename": os.path.basename(path), "weights": weights})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# AUDIO — DELETE A SAVED FILE
# ─────────────────────────────────────────────────────────────

@app.route("/audio/<filename>", methods=["DELETE"])
def audio_delete(filename):
    try:
        path = os.path.join(AUDIO_DIR, os.path.basename(filename))
        if not os.path.exists(path):
            return jsonify({"ok": False, "error": "File not found"}), 404
        os.remove(path)
        if _state["audio_filename"] == filename:
            _state["audio_path"]     = None
            _state["audio_filename"] = None
            _state["audio_weights"]  = None
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# DOWNLOAD ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.route("/download/heightmap")
def download_heightmap():
    if not _state["heightmap_bytes"]:
        return "No heightmap generated yet", 404
    buf = io.BytesIO(_state["heightmap_bytes"])
    return send_file(buf, mimetype="image/png",
                     as_attachment=True, download_name="island_heightmap.png")

@app.route("/download/layout")
def download_layout():
    if not _state["layout"]:
        return "No layout generated yet", 404
    buf = io.BytesIO(json.dumps(_state["layout"], indent=2).encode())
    return send_file(buf, mimetype="application/json",
                     as_attachment=True, download_name="island_layout.json")

@app.route("/download/preview")
def download_preview():
    if not _state["preview_bytes"]:
        return "No preview generated yet", 404
    buf = io.BytesIO(_state["preview_bytes"])
    return send_file(buf, mimetype="image/png",
                     as_attachment=True, download_name="island_preview.png")

# ─────────────────────────────────────────────────────────────
# RANDOM SEED
# ─────────────────────────────────────────────────────────────

@app.route("/random_seed")
def random_seed():
    import random
    return jsonify({"seed": random.randint(1, 99999)})

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"""
  ╔══════════════════════════════════╗
  ║      ISLAND FORGE — v1.0         ║
  ║  http://localhost:{port}            ║
  ╚══════════════════════════════════╝

  Outputs saved to: {OUTPUT_DIR}
  Audio library:    {AUDIO_DIR}
""")
    app.run(host="0.0.0.0", port=port, debug=False)
