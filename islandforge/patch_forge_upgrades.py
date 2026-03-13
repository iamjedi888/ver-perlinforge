#!/usr/bin/env python3
"""
patch_forge_upgrades.py — Phase 5: Island Forge Upgrades
Run on VM: python3 ~/ver-perlinforge/islandforge/patch_forge_upgrades.py

Adds:
  - routes/forge_upgrades.py   (/api/presets/*, /api/save_island)
  - oracle_db.py additions     (presets + island gallery functions)
  - scripts/migrate_forge.sql  (island_presets table)
  - Patches index.html         (preset library UI, biome painter, gallery save, verse download)
"""
import os, subprocess, time, shutil

ROOT      = "/home/ubuntu/ver-perlinforge/islandforge"
ROUTES    = os.path.join(ROOT, "routes")
TEMPLATES = os.path.join(ROOT, "templates")
SCRIPTS   = os.path.join(ROOT, "scripts")

os.makedirs(SCRIPTS, exist_ok=True)

# ══════════════════════════════════════════════════════════════
# 1. routes/forge_upgrades.py
# ══════════════════════════════════════════════════════════════
open(os.path.join(ROUTES, "forge_upgrades.py"), "w").write('''"""
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
''')
print("✓ routes/forge_upgrades.py")

# ══════════════════════════════════════════════════════════════
# 2. oracle_db.py additions
# ══════════════════════════════════════════════════════════════
import json as _json
oracle_path = os.path.join(ROOT, "oracle_db.py")
src = open(oracle_path).read()

additions = '''

# ── PRESETS ──────────────────────────────────────────────────

def get_presets(limit: int = 100) -> list:
    """Return all public island presets."""
    if not db_available():
        return []
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, epic_id, display_name, name, config, created_at
                   FROM island_presets
                   WHERE is_public = 1
                   ORDER BY created_at DESC
                   FETCH FIRST :1 ROWS ONLY""",
                [limit]
            )
            rows = []
            for row in cur.fetchall():
                try:
                    cfg = _json.loads(row[4]) if row[4] else {}
                except Exception:
                    cfg = {}
                rows.append({
                    "id":           row[0],
                    "epic_id":      row[1],
                    "display_name": row[2],
                    "name":         row[3],
                    "config":       cfg,
                    "created_at":   str(row[5]) if row[5] else "",
                })
            return rows
    except Exception as e:
        _log(f"get_presets error: {e}")
        return []

def get_preset_by_id(preset_id: int) -> dict:
    """Return a single preset by ID."""
    if not db_available():
        return None
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, epic_id, display_name, name, config, created_at
                   FROM island_presets WHERE id = :1""",
                [preset_id]
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                cfg = _json.loads(row[4]) if row[4] else {}
            except Exception:
                cfg = {}
            return {
                "id":           row[0],
                "epic_id":      row[1],
                "display_name": row[2],
                "name":         row[3],
                "config":       cfg,
                "created_at":   str(row[5]) if row[5] else "",
            }
    except Exception as e:
        _log(f"get_preset_by_id error: {e}")
        return None

def save_preset(epic_id: str, display_name: str, name: str,
                config: dict, is_public: bool = True):
    """Save an island preset. Returns new ID."""
    if not db_available():
        return None
    try:
        with _conn() as conn:
            cur = conn.cursor()
            new_id = cur.var(__import__("oracledb").NUMBER)
            cur.execute(
                """INSERT INTO island_presets
                   (epic_id, display_name, name, config, is_public, created_at)
                   VALUES (:1, :2, :3, :4, :5, CURRENT_TIMESTAMP)
                   RETURNING id INTO :6""",
                [epic_id, display_name, name, _json.dumps(config),
                 1 if is_public else 0, new_id]
            )
            conn.commit()
            return int(new_id.getvalue()[0])
    except Exception as e:
        _log(f"save_preset error: {e}")
        return None

def delete_preset(preset_id: int, epic_id: str) -> bool:
    """Delete a preset — only owner can delete."""
    if not db_available():
        return False
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM island_presets WHERE id = :1 AND epic_id = :2",
                [preset_id, epic_id]
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        _log(f"delete_preset error: {e}")
        return False

def save_island_to_gallery(epic_id: str, display_name: str, name: str,
                            seed, dominant_biome: str, preview_b64: str,
                            config: dict, verse_data: dict,
                            stickers: list, is_public: bool = True):
    """Save a generated island to the gallery + room wall."""
    if not db_available():
        return None
    try:
        # Upload preview to OCI if available, else store truncated b64
        preview_url = ""
        if preview_b64:
            try:
                import base64, oci.object_storage, os as _os
                client = _oci_client()
                img_bytes = base64.b64decode(preview_b64)
                obj_name  = f"previews/{epic_id or 'anon'}_{seed}_{int(__import__('time').time())}.png"
                ns        = _os.environ.get("OCI_NAMESPACE","")
                bucket    = _os.environ.get("OCI_BUCKET","triptokforge")
                client.put_object(ns, bucket, obj_name,
                                  img_bytes,
                                  content_type="image/png")
                region = _os.environ.get("OCI_REGION","us-ashburn-1")
                preview_url = f"https://objectstorage.{region}.oraclecloud.com/n/{ns}/b/{bucket}/o/{obj_name}"
            except Exception as oci_e:
                _log(f"OCI preview upload skipped: {oci_e}")

        with _conn() as conn:
            cur = conn.cursor()
            new_id = cur.var(__import__("oracledb").NUMBER)
            cur.execute(
                """INSERT INTO island_saves
                   (epic_id, display_name, seed, name, dominant_biome,
                    preview_url, config, verse_data, stickers, is_public, created_at)
                   VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,CURRENT_TIMESTAMP)
                   RETURNING id INTO :11""",
                [epic_id, display_name, seed, name, dominant_biome,
                 preview_url,
                 _json.dumps(config),
                 _json.dumps(verse_data),
                 _json.dumps(stickers),
                 1 if is_public else 0,
                 new_id]
            )
            conn.commit()
            return int(new_id.getvalue()[0])
    except Exception as e:
        _log(f"save_island_to_gallery error: {e}")
        return None
'''

