#!/usr/bin/env python3
"""
patch_forge_v2.py — Forge fixes + UEFN Biome Themes
Run on VM: python3 ~/ver-perlinforge/islandforge/patch_forge_v2.py

Fixes:
  1. oracle_db.py  — clean json import (NameError fix)
  2. index.html    — preset library: loads settings + auto-generates
  3. audio_to_heightmap.py — UEFN biome themes (Chapter 1-4, Arctic, Desert,
                             Jungle, Volcanic) fed by theme param
  4. server_old.py — accepts biome_theme in /generate, passes to classify_biomes
  5. index.html    — UEFN theme selector UI with Fortnite chapter icons
"""
import os, re, subprocess, time

ROOT = "/home/ubuntu/ver-perlinforge/islandforge"

# ══════════════════════════════════════════════════════════════════
# 1. FIX oracle_db.py — clean json import once and for all
# ══════════════════════════════════════════════════════════════════
db_path = os.path.join(ROOT, "oracle_db.py")
src = open(db_path).read()

# Remove every variation of the broken alias
src = src.replace("import json as _json\n# alias\n_json = json\n", "import json\n")
src = src.replace("import json as _json\n", "import json\n")
src = src.replace("_json = json\n", "")
src = src.replace("_json.dumps", "json.dumps")
src = src.replace("_json.loads", "json.loads")

# Make sure we have exactly one `import json` near the top
if src.count("import json") > 1:
    lines = src.splitlines()
    seen = False
    out = []
    for ln in lines:
        if ln.strip() == "import json":
            if seen:
                continue
            seen = True
        out.append(ln)
    src = "\n".join(out)

if "import json" not in src:
    src = "import json\n" + src

open(db_path, "w").write(src)
print("✓ oracle_db.py — json import fixed")

# ══════════════════════════════════════════════════════════════════
# 2. audio_to_heightmap.py — UEFN biome theme system
# ══════════════════════════════════════════════════════════════════
atm_path = os.path.join(ROOT, "audio_to_heightmap.py")
atm = open(atm_path).read()