if "get_presets" not in src:
    # add json import at top if missing
    if "import json" not in src:
        src = "import json as _json\n" + src
    else:
        src = src.replace("import json", "import json as _json\n# alias\n_json = json")
    src = src.rstrip() + "\n" + additions
    open(oracle_path, "w").write(src)
    print("✓ oracle_db.py — preset + gallery functions added")
else:
    print("→ oracle_db.py — already has preset functions")

# ══════════════════════════════════════════════════════════════
# 3. SQL Migration
# ══════════════════════════════════════════════════════════════
open(os.path.join(SCRIPTS, "migrate_forge.sql"), "w").write("""
-- Run once in Oracle console

-- Expand island_saves with new columns
ALTER TABLE island_saves ADD (display_name VARCHAR2(128));
ALTER TABLE island_saves ADD (config       CLOB);
ALTER TABLE island_saves ADD (verse_data   CLOB);
ALTER TABLE island_saves ADD (stickers     VARCHAR2(2048));
ALTER TABLE island_saves ADD (is_public    NUMBER(1) DEFAULT 1);

-- New: island presets library
CREATE TABLE island_presets (
    id            NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    epic_id       VARCHAR2(64),
    display_name  VARCHAR2(128),
    name          VARCHAR2(64),
    config        CLOB,
    is_public     NUMBER(1)     DEFAULT 1,
    created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);
""")
print("✓ scripts/migrate_forge.sql")