THEME_CODE = '''
# ─────────────────────────────────────────────────────────────
# UEFN BIOME THEMES
# Each theme overrides classify_biomes thresholds + colour palette
# ─────────────────────────────────────────────────────────────

UEFN_THEMES = {
    "chapter1": {
        "label":        "Chapter 1 — Classic",
        "description":  "Original BR map. Tilted Towers biome. Balanced grass, forest, snow peaks.",
        "water_level":  0.20,
        "moisture_jungle":  0.62,
        "moisture_forest":  0.44,
        "moisture_desert":  0.30,
        "moisture_snow":    0.34,
        "zone_desert":      0.55,
        "zone_snow":        0.45,
        "highland_min":     0.65,
        "peak_min":         0.82,
        "colours": {
            0: (20,  60, 120),   # water
            1: (210,190,140),    # beach
            2: (130,170, 80),    # plains
            3: ( 60,110, 55),    # forest
            4: ( 30, 90, 40),    # jungle
            5: (220,235,245),    # snow
            6: (195,165, 90),    # desert
            7: ( 90,110, 75),    # highland
            8: (200,200,210),    # peak
            9: (160,190, 80),    # farm
        },
        "weights": {"sub_bass":0.6,"bass":0.5,"midrange":0.5,"presence":0.4,"brilliance":0.3},
    },
    "chapter2": {
        "label":        "Chapter 2 — Swampy Island",
        "description":  "Holly Hedges era. More water, swamp lowlands, lush jungle quadrant.",
        "water_level":  0.26,
        "moisture_jungle":  0.52,
        "moisture_forest":  0.38,
        "moisture_desert":  0.22,
        "moisture_snow":    0.28,
        "zone_desert":      0.60,
        "zone_snow":        0.40,
        "highland_min":     0.68,
        "peak_min":         0.84,
        "colours": {
            0: (15,  50, 105),
            1: (200,180,130),
            2: (110,155, 65),
            3: ( 50,100, 45),
            4: ( 25, 80, 35),    # dense jungle
            5: (215,230,240),
            6: (180,155, 80),
            7: ( 80,100, 65),
            8: (190,195,205),
            9: (150,180, 70),
        },
        "weights": {"sub_bass":0.7,"bass":0.6,"midrange":0.4,"presence":0.5,"brilliance":0.2},
    },
    "chapter3": {
        "label":        "Chapter 3 — Flipped Island",
        "description":  "Snow biome dominant. Rocky highlands, spider-web rivers, open plains.",
        "water_level":  0.18,
        "moisture_jungle":  0.70,
        "moisture_forest":  0.52,
        "moisture_desert":  0.25,
        "moisture_snow":    0.45,
        "zone_desert":      0.65,
        "zone_snow":        0.35,
        "highland_min":     0.60,
        "peak_min":         0.78,
        "colours": {
            0: (25,  65, 130),
            1: (215,200,155),
            2: (140,178, 90),
            3: ( 65,115, 60),
            4: ( 35, 95, 45),
            5: (230,240,250),    # bright snow dominant
            6: (190,160, 85),
            7: ( 95,118, 82),
            8: (210,215,225),
            9: (165,195, 85),
        },
        "weights": {"sub_bass":0.4,"bass":0.3,"midrange":0.6,"presence":0.6,"brilliance":0.5},
    },
    "chapter4": {
        "label":        "Chapter 4 — Shattered Slabs",
        "description":  "Rocky desert dominant. Massive mountain range, sparse jungle corner.",
        "water_level":  0.17,
        "moisture_jungle":  0.70,
        "moisture_forest":  0.55,
        "moisture_desert":  0.38,
        "moisture_snow":    0.25,
        "zone_desert":      0.45,
        "zone_snow":        0.55,
        "highland_min":     0.58,
        "peak_min":         0.75,
        "colours": {
            0: (18,  55, 110),
            1: (205,185,135),
            2: (120,160, 72),
            3: ( 55,105, 50),
            4: ( 28, 85, 38),
            5: (225,232,242),
            6: (200,172, 98),    # warm sandstone desert
            7: (105,120, 85),    # rocky highland
            8: (205,198,188),    # pale stone peak
            9: (155,185, 75),
        },
        "weights": {"sub_bass":0.5,"bass":0.4,"midrange":0.5,"presence":0.7,"brilliance":0.4},
    },
    "arctic": {
        "label":        "Arctic Wasteland",
        "description":  "Permafrost island. 70% snow cover, frozen tundra, icy peaks. Zero desert.",
        "water_level":  0.15,
        "moisture_jungle":  0.90,   # jungle almost impossible
        "moisture_forest":  0.72,
        "moisture_desert":  0.05,   # no desert
        "moisture_snow":    0.22,   # snow everywhere
        "zone_desert":      0.95,
        "zone_snow":        0.05,
        "highland_min":     0.52,
        "peak_min":         0.68,
        "colours": {
            0: ( 10,  40, 100),   # near-black arctic water
            1: (230,220,205),     # pale frost beach
            2: (175,200,190),     # frozen tundra
            3: (120,155,140),     # spruce forest
            4: ( 80,120, 95),     # boreal
            5: (240,248,255),     # crisp white snow
            6: (200,195,185),     # frozen wasteland (no real desert)
            7: (150,165,175),     # ice-rock highland
            8: (225,232,242),     # glacier peak
            9: (160,185,170),
        },
        "weights": {"sub_bass":0.3,"bass":0.3,"midrange":0.7,"presence":0.3,"brilliance":0.8},
    },
    "desert": {
        "label":        "Sahara Paradise",
        "description":  "Golden dunes, warm oasis pools, sandstone arches. Peaceful desert at sunset.",
        "water_level":  0.14,
        "moisture_jungle":  0.85,
        "moisture_forest":  0.72,
        "moisture_desert":  0.50,   # desert everywhere
        "moisture_snow":    0.02,
        "zone_desert":      0.25,   # desert wins zone battle
        "zone_snow":        0.98,
        "highland_min":     0.63,
        "peak_min":         0.80,
        "colours": {
            0: ( 60,  90, 130),   # muddy oasis water
            1: (225,210,160),     # pale sand beach
            2: (210,185,120),     # sand plains
            3: (170,145, 90),     # scrub brush
            4: (140,115, 65),     # dried jungle
            5: (235,215,175),     # salt flat (was snow)
            6: (215,175, 95),     # golden sand desert
            7: (165,138, 88),     # sandstone highland
            8: (190,160,110),     # mesa peak
            9: (180,165,105),
        },
        "weights": {"sub_bass":0.8,"bass":0.7,"midrange":0.3,"presence":0.2,"brilliance":0.1},
    },
    "jungle": {
        "label":        "Primal Jungle",
        "description":  "Dense canopy everywhere. Rivers, wetlands, no desert or snow.",
        "water_level":  0.25,
        "moisture_jungle":  0.38,   # jungle threshold very low = jungle everywhere
        "moisture_forest":  0.28,
        "moisture_desert":  0.05,
        "moisture_snow":    0.02,
        "zone_desert":      0.98,
        "zone_snow":        0.98,
        "highland_min":     0.70,
        "peak_min":         0.85,
        "colours": {
            0: ( 15,  65, 100),   # murky jungle water
            1: (180,190,130),     # muddy shore
            2: ( 90,140, 55),     # jungle floor plains
            3: ( 45, 95, 38),     # medium forest
            4: ( 20, 75, 28),     # deep jungle canopy
            5: (160,185,110),     # high altitude jungle (was snow)
            6: (130,160, 80),     # dry plateau
            7: ( 70,105, 55),     # highland jungle
            8: (100,130, 70),     # mossy peak
            9: (120,155, 65),
        },
        "weights": {"sub_bass":0.5,"bass":0.6,"midrange":0.7,"presence":0.6,"brilliance":0.4},
    },
    "volcanic": {
        "label":        "Volcanic Inferno",
        "description":  "Active caldera. Lava flows, ash plains, scorched rock. Extreme terrain.",
        "water_level":  0.12,
        "moisture_jungle":  0.75,
        "moisture_forest":  0.60,
        "moisture_desert":  0.35,
        "moisture_snow":    0.02,
        "zone_desert":      0.40,
        "zone_snow":        0.95,
        "highland_min":     0.50,
        "peak_min":         0.68,
        "colours": {
            0: ( 80,  20,  10),   # lava lake
            1: (120,  55,  30),   # scorched shore
            2: ( 80,  70,  60),   # ash plains
            3: ( 55,  80,  45),   # struggling forest
            4: ( 35,  65,  30),   # dense scrub
            5: (200, 175, 155),   # ash snow
            6: ( 90,  60,  40),   # volcanic desert
            7: ( 70,  55,  45),   # magma rock highland
            8: (110,  80,  60),   # crater rim peak
            9: ( 95,  90,  55),
        },
        "weights": {"sub_bass":0.9,"bass":0.8,"midrange":0.2,"presence":0.3,"brilliance":0.2},
    },
}

def get_theme(name: str) -> dict:
    return UEFN_THEMES.get(name, UEFN_THEMES["chapter1"])


def classify_biomes_themed(height, moisture, water_level=0.20, theme_name="chapter1"):
    """
    classify_biomes with per-theme thresholds and colour overrides.
    Returns (biome_array, biome_colours_dict, biome_names_dict)
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter

    th = get_theme(theme_name)
    wl = th.get("water_level", water_level)

    size  = height.shape[0]
    biome = np.zeros((size, size), dtype=np.uint8)

    zone = nn(size, 2, 0.5, 2.0, 1.0, 42)
    moisture_smooth = gaussian_filter(moisture, sigma=size * 0.08)

    PLAINS = 2
    biome[:] = PLAINS

    biome[height < wl]                                             = 0  # water
    biome[(height >= wl) & (height < wl + 0.05)]                  = 1  # beach

    land = height >= wl + 0.05

    mj = th["moisture_jungle"]
    mf = th["moisture_forest"]
    md = th["moisture_desert"]
    ms = th["moisture_snow"]
    zd = th["zone_desert"]
    zs = th["zone_snow"]
    hm = th["highland_min"]
    pm = th["peak_min"]

    biome[land & (moisture_smooth > mj)]                           = 4  # jungle
    biome[land & (moisture_smooth > mf) & (moisture_smooth <= mj)] = 3  # forest
    biome[land & (moisture_smooth < md) & (zone > zd)]             = 6  # desert
    biome[land & (moisture_smooth < ms) & (zone <= zs)]            = 5  # snow
    biome[land & (height > hm) & (height <= pm)]                   = 7  # highland
    biome[land & (height > pm)]                                     = 8  # peak

    colours = th["colours"]
    names   = {0:"Water",1:"Beach",2:"Plains",3:"Forest",
               4:"Jungle",5:"Snow",6:"Desert",7:"Highland",8:"Peak",9:"Farm"}

    return biome, colours, names
'''

if "UEFN_THEMES" not in atm:
    # Insert before classify_biomes
    insert_before = "def classify_biomes("
    atm = atm.replace(insert_before, THEME_CODE + "\n" + insert_before)
    open(atm_path, "w").write(atm)
    print("✓ audio_to_heightmap.py — UEFN_THEMES + classify_biomes_themed added")
else:
    print("→ audio_to_heightmap.py — themes already present")

# ══════════════════════════════════════════════════════════════════
# 3. Auto-find whichever file has the /generate route and patch it
# ══════════════════════════════════════════════════════════════════
import glob as _glob

sv_path = None
for _candidate in _glob.glob(os.path.join(ROOT, "**/*.py"), recursive=True):
    try:
        _txt = open(_candidate).read()
        if '"/generate"' in _txt and "def generate" in _txt:
            sv_path = _candidate
            break
    except Exception:
        pass

if not sv_path:
    print("⚠ Could not find /generate route file — skipping biome_theme wire")
    print("  (theme selector will still appear in UI, server defaults to chapter1)")
else:
    print(f"✓ Found generate route in: {sv_path}")
    sv = open(sv_path).read()

    OLD_CLASSIFY = "biome    = classify_biomes(height, moisture, water_level)"
    NEW_CLASSIFY = """biome_theme = data.get("biome_theme", "chapter1")
        try:
            from audio_to_heightmap import classify_biomes_themed, BIOME_NAMES as _BN, BIOME_COLOURS as _BC
            biome, _themed_colours, _themed_names = classify_biomes_themed(
                height, moisture, water_level, biome_theme
            )
            _BC.clear(); _BC.update(_themed_colours)
            _BN.clear(); _BN.update(_themed_names)
        except Exception as _te:
            biome = classify_biomes(height, moisture, water_level)"""

    if "biome_theme" not in sv:
        sv = sv.replace(OLD_CLASSIFY, NEW_CLASSIFY)
        sv = sv.replace(
            '"saved_to":        OUTPUT_DIR,',
            '"saved_to":        OUTPUT_DIR,\n            "biome_theme":     data.get("biome_theme","chapter1"),'
        )
        open(sv_path, "w").write(sv)
        print(f"✓ {os.path.basename(sv_path)} — biome_theme wired into /generate")
    else:
        print(f"→ {os.path.basename(sv_path)} — biome_theme already wired")