# ══════════════════════════════════════════════════════════════
# 4. Register blueprint in server.py
# ══════════════════════════════════════════════════════════════
server_path = os.path.join(ROOT, "server.py")
src = open(server_path).read()
if "forge_upgrades_bp" not in src:
    lines = src.splitlines()
    last_import_idx = 0
    last_register_idx = 0
    for i, line in enumerate(lines):
        if "import" in line and "_bp" in line:
            last_import_idx = i
        if "register_blueprint" in line:
            last_register_idx = i
    lines.insert(last_import_idx + 1,
        "from routes.forge_upgrades import forge_upgrades_bp")
    lines.insert(last_register_idx + 2,
        "app.register_blueprint(forge_upgrades_bp)")
    open(server_path, "w").write("\n".join(lines))
    print("✓ server.py — forge_upgrades_bp registered")
else:
    print("→ server.py — already registered")

# ══════════════════════════════════════════════════════════════
# 5. Patch index.html — inject preset library + biome painter
#    + gallery save + verse download button
# ══════════════════════════════════════════════════════════════
index_path = os.path.join(ROOT, "index.html")
html = open(index_path).read()

# ── 5a. Add Save to Gallery + Download Verse buttons ─────────
OLD_BUTTONS = '''      <a class="btn-dl btn-secondary btn-disabled" id="dl-hm" href="/download/heightmap" download="island_heightmap.png">↓ Heightmap PNG</a>
      <a class="btn-dl btn-secondary btn-disabled" id="dl-js" href="/download/layout" download="island_layout.json">↓ Layout JSON</a>
      <a class="btn-dl btn-secondary btn-disabled" id="dl-pv" href="/download/preview" download="island_preview.png">↓ Preview</a>
      <button class="btn-dl btn-secondary btn-disabled" id="btn-verse" onclick="openVerse()"></> Verse Constants</button>'''

NEW_BUTTONS = '''      <a class="btn-dl btn-secondary btn-disabled" id="dl-hm" href="/download/heightmap" download="island_heightmap.png">↓ Heightmap PNG</a>
      <a class="btn-dl btn-secondary btn-disabled" id="dl-js" href="/download/layout" download="island_layout.json">↓ Layout JSON</a>
      <a class="btn-dl btn-secondary btn-disabled" id="dl-pv" href="/download/preview" download="island_preview.png">↓ Preview</a>
      <button class="btn-dl btn-secondary btn-disabled" id="btn-verse" onclick="openVerse()"></> Verse Constants</button>
      <button class="btn-dl btn-secondary btn-disabled" id="btn-verse-dl" onclick="downloadVerse()">↓ .verse File</button>
      <button class="btn-dl btn-primary btn-disabled"   id="btn-save-gallery" onclick="saveToGallery()">⊕ Save to Room</button>
      <button class="btn-dl btn-secondary"              id="btn-save-preset"  onclick="openSavePreset()">☆ Save Preset</button>'''

if "btn-save-gallery" not in html:
    html = html.replace(OLD_BUTTONS, NEW_BUTTONS)
    print("✓ index.html — save/verse-dl/preset buttons added")
else:
    print("→ index.html — buttons already present")