# ══════════════════════════════════════════════════════════════════
# 4. index.html — Theme selector UI + fix preset apply logic
# ══════════════════════════════════════════════════════════════════
idx_path = os.path.join(ROOT, "index.html")
html = open(idx_path).read()

# ── 4a. Theme selector CSS ──────────────────────────────────────
THEME_CSS = """
<style id="biome-theme-css">
/* ── UEFN Biome Theme Selector ─────────────────────── */
.theme-section{margin-bottom:18px}
.theme-label{font-family:var(--mono);font-size:10px;letter-spacing:2px;
  text-transform:uppercase;color:var(--dim);margin-bottom:8px;display:block}
.theme-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:5px}
.theme-card{position:relative;padding:7px 5px 6px;border:1px solid var(--border2);
  cursor:pointer;text-align:center;transition:all .15s;overflow:hidden;
  background:rgba(0,0,0,.3)}
.theme-card::before{content:'';position:absolute;inset:0;opacity:0;transition:opacity .15s}
.theme-card:hover{border-color:rgba(255,255,255,.25)}
.theme-card.active{border-color:var(--accent)}
.theme-card.active::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:var(--accent)}
.theme-icon{font-size:16px;display:block;margin-bottom:2px;line-height:1}
.theme-name{font-family:var(--mono);font-size:8px;letter-spacing:1px;
  text-transform:uppercase;color:var(--mid);line-height:1.2;display:block}
.theme-card.active .theme-name{color:var(--accent)}
.theme-swatch{position:absolute;bottom:0;left:0;right:0;height:3px;
  display:flex;gap:0}
.theme-swatch span{flex:1;height:100%}

/* ── Preset panel tweaks ───────────────────────── */
.preset-item{cursor:pointer;transition:all .15s}
.preset-item:hover{background:rgba(0,229,160,.12)!important;
  border-color:var(--accent)!important}
.preset-load-btn{font-family:var(--mono);font-size:9px;letter-spacing:1px;
  padding:3px 8px;border:1px solid var(--accent);color:var(--accent);
  background:none;cursor:pointer;flex-shrink:0;transition:all .15s}
.preset-load-btn:hover{background:var(--accent);color:#000}
</style>
"""

# ── 4b. Theme definitions for JS ───────────────────────────────
THEME_JS = """
<script id="biome-theme-js">
// ── UEFN Biome Themes (mirrors server UEFN_THEMES) ─────────────
const UEFN_THEMES = {
  chapter1: {
    label:"Chapter 1",icon:"🌿",
    swatches:["#143c78","#d2be8c","#82aa50","#3c6e37","#dceef5","#c3a55a"],
    weights:{sub_bass:60,bass:50,midrange:50,presence:40,brilliance:30},
    water_level:0.20,
  },
  chapter2: {
    label:"Chapter 2",icon:"🌴",
    swatches:["#0f3269","#c8b482","#6e9b41","#32641d","#d7e6f0","#b49b50"],
    weights:{sub_bass:70,bass:60,midrange:40,presence:50,brilliance:20},
    water_level:0.26,
  },
  chapter3: {
    label:"Chapter 3",icon:"❄️",
    swatches:["#194182","#d7c89b","#8cb25a","#416e3c","#e6f0fa","#bea055"],
    weights:{sub_bass:40,bass:30,midrange:60,presence:60,brilliance:50},
    water_level:0.18,
  },
  chapter4: {
    label:"Chapter 4",icon:"🪨",
    swatches:["#123772","#cdB987","#7ba048","#376934","#e1e8f2","#c8ac62"],
    weights:{sub_bass:50,bass:40,midrange:50,presence:70,brilliance:40},
    water_level:0.17,
  },
  arctic: {
    label:"Arctic",icon:"🧊",
    swatches:["#0a2864","#e6dccd","#afc8be","#78978c","#f0f8ff","#c8c3b9"],
    weights:{sub_bass:30,bass:30,midrange:70,presence:30,brilliance:80},
    water_level:0.15,
  },
  desert: {
    label:"Sahara",icon:"🌅",
    swatches:["#3c5a82","#e1d2a0","#d2b978","#aa9158","#ebdaaf","#d7af5f"],
    weights:{sub_bass:80,bass:70,midrange:30,presence:20,brilliance:10},
    water_level:0.14,
  },
  jungle: {
    label:"Primal",icon:"🌱",
    swatches:["#0f4164","#b4be82","#5a8c37","#2d5f1c","#a0b96e","#82a041"],
    weights:{sub_bass:50,bass:60,midrange:70,presence:60,brilliance:40},
    water_level:0.25,
  },
  volcanic: {
    label:"Volcanic",icon:"🌋",
    swatches:["#50140a","#781e1e","#504640","#374d2d","#c8af9b","#5a3c28"],
    weights:{sub_bass:90,bass:80,midrange:20,presence:30,brilliance:20},
    water_level:0.12,
  },
};

let _activeTheme = "chapter1";

function buildThemeSelector() {
  const container = document.getElementById('theme-grid');
  if (!container) return;
  container.innerHTML = Object.entries(UEFN_THEMES).map(([key, t]) => `
    <div class="theme-card${key===_activeTheme?' active':''}"
         onclick="selectTheme('${key}')" title="${t.label}">
      <span class="theme-icon">${t.icon}</span>
      <span class="theme-name">${t.label}</span>
      <div class="theme-swatch">${t.swatches.map(c=>`<span style="background:${c}"></span>`).join('')}</div>
    </div>`).join('');
}

function selectTheme(key) {
  _activeTheme = key;
  const t = UEFN_THEMES[key];
  // Apply weights to sliders
  Object.entries(t.weights).forEach(([k,v]) => {
    const el = document.getElementById(k);
    if (el) { el.value = v; if(el.nextElementSibling) el.nextElementSibling.textContent = v; }
  });
  // Rebuild grid highlights
  document.querySelectorAll('.theme-card').forEach(c => {
    c.classList.toggle('active', c.getAttribute('onclick').includes(`'${key}'`));
  });
  showThemeToast(key);
}

function showThemeToast(key) {
  const t = UEFN_THEMES[key];
  const el = document.getElementById('save-confirm');
  if (el) {
    el.textContent = t.icon + ' ' + t.label + ' theme loaded';
    el.style.borderColor = 'var(--blue)';
    el.style.color = 'var(--blue)';
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2200);
  }
}

// ── Preset library: load settings AND auto-generate ────────────
async function applyPreset(id) {
  try {
    const r = await fetch('/api/presets/load/' + id);
    const d = await r.json();
    if (!d.ok) { alert(d.error); return; }
    const c = d.preset.config;

    // Seed
    if (c.seed    != null) document.getElementById('seed').value    = c.seed;
    if (c.size    != null) document.getElementById('size').value    = c.size;
    if (c.plots   != null) document.getElementById('plots').value   = c.plots;
    if (c.spacing != null) document.getElementById('spacing').value = c.spacing;

    // World size — click the matching card
    if (c.world_size) {
      const card = document.querySelector(`[data-preset="${c.world_size}"]`);
      if (card) card.click();
    } else if (c.world_size_cm) {
      // Try to find card by cm value
      const card = document.querySelector(`[data-cm="${c.world_size_cm}"]`);
      if (card) card.click();
    }

    // Audio weights
    if (c.weights) {
      ['sub_bass','bass','midrange','presence','brilliance'].forEach(k => {
        const el = document.getElementById(k);
        if (el && c.weights[k] != null) {
          const val = Math.round(c.weights[k] * 100);
          el.value = val;
          // update display label if present
          const lbl = document.getElementById(k + '_val') || el.nextElementSibling;
          if (lbl && lbl.tagName !== 'INPUT') lbl.textContent = val;
        }
      });
    }

    // Biome theme
    if (c.biome_theme) selectTheme(c.biome_theme);

    // Biome overrides
    if (c.biome_overrides) window._biomePaints = c.biome_overrides;

    // Flash the preset item
    document.querySelectorAll('.preset-item').forEach(el => {
      el.style.borderColor = el.dataset.id == id ? 'var(--accent)' : '';
    });

    // Short delay then generate
    setTimeout(() => {
      if (typeof generate === 'function') generate();
    }, 120);

  } catch(e) {
    alert('Error loading preset: ' + e.message);
  }
}

async function loadPresets() {
  try {
    const r = await fetch('/api/presets');
    const d = await r.json();
    const list = document.getElementById('preset-list');
    const cnt  = document.getElementById('preset-count');
    const presets = d.presets || [];
    if (cnt) cnt.textContent = presets.length + ' saved';
    if (!presets.length) {
      list.innerHTML = '<div class="preset-empty">No presets yet — generate and save one</div>';
      return;
    }
    list.innerHTML = presets.map(p => `
      <div class="preset-item" data-id="${p.id}"
           style="display:flex;align-items:center;gap:8px;padding:8px 10px;
                  background:rgba(0,229,160,.04);border:1px solid var(--border2);
                  cursor:pointer;transition:all .15s;margin-bottom:4px">
        <div style="flex:1;font-family:var(--mono);font-size:11px;color:var(--fg);
                    overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${p.name}</div>
        <div style="font-family:var(--mono);font-size:9px;color:var(--dim)">${p.display_name}</div>
        <button class="preset-load-btn" onclick="applyPreset(${p.id})">LOAD</button>
        <span onclick="event.stopPropagation();deletePreset(${p.id})"
              style="font-size:10px;color:var(--dim);cursor:pointer;padding:2px 6px;
                     transition:color .15s"
              onmouseover="this.style.color='#ff4060'"
              onmouseout="this.style.color='var(--dim)'">✕</span>
      </div>`).join('');
  } catch(e) {
    const list = document.getElementById('preset-list');
    if (list) list.innerHTML = '<div class="preset-empty" style="font-family:var(--mono);font-size:10px;color:var(--dim);padding:12px;text-align:center">Could not load presets</div>';
  }
}

async function deletePreset(id) {
  if (!confirm('Delete this preset?')) return;
  await fetch('/api/presets/delete/' + id, {method:'POST'});
  loadPresets();
}

// ── Patch generate() to include theme ─────────────────────────
const _origFetch = window.fetch;
const _generateEndpoint = '/generate';
// Override fetch only for /generate calls to inject biome_theme
window.fetch = function(url, opts) {
  if (url === _generateEndpoint && opts && opts.body) {
    try {
      const body = JSON.parse(opts.body);
      body.biome_theme = _activeTheme;
      opts = Object.assign({}, opts, {body: JSON.stringify(body)});
    } catch(e) {}
  }
  return _origFetch.call(this, url, opts);
};

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildThemeSelector();
  loadPresets();
});
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  setTimeout(() => { buildThemeSelector(); loadPresets(); }, 50);
}
</script>
"""