# ── 5b. Inject Preset Library panel + Biome Painter + Save modal ──
PRESET_CSS = """
<style id="forge-upgrades-css">
/* ── Preset Library ───────────────────────── */
.preset-section{margin-top:18px;border-top:1px solid var(--border);padding-top:16px}
.preset-section-title{font-family:var(--mono);font-size:10px;letter-spacing:2px;
  text-transform:uppercase;color:var(--dim);margin-bottom:10px;display:flex;
  align-items:center;justify-content:space-between}
.preset-list{display:flex;flex-direction:column;gap:6px;max-height:220px;overflow-y:auto;
  scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.preset-item{display:flex;align-items:center;gap:8px;padding:8px 10px;
  background:rgba(0,229,160,.04);border:1px solid var(--border2);cursor:pointer;
  transition:all .15s}
.preset-item:hover{border-color:var(--accent);background:rgba(0,229,160,.08)}
.preset-item-name{font-family:var(--mono);font-size:11px;color:var(--fg);flex:1;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.preset-item-author{font-family:var(--mono);font-size:10px;color:var(--dim)}
.preset-item-del{font-size:11px;color:var(--dim);cursor:pointer;padding:2px 6px;
  transition:color .15s;flex-shrink:0}
.preset-item-del:hover{color:#ff4060}
.preset-empty{font-family:var(--mono);font-size:10px;color:var(--dim);
  padding:12px;text-align:center;letter-spacing:2px}

/* ── Biome Painter ────────────────────────── */
.biome-painter{margin-top:14px;border-top:1px solid var(--border);padding-top:14px;
  display:none}
.biome-painter.active{display:block}
.painter-title{font-family:var(--mono);font-size:10px;letter-spacing:2px;
  text-transform:uppercase;color:var(--dim);margin-bottom:8px}
.painter-brushes{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.brush-btn{display:flex;align-items:center;gap:5px;padding:5px 10px;
  border:1px solid var(--border2);cursor:pointer;font-family:var(--mono);font-size:10px;
  color:var(--dim);transition:all .15s;background:none}
.brush-btn:hover,.brush-btn.active{border-color:var(--accent);color:var(--accent)}
.brush-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.painter-controls{display:flex;gap:8px;align-items:center;margin-bottom:8px}
.painter-controls label{font-family:var(--mono);font-size:10px;color:var(--dim);
  letter-spacing:1px}
.brush-size-slider{accent-color:var(--accent);flex:1;max-width:100px;cursor:pointer}
.painter-hint{font-family:var(--mono);font-size:9px;color:var(--dim);
  letter-spacing:1px;opacity:.7}
#biome-canvas-overlay{position:absolute;top:0;left:0;cursor:crosshair;opacity:.7;
  display:none;border-radius:inherit}

/* ── Save Preset Modal ────────────────────── */
#save-preset-modal{position:fixed;inset:0;z-index:500;background:rgba(2,4,8,.88);
  backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;
  opacity:0;pointer-events:none;transition:opacity .2s}
#save-preset-modal.open{opacity:1;pointer-events:all}
.sp-card{width:360px;background:#0d1018;border:1px solid var(--border2);padding:28px;
  position:relative}
.sp-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--accent),transparent)}
.sp-title{font-family:'Orbitron',monospace;font-size:.75rem;font-weight:700;
  letter-spacing:2px;color:#fff;margin-bottom:18px}
.sp-card input,.sp-card select{width:100%;background:rgba(0,229,160,.04);
  border:1px solid var(--border2);color:var(--fg);font-family:var(--mono);
  font-size:11px;padding:9px 12px;outline:none;margin-bottom:10px;letter-spacing:1px}
.sp-card input:focus,.sp-card select:focus{border-color:var(--accent)}
.sp-row{display:flex;gap:8px}
.sp-btn{flex:1;font-family:'Orbitron',monospace;font-size:.58rem;font-weight:700;
  letter-spacing:2px;text-transform:uppercase;padding:9px;cursor:pointer;
  border:none;transition:background .15s}
.sp-btn.primary{background:var(--accent);color:#000}
.sp-btn.primary:hover{background:#fff}
.sp-btn.cancel{background:rgba(255,64,96,.1);color:#ff4060;border:1px solid rgba(255,64,96,.2)}
.sp-btn.cancel:hover{background:rgba(255,64,96,.2)}
.sp-msg{font-family:var(--mono);font-size:10px;margin-top:8px;
  letter-spacing:1px;display:none}
.sp-check{display:flex;align-items:center;gap:8px;margin-bottom:12px;
  font-family:var(--mono);font-size:10px;color:var(--dim);cursor:pointer}
.sp-check input{width:auto;margin-bottom:0;cursor:pointer}

/* ── Save toast ───────────────────────────── */
.save-confirm{position:fixed;bottom:24px;right:24px;z-index:600;
  background:#0d1018;border:1px solid var(--accent);padding:12px 20px;
  font-family:var(--mono);font-size:11px;color:var(--accent);letter-spacing:2px;
  text-transform:uppercase;opacity:0;transform:translateY(8px);
  transition:all .3s;pointer-events:none}
.save-confirm.show{opacity:1;transform:translateY(0)}
</style>
"""