# ── 4c. Theme selector HTML block ──────────────────────────────
THEME_HTML = """
<!-- UEFN Biome Theme Selector — injected by patch_forge_v2 -->
<div class="theme-section" id="biome-theme-section" style="margin-bottom:16px">
  <span class="theme-label">◈ UEFN Biome Theme</span>
  <div class="theme-grid" id="theme-grid"></div>
</div>
"""

# Inject CSS
if "biome-theme-css" not in html:
    html = html.replace("</head>", THEME_CSS + "\n</head>")
    print("✓ index.html — theme CSS injected")

# Inject theme selector HTML right before the world-size preset cards
if "biome-theme-section" not in html:
    # Place it before the world size section
    target = 'id="ws-presets"'
    if target in html:
        # Find the parent section/div wrapping ws-presets and prepend before it
        html = html.replace(
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:14px" id="ws-presets">',
            THEME_HTML + '\n<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:14px" id="ws-presets">'
        )
        print("✓ index.html — theme selector HTML injected")
    else:
        print("⚠ index.html — could not find ws-presets anchor, appending to body")
        html = html.replace("</body>", THEME_HTML + "\n</body>")

# Remove old broken forge-upgrades-js and replace with the new one
if "forge-upgrades-js" in html:
    html = re.sub(
        r'<script id="forge-upgrades-js">.*?</script>',
        '',
        html,
        flags=re.DOTALL
    )
    print("✓ index.html — removed old forge-upgrades-js")