PRESET_HTML = """
<!-- FORGE UPGRADES: preset library injected below controls -->
<div class="preset-section" id="forge-presets-section">
  <div class="preset-section-title">
    <span>⊙ Preset Library</span>
    <span id="preset-count" style="color:var(--dim);font-size:9px"></span>
  </div>
  <div class="preset-list" id="preset-list">
    <div class="preset-empty">Loading presets...</div>
  </div>
</div>

<!-- Biome Painter (shown after generation) -->
<div class="biome-painter" id="biome-painter">
  <div class="painter-title">◈ Biome Painter — Override Zones</div>
  <div class="painter-brushes" id="painter-brushes"></div>
  <div class="painter-controls">
    <label>Brush</label>
    <input type="range" class="brush-size-slider" id="brush-size" min="4" max="40" value="14"/>
    <span id="brush-size-label" style="font-family:var(--mono);font-size:10px;color:var(--dim)">14px</span>
  </div>
  <div class="painter-hint">Paint directly on the map preview → regenerate to apply overrides</div>
  <button onclick="clearBiomePaints()" style="margin-top:8px;font-family:var(--mono);font-size:10px;
    padding:5px 12px;background:none;border:1px solid var(--border2);color:var(--dim);cursor:pointer;
    transition:all .15s" onmouseover="this.style.color='var(--accent)'" onmouseout="this.style.color='var(--dim)'">
    ✕ Clear Overrides
  </button>
</div>

<!-- Save Preset Modal -->
<div id="save-preset-modal">
  <div class="sp-card">
    <div class="sp-title">Save Island Preset</div>
    <input type="text" id="sp-name" placeholder="Preset name (e.g. Tundra Warzone)" maxlength="64"/>
    <label class="sp-check">
      <input type="checkbox" id="sp-public" checked/>
      Share publicly with all members
    </label>
    <div class="sp-row">
      <button class="sp-btn primary" onclick="confirmSavePreset()">Save Preset</button>
      <button class="sp-btn cancel" onclick="closeSavePreset()">Cancel</button>
    </div>
    <div class="sp-msg" id="sp-msg"></div>
  </div>
</div>

<!-- Save confirm toast -->
<div class="save-confirm" id="save-confirm">Island saved to Room ✓</div>
"""