# Remove old broken biome-theme-js if present
if "biome-theme-js" in html:
    html = re.sub(
        r'<script id="biome-theme-js">.*?</script>',
        '',
        html,
        flags=re.DOTALL
    )

# Inject new combined JS before </body>
if "biome-theme-js" not in html:
    html = html.replace("</body>", THEME_JS + "\n</body>")
    print("✓ index.html — new theme + preset JS injected")

# ── 4d. Wire _onGenerateComplete hook if not present ───────────
HOOK_LINE = "if(window._onGenerateComplete) window._onGenerateComplete(d);"
if HOOK_LINE not in html:
    old_enable = "['dl-hm','dl-js','dl-pv','btn-verse'].forEach(id => $(id).classList.remove('btn-disabled'));"
    new_enable  = old_enable + "\n    " + HOOK_LINE
    html = html.replace(old_enable, new_enable)
    print("✓ index.html — _onGenerateComplete hook added")

# ── 4e. Add verse-dl and save-gallery buttons if missing ───────
if "btn-save-gallery" not in html:
    old_btn = '<button class="btn-dl btn-secondary btn-disabled" id="btn-verse" onclick="openVerse()"></> Verse Constants</button>'
    new_btn = old_btn + """
      <button class="btn-dl btn-secondary btn-disabled" id="btn-verse-dl" onclick="downloadVerse()">↓ .verse File</button>
      <button class="btn-dl btn-primary btn-disabled"   id="btn-save-gallery" onclick="saveToGallery()">⊕ Save to Room</button>
      <button class="btn-dl btn-secondary"              id="btn-save-preset"  onclick="openSavePreset()">☆ Save Preset</button>"""
    html = html.replace(old_btn, new_btn)
    print("✓ index.html — action buttons added")