FORGE_JS = """
<script id="forge-upgrades-js">
// ── Biome colours (match server biome palette) ─────────────
const BIOME_COLOURS = {
  'Ocean':      '#1a4a7a',
  'Beach':      '#d4b483',
  'Grassland':  '#4a7c3f',
  'Forest':     '#2d5a1b',
  'Desert':     '#c8a04a',
  'Tundra':     '#a8c4d0',
  'Mountain':   '#7a7068',
  'Snow':       '#dce8f0',
  'Swamp':      '#4a5c3a',
  'Jungle':     '#1e6b2a',
  'Volcanic':   '#8b2a0a',
  'Canyon':     '#9a5a30',
};
let _paintBiome = null;
let _biomePaints = {}; // {x_norm: {y_norm: biomeName}}
let _isPainting = false;
let _brushSize = 14;
const BIOME_NAMES = Object.keys(BIOME_COLOURS);

// ── Preset Library ─────────────────────────────────────────
async function loadPresets() {
  try {
    const r = await fetch('/api/presets');
    const d = await r.json();
    const list = document.getElementById('preset-list');
    const cnt  = document.getElementById('preset-count');
    const presets = d.presets || [];
    cnt.textContent = presets.length + ' saved';
    if (!presets.length) {
      list.innerHTML = '<div class="preset-empty">No presets yet — generate and save one</div>';
      return;
    }
    list.innerHTML = presets.map(p => `
      <div class="preset-item" onclick="applyPreset(${p.id})">
        <div class="preset-item-name">${p.name}</div>
        <div class="preset-item-author">${p.display_name}</div>
        <span class="preset-item-del" onclick="event.stopPropagation();deletePreset(${p.id})" title="Delete">✕</span>
      </div>`).join('');
  } catch(e) {
    document.getElementById('preset-list').innerHTML =
      '<div class="preset-empty">Could not load presets</div>';
  }
}

async function applyPreset(id) {
  try {
    const r = await fetch('/api/presets/load/' + id);
    const d = await r.json();
    if (!d.ok) { alert(d.error); return; }
    const c = d.preset.config;
    if (c.seed)         document.getElementById('seed').value    = c.seed;
    if (c.size)         document.getElementById('size').value    = c.size;
    if (c.plots)        document.getElementById('plots').value   = c.plots;
    if (c.spacing)      document.getElementById('spacing').value = c.spacing;
    if (c.world_size)   selectWorldSizeByPreset(c.world_size, c.world_size_cm);
    if (c.weights) {
      ['sub_bass','bass','midrange','presence','brilliance'].forEach(k => {
        const el = document.getElementById(k);
        if (el && c.weights[k] != null) el.value = Math.round(c.weights[k]*100);
      });
    }
    if (c.biome_overrides) _biomePaints = c.biome_overrides;
    showSaveConfirm('Preset loaded — hit Generate ▶', 'var(--blue)');
  } catch(e) { alert('Error loading preset'); }
}

async function deletePreset(id) {
  if (!confirm('Delete this preset?')) return;
  await fetch('/api/presets/delete/' + id, {method:'POST'});
  loadPresets();
}

function selectWorldSizeByPreset(preset, cm) {
  const card = document.querySelector(`[data-preset="${preset}"]`);
  if (card) card.click();
}

// ── Save Preset Modal ──────────────────────────────────────
function openSavePreset() {
  if (!window._verseData) { alert('Generate an island first.'); return; }
  document.getElementById('save-preset-modal').classList.add('open');
  document.getElementById('sp-name').focus();
}
function closeSavePreset() {
  document.getElementById('save-preset-modal').classList.remove('open');
  document.getElementById('sp-msg').style.display = 'none';
}

async function confirmSavePreset() {
  const name = document.getElementById('sp-name').value.trim();
  if (!name) { showSpMsg('Enter a name first', false); return; }
  const isPublic = document.getElementById('sp-public').checked;
  const d = window._verseData;
  const config = {
    seed:          parseInt(document.getElementById('seed').value),
    size:          parseInt(document.getElementById('size').value),
    plots:         parseInt(document.getElementById('plots').value),
    spacing:       parseInt(document.getElementById('spacing').value),
    world_size:    window._wsPreset,
    world_size_cm: window._wsCm,
    weights: {
      sub_bass:   parseFloat(document.getElementById('sub_bass').value)/100,
      bass:       parseFloat(document.getElementById('bass').value)/100,
      midrange:   parseFloat(document.getElementById('midrange').value)/100,
      presence:   parseFloat(document.getElementById('presence').value)/100,
      brilliance: parseFloat(document.getElementById('brilliance').value)/100,
    },
    biome_overrides: _biomePaints,
  };
  try {
    const r = await fetch('/api/presets/save', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({name, config, is_public: isPublic})
    });
    const res = await r.json();
    if (res.ok) {
      showSpMsg('Saved! ✓', true);
      setTimeout(() => { closeSavePreset(); loadPresets(); }, 1000);
    } else {
      showSpMsg(res.error || 'Error saving', false);
    }
  } catch(e) { showSpMsg('Network error', false); }
}

function showSpMsg(txt, ok) {
  const el = document.getElementById('sp-msg');
  el.textContent = txt;
  el.style.color = ok ? 'var(--accent)' : '#ff4060';
  el.style.display = 'block';
}

// ── Verse Download ─────────────────────────────────────────
function downloadVerse() {
  const code = document.getElementById('verse-code').textContent;
  if (!code) { openVerse(); return; }
  const seed = document.getElementById('seed').value;
  const blob = new Blob([code], {type:'text/plain'});
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = `plot_registry_seed${seed}.verse`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Gallery / Room Save ────────────────────────────────────
async function saveToGallery() {
  const d = window._verseData;
  if (!d) { alert('Generate an island first.'); return; }
  const name    = prompt('Island name:', 'Island ' + document.getElementById('seed').value);
  if (!name) return;
  const dominant = (d.biome_stats && d.biome_stats[0]) ? d.biome_stats[0].name : 'Unknown';
  const preview  = document.getElementById('map-img').src.split('base64,')[1] || '';
  const config   = {
    seed:     parseInt(document.getElementById('seed').value),
    size:     parseInt(document.getElementById('size').value),
    plots:    parseInt(document.getElementById('plots').value),
    world_size: window._wsPreset,
  };
  try {
    const r = await fetch('/api/save_island', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        name, seed: config.seed, dominant_biome: dominant,
        preview_b64: preview, config, verse_data: d.verse_constants || {},
        stickers: [], is_public: true
      })
    });
    const res = await r.json();
    if (res.ok) {
      showSaveConfirm('Island saved to Room ✓');
    } else {
      showSaveConfirm(res.error || 'Error saving', '#ff4060');
    }
  } catch(e) { showSaveConfirm('Network error', '#ff4060'); }
}

function showSaveConfirm(msg, color) {
  const el = document.getElementById('save-confirm');
  el.textContent = msg;
  el.style.borderColor  = color || 'var(--accent)';
  el.style.color        = color || 'var(--accent)';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

// ── Biome Painter ──────────────────────────────────────────
function initBiomePainter() {
  const brushes = document.getElementById('painter-brushes');
  brushes.innerHTML = BIOME_NAMES.map(b => `
    <div class="brush-btn${_paintBiome===b?' active':''}" onclick="selectBrush('${b}')">
      <div class="brush-dot" style="background:${BIOME_COLOURS[b]}"></div>
      ${b}
    </div>`).join('');
  document.getElementById('biome-painter').classList.add('active');
  setupPainterCanvas();
}

function selectBrush(biome) {
  _paintBiome = biome;
  document.querySelectorAll('.brush-btn').forEach(b =>
    b.classList.toggle('active', b.textContent.trim().startsWith(biome)));
}

function clearBiomePaints() {
  _biomePaints = {};
  const canvas = document.getElementById('biome-canvas-overlay');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  showSaveConfirm('Biome overrides cleared', 'var(--dim)');
}

function setupPainterCanvas() {
  const mapImg = document.getElementById('map-img');
  if (!mapImg || mapImg.style.display === 'none') return;
  const wrap = mapImg.parentElement;
  wrap.style.position = 'relative';
  let canvas = document.getElementById('biome-canvas-overlay');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'biome-canvas-overlay';
    wrap.appendChild(canvas);
  }
  canvas.width  = mapImg.offsetWidth  || 512;
  canvas.height = mapImg.offsetHeight || 512;
  canvas.style.width  = mapImg.offsetWidth  + 'px';
  canvas.style.height = mapImg.offsetHeight + 'px';
  canvas.style.display = 'block';

  const ctx = canvas.getContext('2d');

  function paint(e) {
    if (!_paintBiome) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left);
    const y = (e.clientY - rect.top);
    ctx.beginPath();
    ctx.arc(x, y, _brushSize, 0, Math.PI*2);
    ctx.fillStyle = BIOME_COLOURS[_paintBiome] + 'cc';
    ctx.fill();
    // Store normalized coords
    const nx = (x / canvas.width).toFixed(4);
    const ny = (y / canvas.height).toFixed(4);
    if (!_biomePaints[nx]) _biomePaints[nx] = {};
    _biomePaints[nx][ny] = _paintBiome;
  }

  canvas.addEventListener('mousedown', e => { _isPainting=true; paint(e); });
  canvas.addEventListener('mousemove', e => { if(_isPainting) paint(e); });
  canvas.addEventListener('mouseup',   () => _isPainting=false);
  canvas.addEventListener('mouseleave',() => _isPainting=false);

  // Touch support
  canvas.addEventListener('touchstart', e => { _isPainting=true; paint(e.touches[0]); });
  canvas.addEventListener('touchmove',  e => { e.preventDefault(); if(_isPainting) paint(e.touches[0]); }, {passive:false});
  canvas.addEventListener('touchend',   () => _isPainting=false);
}

// Brush size slider
const bsSlider = document.getElementById('brush-size');
if (bsSlider) {
  bsSlider.addEventListener('input', e => {
    _brushSize = parseInt(e.target.value);
    document.getElementById('brush-size-label').textContent = _brushSize + 'px';
  });
}

// Hook into generate completion — show painter + enable buttons
const _origGenComplete = window._onGenerateComplete;
window._onGenerateComplete = function(d) {
  if (_origGenComplete) _origGenComplete(d);
  initBiomePainter();
  ['btn-verse-dl','btn-save-gallery'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('btn-disabled');
  });
};

// Init presets on load
loadPresets();

// Close save preset modal on bg click
document.getElementById('save-preset-modal').addEventListener('click', function(e) {
  if (e.target === this) closeSavePreset();
});
</script>
"""