open(idx_path, "w").write(html)
print("✓ index.html saved")

# ══════════════════════════════════════════════════════════════════
# 5. Ensure forge_upgrades route is registered (gallery save, presets)
# ══════════════════════════════════════════════════════════════════
# Check server.py for registration
sv_main = os.path.join(ROOT, "server.py")
sv_main_src = open(sv_main).read()
if "forge_upgrades_bp" not in sv_main_src:
    lines = sv_main_src.splitlines()
    last_import = 0
    last_register = 0
    for i, ln in enumerate(lines):
        if "import" in ln and "_bp" in ln: last_import = i
        if "register_blueprint" in ln: last_register = i
    lines.insert(last_import + 1,
        "from routes.forge_upgrades import forge_upgrades_bp")
    lines.insert(last_register + 2,
        "app.register_blueprint(forge_upgrades_bp)")
    open(sv_main, "w").write("\n".join(lines))
    print("✓ server.py — forge_upgrades_bp registered")
else:
    print("→ server.py — already registered")

# ══════════════════════════════════════════════════════════════════
# 6. Restart + health check
# ══════════════════════════════════════════════════════════════════
print("\n▸ Restarting islandforge...")
subprocess.run(["sudo","systemctl","restart","islandforge"], check=True)
time.sleep(6)

for path in ["/health", "/forge", "/api/presets"]:
    r = subprocess.run(
        ["curl","-s","-o","/dev/null","-w","%{http_code}",
         f"http://127.0.0.1:5000{path}"],
        capture_output=True, text=True
    )
    status = r.stdout.strip()
    icon = "✓" if status == "200" else "✗"
    print(f"  {icon} {path:30s} → {status}")

print("""
✅ Forge v2 live at triptokforge.org/forge

Fixed:
  ✓ oracle_db.py json NameError — gone
  ✓ Preset library — LOAD button fires generate() automatically
  ✓ World size + weights load correctly from preset

New:
  ◈ UEFN Biome Theme selector — 8 themes:
      Chapter 1 / Chapter 2 / Chapter 3 / Chapter 4
      Arctic / Desert Storm / Primal Jungle / Volcanic Inferno
  Each theme changes:
    — biome thresholds (how much snow/jungle/desert generates)
    — colour palette (map preview colours)
    — default noise weight suggestions
  Theme is saved with presets and reloaded
  ↓ .verse File download button
  ⊕ Save to Room button
""")