# Inject CSS before </head>
if "forge-upgrades-css" not in html:
    html = html.replace("</head>", PRESET_CSS + "\n</head>")
    print("✓ index.html — CSS injected")

# Inject HTML before </body>
if "forge-upgrades-js" not in html:
    # Insert preset section after the world-size controls panel
    if 'id="ws-presets"' in html:
        html = html.replace(
            'id="ws-presets">',
            'id="ws-presets">'
        )
    html = html.replace("</body>", PRESET_HTML + "\n" + FORGE_JS + "\n</body>")
    print("✓ index.html — preset library + biome painter + JS injected")
else:
    print("→ index.html — upgrades already present")

# Hook _onGenerateComplete into the existing generate() success path
# Find the line that enables download buttons and add the hook call
if "_onGenerateComplete" not in html:
    old_enable = "['dl-hm','dl-js','dl-pv','btn-verse'].forEach(id => $(id).classList.remove('btn-disabled'));"
    new_enable = old_enable + "\n    if(window._onGenerateComplete) window._onGenerateComplete(d);"
    html = html.replace(old_enable, new_enable)
    print("✓ index.html — _onGenerateComplete hook added")

open(index_path, "w").write(html)
print("✓ index.html saved")

# ══════════════════════════════════════════════════════════════
# 6. Restart
# ══════════════════════════════════════════════════════════════
print("\n▸ Restarting...")
subprocess.run(["sudo","systemctl","restart","islandforge"], check=True)
time.sleep(5)

for path in ["/forge", "/api/presets", "/health"]:
    r = subprocess.run(
        ["curl","-s","-o","/dev/null","-w","%{http_code}",
         f"http://127.0.0.1:5000{path}"],
        capture_output=True, text=True
    )
    print(f"  {path:30s} → {r.stdout}")

print("""
✅ Phase 5 — Island Forge Upgrades live!

New features on /forge:
  ☆ Save Preset    — name + save any config to the preset library
  ⊙ Preset Library — load community presets instantly into controls
  ◈ Biome Painter  — paint biome overrides on map after generation
  ↓ .verse File    — download plot_registry.verse directly
  ⊕ Save to Room   — save island to your card wall room

Oracle SQL to run once:
  ALTER TABLE island_saves ADD (display_name VARCHAR2(128));
  ALTER TABLE island_saves ADD (config CLOB);
  ALTER TABLE island_saves ADD (verse_data CLOB);
  ALTER TABLE island_saves ADD (stickers VARCHAR2(2048));
  ALTER TABLE island_saves ADD (is_public NUMBER(1) DEFAULT 1);

  CREATE TABLE island_presets (
    id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    epic_id      VARCHAR2(64),
    display_name VARCHAR2(128),
    name         VARCHAR2(64),
    config       CLOB,
    is_public    NUMBER(1) DEFAULT 1,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
""")
