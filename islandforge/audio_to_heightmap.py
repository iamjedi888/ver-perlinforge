"""
audio_to_heightmap.py  —  Island Forge v3.0
============================================
v3.0 — Fortnite-realistic terrain:
  - Mostly flat playable zones (60-70% of map is gentle terrain)
  - Distinct POI landing pads — deliberate raised/lowered zones
  - Coastal cliff walls with flat interior tops
  - Asymmetric mountain ridges — one steep face, one gentle slope
  - Wide shallow river valleys (not gorges)
  - Large contiguous biome zones (quarter-map scale)
  - Storm-funnel terrain — natural bowl toward center
  - Audio drives STYLE not just intensity:
      sub_bass  → number + scale of mountain ridges
      bass      → how hilly the flatlands are
      midrange  → number of POIs and their elevation contrast
      presence  → coastal cliff ruggedness
      brilliance→ surface detail / rocky outcrops
      bpm       → island shape (slow=wide/open, fast=complex/fractured)

WORLD SIZE PRESETS  (pass --world_size to CLI, or world_size_cm to build_layout)
──────────────────────────────────────────────────────────────────────────────────
  "uefn_small"   →    50,000 cm  (  500m ×   500m)  UEFN default island
  "uefn_max"     →   100,000 cm  (    1km ×     1km)  UEFN creative max
  "br_chapter2"  →   550,000 cm  (  5.5km ×   5.5km)  Fortnite BR Chapter 2
  "double_br"    → 1,100,000 cm  (   11km ×    11km)  DEFAULT — 2× BR map
  "skyrim"       → 3,700,000 cm  (   37km ×    37km)  approx. Skyrim landmass
  "gta5"         → 8,100,000 cm  (   81km ×    81km)  approx. GTA V map
  Or pass any integer in cm directly.

⚠️  UEFN IMPORT WARNING  ────────────────────────────────────────────────────────
  Current UEFN landscape import guidance is a maximum 2048×2048 vertices
  (or equivalent), which maps cleanly to a 2017×2017 square heightmap export.
  If the island exceeds ~100,000 cm (1km) on its widest axis, plan for
  streaming / World Partition workflow before import:
    UEFN → Edit → Project Settings → World → Enable World Partition
    Then: World Settings → Enable Streaming
  For Battle Royale scale and above, also set:
    Landscape → Section Size: 63×63 quads
    Landscape → Sections Per Component: 2×2
    Recommended heightmap resolution for double_br: 2017×2017 px
─────────────────────────────────────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────────────────────
# WORLD SIZE PRESETS
# ─────────────────────────────────────────────────────────────

WORLD_SIZE_PRESETS = {
    "uefn_small":  50_000,      #   500m ×   500m — UEFN default island
    "uefn_max":   100_000,      #     1km ×     1km — UEFN creative max
    "br_chapter2": 550_000,     #   5.5km ×   5.5km — Fortnite BR Chapter 2
    "double_br":  1_100_000,    #    11km ×    11km — DEFAULT (2× BR map)
    "skyrim":     3_700_000,    #    37km ×    37km — approx. Skyrim
    "gta5":       8_100_000,    #    81km ×    81km — approx. GTA V
}

# Default world size — 2× the Fortnite BR map, requires streaming / partition prep
DEFAULT_WORLD_SIZE_CM = WORLD_SIZE_PRESETS["double_br"]  # 1,100,000 cm

# Current direct UEFN square landscape lane tops out at 2017 (2048-equivalent guidance).
UEFN_DIRECT_IMPORT_MAX_PX = 2017
UEFN_STREAMING_THRESHOLD_CM = WORLD_SIZE_PRESETS["uefn_max"]

# Recommended UEFN-facing heightmap resolutions per size preset.
RECOMMENDED_HEIGHTMAP_SIZE = {
    "uefn_small":   505,
    "uefn_max":    1009,
    "br_chapter2": 1009,
    "double_br":   2017,   # ~54cm/px at 11km — good detail
    "skyrim":      2017,   # keep export inside current direct UEFN square limit
    "gta5":        2017,   # keep export inside current direct UEFN square limit
}

import argparse, json, math, os, sys
import numpy as np
from verse_export_generator import integrate_with_forge  # ✅ NEW IMPORT
from PIL import Image
from scipy.ndimage import gaussian_filter, label

# ─────────────────────────────────────────────────────────────
# NOISE PRIMITIVES
# ─────────────────────────────────────────────────────────────

def make_permutation(seed):
    rng = np.random.default_rng(seed)
    p = np.arange(256, dtype=np.int32)
    rng.shuffle(p)
    return np.tile(p, 2)

def fade(t): return t*t*t*(t*(t*6-15)+10)
def lerp(a,b,t): return a+t*(b-a)

def grad(h,x,y):
    h=h&3
    u=np.where(h<2,x,y); v=np.where(h<2,y,x)
    return np.where(h&1,-u,u)+np.where(h&2,-v,v)

def perlin2d(x,y,perm):
    xi=x.astype(int)&255; yi=y.astype(int)&255
    xf=x-np.floor(x); yf=y-np.floor(y)
    u=fade(xf); v=fade(yf)
    aa=perm[perm[xi]+yi]; ab=perm[perm[xi]+yi+1]
    ba=perm[perm[xi+1]+yi]; bb=perm[perm[xi+1]+yi+1]
    x1=lerp(grad(aa,xf,yf),grad(ba,xf-1,yf),u)
    x2=lerp(grad(ab,xf,yf-1),grad(bb,xf-1,yf-1),u)
    return lerp(x1,x2,v)

def octave_noise(size, octaves, persistence, lacunarity, scale, seed):
    perm = make_permutation(seed)
    result = np.zeros((size, size), dtype=np.float32)
    amp=1.0; freq=1.0; maxv=0.0
    lin = np.linspace(0, scale, size, endpoint=False, dtype=np.float32)
    xs, ys = np.meshgrid(lin, lin)
    for _ in range(octaves):
        result += amp * perlin2d(xs*freq, ys*freq, perm)
        maxv += amp; amp *= persistence; freq *= lacunarity
    return (result / maxv).astype(np.float32, copy=False)

def nn(size, oct, per, lac, scale, seed):
    """Normalised noise 0..1"""
    n = octave_noise(size, oct, per, lac, scale, seed)
    lo,hi = n.min(), n.max()
    return ((n-lo)/(hi-lo+1e-9)).astype(np.float32, copy=False)

# ─────────────────────────────────────────────────────────────
# AUDIO ANALYSIS
# ─────────────────────────────────────────────────────────────

def analyse_audio(path):
    """Return frequency band weights from an audio file."""
    try:
        import librosa
        y, sr = librosa.load(path, sr=22050, mono=True, duration=120)
        S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

        def band_energy(lo, hi):
            mask = (freqs >= lo) & (freqs < hi)
            if not mask.any(): return 0.0
            e = float(np.mean(S[mask]))
            return e

        raw = {
            "sub_bass":  band_energy(20,   80),
            "bass":      band_energy(80,   250),
            "midrange":  band_energy(250,  2000),
            "presence":  band_energy(2000, 6000),
            "brilliance":band_energy(6000, 20000),
        }
        mx = max(raw.values()) or 1.0
        weights = {k: min(1.0, v/mx) for k,v in raw.items()}

        # Tempo
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        weights["tempo_bpm"] = float(np.atleast_1d(tempo)[0]) if tempo is not None else 120.0
        weights["duration_s"] = float(len(y)/sr)
        return weights

    except Exception as e:
        print(f"[audio] {e} — using defaults")
        return {"sub_bass":0.5,"bass":0.5,"midrange":0.5,
                "presence":0.5,"brilliance":0.3,"tempo_bpm":120.0,"duration_s":0.0}

# ─────────────────────────────────────────────────────────────
# ISLAND MASK  — coastal cliffs, bays, peninsulas
# ─────────────────────────────────────────────────────────────

def build_island_mask(size, seed, presence, bpm=120.0):
    """
    Returns a 0..1 mask where:
      0 = deep ocean
      0..0.4 = shallow / beach transition
      0.4..1 = inland
    Coastal shape complexity driven by presence + bpm.
    """
    rng = np.random.default_rng(seed + 9000)
    cy, cx = size//2, size//2
    ys = np.arange(size); xs = np.arange(size)
    YY, XX = np.meshgrid(ys, xs, indexing='ij')

    # Base ellipse — slower bpm = wider, rounder; faster = more elongated
    # Larger radii so land fills ~45-50% of map (Fortnite-realistic)
    bpm_t = np.clip((bpm - 60) / 120, 0, 1)
    rx = size * (0.47 + 0.04 * (1 - bpm_t))
    ry = size * (0.45 + 0.05 * bpm_t)
    angle = rng.uniform(0, math.pi)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    dx = (XX - cx) * cos_a + (YY - cy) * sin_a
    dy = -(XX - cx) * sin_a + (YY - cy) * cos_a
    base_mask = 1.0 - np.clip(np.sqrt((dx/rx)**2 + (dy/ry)**2), 0, 1)

    # Large warp — creates bays and peninsulas
    warp_scale = 0.8 + presence * 0.6
    warp_oct   = 3
    wx = nn(size, warp_oct, 0.5, 2.0, warp_scale, seed+1) - 0.5
    wy = nn(size, warp_oct, 0.5, 2.0, warp_scale, seed+2) - 0.5
    warp_strength = size * (0.08 + presence * 0.10)
    YW = np.clip((YY + wy * warp_strength).astype(int), 0, size-1)
    XW = np.clip((XX + wx * warp_strength).astype(int), 0, size-1)
    mask = base_mask[YW, XW]

    # Fine coastal detail
    coast_noise = nn(size, 4, 0.6, 2.2, 1.5 + presence, seed+3) - 0.5
    mask += coast_noise * 0.06 * presence

    # Smooth and normalise
    mask = gaussian_filter(mask, sigma=size*0.015)
    lo, hi = mask.min(), mask.max()
    mask = (mask - lo) / (hi - lo + 1e-9)
    return np.clip(mask, 0, 1).astype(np.float32, copy=False)

# ─────────────────────────────────────────────────────────────
# FORTNITE-STYLE BASE TERRAIN
# ─────────────────────────────────────────────────────────────

def build_fortnite_terrain(size, seed, w, island_mask, terrain_profile=None):
    """
    Builds terrain that mimics Fortnite map structure:
    - Large flat interior bowl (natural storm funnel)
    - Coastal ridge / cliff shelf
    - 1-3 mountain ridges (asymmetric)
    - Gently rolling flatlands between them
    - Audio weights shape the style
    """
    rng = np.random.default_rng(seed + 100)
    terrain_profile = terrain_profile or {}
    basin_scale = float(terrain_profile.get("basin", 1.0))
    hill_scale = float(terrain_profile.get("hills", 1.0))
    coast_scale = float(terrain_profile.get("coast", 1.0))
    ridge_scale = float(terrain_profile.get("ridges", 1.0))
    detail_scale = float(terrain_profile.get("detail", 1.0))
    sub_bass   = w.get("sub_bass",   0.5)
    bass       = w.get("bass",       0.5)
    presence   = w.get("presence",   0.5)
    brilliance = w.get("brilliance", 0.3)

    cy, cx = size // 2, size // 2
    ys = np.arange(size); xs = np.arange(size)
    YY, XX = np.meshgrid(ys, xs, indexing='ij')
    dist_center = np.sqrt(((YY-cy)/size)**2 + ((XX-cx)/size)**2) * 2
    dist_center = np.clip(dist_center, 0, 1)

    # ── Layer 1: Interior bowl (Fortnite always has playable flat center)
    # Center is lower, edges of inland area rise to coastal ridges
    bowl = dist_center * 0.35 * basin_scale
    bowl = gaussian_filter(bowl, sigma=size*0.06)

    # ── Layer 2: Gentle rolling hills over flatlands
    # bass controls hilliness of playable area
    hills = nn(size, 4, 0.55, 2.0, 1.5 + bass * 1.5, seed+10)
    hills = gaussian_filter(hills, sigma=size*0.04)
    # Keep hills gentle — flatten the amplitude
    hills = hills * (0.12 + bass * 0.10) * hill_scale

    # ── Layer 3: Coastal cliff shelf
    # Inner land is raised relative to water, creating natural cliffs at coast
    # island_mask already gives us the coastal gradient
    coast_shelf = np.clip((island_mask - 0.35) * 3, 0, 1)
    coast_shelf = gaussian_filter(coast_shelf ** 0.7, sigma=size*0.025)
    coast_shelf *= (0.18 + presence * 0.15) * coast_scale

    # ── Layer 4: Mountain ridges (sub_bass driven)
    # Fortnite has 1-3 distinct ridges, not scattered peaks
    n_ridges = max(1, min(4, int(round((1 + sub_bass * 2.5) * ridge_scale))))
    ridge_terrain = np.zeros((size, size), dtype=np.float32)

    for i in range(n_ridges):
        # Each ridge is a directional noise band
        ridge_angle = rng.uniform(0, math.pi)
        cos_r, sin_r = math.cos(ridge_angle), math.sin(ridge_angle)
        # Rotated coordinates
        dxr = (XX - cx) * cos_r + (YY - cy) * sin_r
        dyr = -(XX - cx) * sin_r + (YY - cy) * cos_r

        # Ridge placement — offset from center
        ridge_offset_x = rng.uniform(-0.2, 0.2) * size
        ridge_offset_y = rng.uniform(-0.15, 0.15) * size

        # Ridge cross-section: steep one side, gentle other (asymmetric!)
        ridge_pos = dxr - ridge_offset_x
        ridge_width = size * (0.08 + sub_bass * 0.06)
        # Asymmetric profile: tanh for steep face, gaussian for gentle slope
        steep_side  = np.exp(-np.maximum(0, ridge_pos)**2 / (2*(ridge_width*0.6)**2))
        gentle_side = np.exp(-np.maximum(0, -ridge_pos)**2 / (2*(ridge_width*1.4)**2))
        ridge_profile = steep_side * 0.7 + gentle_side * 0.3

        # Ridge height variation along length (not uniform — has high/low points)
        ridge_noise = nn(size, 3, 0.6, 2.0, 2.0, seed+20+i*7)
        ridge_blend = ridge_profile * (0.5 + ridge_noise * 0.5)

        # Keep ridges only on land
        ridge_blend *= np.clip(island_mask * 2 - 0.4, 0, 1)
        ridge_blend = gaussian_filter(ridge_blend, sigma=size*0.02)

        ridge_height = (0.30 + sub_bass * 0.20) * ridge_scale
        ridge_terrain += ridge_blend * ridge_height / n_ridges

    # ── Layer 5: Fine surface detail (brilliance driven)
    detail = nn(size, 5, 0.5, 2.1, 3.0 + brilliance*2, seed+30)
    detail = gaussian_filter(detail, sigma=size*0.005)
    detail = (detail - 0.5) * (0.04 + brilliance * 0.04) * detail_scale

    # ── Combine
    terrain = bowl + hills + coast_shelf + ridge_terrain + detail

    # Normalise to 0..1
    terrain = np.clip(terrain, 0, None)
    lo, hi = terrain.min(), terrain.max()
    terrain = (terrain - lo) / (hi - lo + 1e-9)

    # Apply island mask — ocean is 0
    # Use a smooth step so coast doesn't have a hard line
    land_fade = np.clip((island_mask - 0.25) / 0.25, 0, 1)
    land_fade = land_fade ** 1.5  # sharpen the coastal cliff
    terrain = terrain * land_fade

    return terrain.astype(np.float32, copy=False)

# ─────────────────────────────────────────────────────────────
# POI LANDING PADS
# ─────────────────────────────────────────────────────────────

def inject_pois(terrain, island_mask, size, seed, midrange=0.5, n_pois=None, poi_scale=1.0):
    """
    Flatten circular areas for POIs (named locations).
    Some are raised (hilltop town), some are lowered (valley village).
    Returns terrain + list of POI centers.
    """
    rng = np.random.default_rng(seed + 5000)
    if n_pois is None:
        n_pois = max(2, min(9, int(round((3 + midrange * 4) * poi_scale))))  # 2-9 POIs

    cy, cx = size // 2, size // 2
    land_mask = island_mask > 0.45  # only place POIs well inside coast

    poi_centers = []
    max_attempts = 200
    min_poi_sep  = size * 0.18

    for _ in range(n_pois):
        for attempt in range(max_attempts):
            # Bias placement toward middle ring (not too central, not too coastal)
            r   = rng.uniform(0.10, 0.38) * size
            ang = rng.uniform(0, 2 * math.pi)
            py  = int(cy + r * math.sin(ang))
            px  = int(cx + r * math.cos(ang))
            py  = np.clip(py, 0, size-1)
            px  = np.clip(px, 0, size-1)

            if not land_mask[py, px]:
                continue

            # Check separation from existing POIs
            too_close = any(
                math.hypot(py-ey, px-ex) < min_poi_sep
                for ey, ex in poi_centers
            )
            if too_close:
                continue

            poi_centers.append((py, px))
            break

    # Flatten each POI area
    YY, XX = np.meshgrid(np.arange(size), np.arange(size), indexing='ij')
    for (py, px) in poi_centers:
        # POI radius — varies with midrange
        poi_r = size * (0.04 + midrange * 0.025) * max(0.82, min(1.18, poi_scale))
        dist  = np.sqrt((YY-py)**2 + (XX-px)**2)
        blend = np.clip(1 - dist / poi_r, 0, 1) ** 2

        # Target elevation — some POIs raised, some lowered
        current_elev = terrain[py, px]
        # Raised POI: +0.08 to +0.15, Lowered POI: -0.05 to -0.10
        if rng.random() > 0.35:
            target = np.clip(current_elev + rng.uniform(0.06, 0.14), 0.1, 0.75)
        else:
            target = np.clip(current_elev - rng.uniform(0.04, 0.08), 0.02, 0.4)

        terrain = terrain * (1 - blend) + target * blend

    return terrain, poi_centers

# ─────────────────────────────────────────────────────────────
# RIVERS  — wide shallow valleys
# ─────────────────────────────────────────────────────────────

def simulate_rivers(terrain, island_mask, size, seed, midrange=0.5, river_scale=1.0):
    """
    Fortnite rivers are wide, shallow, and navigable.
    They flow from high ground toward coast in gentle curves.
    """
    rng = np.random.default_rng(seed + 3000)
    n_rivers = max(1, min(6, int(round((1 + midrange * 3) * river_scale))))

    for _ in range(n_rivers):
        # Start from upper third of terrain on land
        land = island_mask > 0.5
        high = (terrain > 0.45) & land
        candidates = np.argwhere(high)
        if len(candidates) == 0:
            continue
        idx = rng.integers(0, len(candidates))
        ry, rx = candidates[idx]

        path = [(ry, rx)]
        visited = set()
        visited.add((ry, rx))

        # Flow downhill with some meandering
        for step in range(400):
            cy_r, cx_r = path[-1]
            # 3x3 neighbourhood — find lowest unvisited
            best_val = terrain[cy_r, cx_r]
            best_pos = None
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ny = np.clip(cy_r+dy, 0, size-1)
                    nx = np.clip(cx_r+dx, 0, size-1)
                    if (ny,nx) not in visited and terrain[ny,nx] < best_val - 0.002:
                        best_val = terrain[ny,nx]
                        best_pos = (ny, nx)
            if best_pos is None:
                break
            if island_mask[best_pos] < 0.25:
                break
            path.append(best_pos)
            visited.add(best_pos)

        if len(path) < 20:
            continue

        # Carve river — wide and shallow
        river_width  = size * (0.018 + midrange * 0.012) * max(0.75, min(1.35, river_scale))
        river_depth  = 0.045  # very shallow
        YY, XX = np.meshgrid(np.arange(size), np.arange(size), indexing='ij')

        # Sample every N steps for performance
        for i in range(0, len(path), 3):
            py, px = path[i]
            dist = np.sqrt((YY-py)**2 + (XX-px)**2)
            # Wide smooth valley profile
            blend = np.clip(1 - dist / river_width, 0, 1) ** 1.5
            target = np.clip(terrain[py,px] - river_depth, 0.01, 1)
            terrain = terrain * (1 - blend * 0.6) + target * blend * 0.6

    return terrain

# ─────────────────────────────────────────────────────────────
# ROADS  — flat paths between POIs
# ─────────────────────────────────────────────────────────────

def build_roads(terrain, size, poi_centers, seed):
    """Connect POIs with roads — flat, slightly recessed paths."""
    if len(poi_centers) < 2:
        return terrain, np.zeros((size,size), dtype=bool)

    road_mask = np.zeros((size,size), dtype=bool)
    rng = np.random.default_rng(seed + 8000)
    road_width = max(3, size // 100)

    YY, XX = np.meshgrid(np.arange(size), np.arange(size), indexing='ij')

    # Connect each POI to nearest neighbour
    connected = {0}
    remaining = set(range(1, len(poi_centers)))

    while remaining:
        best_dist = 1e9
        best_i = best_j = -1
        for i in connected:
            for j in remaining:
                py1,px1 = poi_centers[i]
                py2,px2 = poi_centers[j]
                d = math.hypot(py2-py1, px2-px1)
                if d < best_dist:
                    best_dist = d; best_i = i; best_j = j
        if best_i < 0:
            break

        connected.add(best_j)
        remaining.discard(best_j)

        # Draw road segment
        py1,px1 = poi_centers[best_i]
        py2,px2 = poi_centers[best_j]
        steps = max(int(best_dist * 1.5), 40)
        for s in range(steps+1):
            t = s / steps
            # Slight curve via midpoint offset
            mid_offset_y = rng.uniform(-0.06, 0.06) * size * math.sin(t * math.pi)
            mid_offset_x = rng.uniform(-0.06, 0.06) * size * math.sin(t * math.pi)
            ry = int(np.clip(py1 + (py2-py1)*t + mid_offset_y, 0, size-1))
            rx = int(np.clip(px1 + (px2-px1)*t + mid_offset_x, 0, size-1))
            dist = np.sqrt((YY-ry)**2 + (XX-rx)**2)
            blend = np.clip(1 - dist / road_width, 0, 1) ** 2
            road_elev = terrain[ry, rx]
            terrain = terrain * (1-blend*0.8) + road_elev * blend * 0.8
            road_mask |= (blend > 0.4)

    return terrain, road_mask

# ─────────────────────────────────────────────────────────────
# GENERATE TERRAIN  — main entry
# ─────────────────────────────────────────────────────────────

def generate_terrain(size, seed, weights, water_level=0.20, theme_name="chapter1"):
    """
    Full Fortnite-style terrain generation pipeline.
    Returns (height_array 0..1, road_mask bool array).
    """
    w          = weights
    sub_bass   = w.get("sub_bass",   0.5)
    midrange   = w.get("midrange",   0.5)
    presence   = w.get("presence",   0.5)
    bpm        = w.get("tempo_bpm",  120.0)

    theme = get_theme(theme_name)
    terrain_profile = theme.get("terrain_profile", {})

    # 1. Island mask
    island_mask = build_island_mask(size, seed, presence, bpm)

    # 2. Base terrain
    terrain = build_fortnite_terrain(size, seed, w, island_mask, terrain_profile=terrain_profile)

    # 3. POI landing pads
    terrain, poi_centers = inject_pois(
        terrain,
        island_mask,
        size,
        seed,
        midrange,
        poi_scale=float(terrain_profile.get("pois", 1.0)),
    )

    # 4. Rivers
    terrain = simulate_rivers(
        terrain,
        island_mask,
        size,
        seed,
        midrange,
        river_scale=float(terrain_profile.get("rivers", 1.0)),
    )

    # 5. Roads between POIs
    terrain, road_mask = build_roads(terrain, size, poi_centers, seed)

    # 6. Final smooth pass — remove jaggies, keep landforms
    terrain = gaussian_filter(terrain, sigma=size * 0.003)

    # 7. Clip ocean to exactly 0
    terrain[island_mask < 0.25] = 0.0

    # 8. Normalise + elevation compression for Fortnite-style flat playspace
    land_px = island_mask > 0.25
    if land_px.any():
        lo, hi = terrain[land_px].min(), terrain[land_px].max()
        terrain[land_px] = (terrain[land_px] - lo) / (hi - lo + 1e-9)
        # Compress elevation curve: flatten the middle, keep peaks dramatic
        # Most terrain (50th-80th pct) should be in 0.25-0.50 range
        t = terrain[land_px]
        # Power curve that pulls midrange down but keeps peaks
        compressed = np.where(t < 0.7,
            water_level + 0.01 + (t ** 1.6) * 0.55,
            water_level + 0.01 + 0.55 + (t - 0.7) * 1.5)
        terrain[land_px] = np.clip(compressed, water_level + 0.01, 1.0)

    return np.clip(terrain, 0, 1).astype(np.float32, copy=False), road_mask

# ─────────────────────────────────────────────────────────────
# MOISTURE + BIOMES
# ─────────────────────────────────────────────────────────────

def generate_moisture(size, seed):
    return nn(size, 4, 0.5, 2.0, 2.0, seed + 999).astype(np.float32, copy=False)

# Biome IDs
BIOME_WATER    = 0
BIOME_BEACH    = 1
BIOME_PLAINS   = 2
BIOME_FOREST   = 3
BIOME_JUNGLE   = 4
BIOME_SNOW     = 5
BIOME_DESERT   = 6
BIOME_HIGHLAND = 7
BIOME_PEAK     = 8
BIOME_FARM     = 9

BIOME_NAMES = {
    0:"Water", 1:"Beach", 2:"Plains", 3:"Forest",
    4:"Jungle", 5:"Snow", 6:"Desert", 7:"Highland",
    8:"Peak", 9:"Farm",
}

BIOME_COLOURS = {
    0: (20,  60, 120),   # deep blue water
    1: (210,190,140),    # sandy beach
    2: (130,170, 80),    # green plains
    3: ( 60,110, 55),    # dark forest
    4: ( 30, 90, 40),    # dense jungle
    5: (220,235,245),    # snow
    6: (195,165, 90),    # desert
    7: ( 90,110, 75),    # highland
    8: (200,200,210),    # rocky peak
    9: (160,190, 80),    # farm (bright green)
}


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
        "label":        "Desert Storm",
        "description":  "Arid wasteland. Sand seas, scorched rock, zero snow. Oasis patches only.",
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


# Official Fortnite-inspired chapter and climate models.
# This overrides the older placeholder theme table above with
# stronger macro-biome direction and terrain-shape defaults.
UEFN_THEMES = {
    "chapter1": {
        "label": "Chapter 1 - Athena",
        "description": "Classic Battle Royale mix: temperate core, one frosted corner, one arid accent, and broad readable POI space.",
        "water_level": 0.20,
        "moisture_jungle": 0.67,
        "moisture_forest": 0.44,
        "moisture_desert": 0.32,
        "moisture_snow": 0.35,
        "zone_desert": 0.58,
        "zone_snow": 0.44,
        "highland_min": 0.65,
        "peak_min": 0.82,
        "zone_seed": 42,
        "biome_bias": {"plains": 0.18, "forest": 0.10, "jungle": -0.12, "snow": 0.05, "desert": 0.02},
        "terrain_profile": {"basin": 1.00, "hills": 0.95, "coast": 1.00, "ridges": 1.00, "rivers": 0.90, "pois": 1.00, "detail": 0.90},
        "land_biome_targets": {"plains": 0.36, "forest": 0.25, "snow": 0.11, "desert": 0.08, "highland": 0.13, "peak": 0.07},
        "macro_regions": [
            {"biome": "forest", "x": 0.34, "y": 0.38, "radius": 0.28, "strength": 0.56},
            {"biome": "snow", "x": 0.20, "y": 0.80, "radius": 0.22, "strength": 0.78},
            {"biome": "desert", "x": 0.80, "y": 0.72, "radius": 0.18, "strength": 0.48},
        ],
        "colours": {0: (20, 60, 120), 1: (210, 190, 140), 2: (130, 170, 80), 3: (60, 110, 55), 4: (30, 90, 40), 5: (220, 235, 245), 6: (195, 165, 90), 7: (90, 110, 75), 8: (200, 200, 210), 9: (160, 190, 80)},
        "weights": {"sub_bass": 0.56, "bass": 0.49, "midrange": 0.52, "presence": 0.42, "brilliance": 0.30},
    },
    "chapter2": {
        "label": "Chapter 2 - Apollo",
        "description": "River-cut temperate island with wetter lowlands, stronger coastline travel, and restrained snow or desert accents.",
        "water_level": 0.24,
        "moisture_jungle": 0.56,
        "moisture_forest": 0.39,
        "moisture_desert": 0.23,
        "moisture_snow": 0.30,
        "zone_desert": 0.63,
        "zone_snow": 0.38,
        "highland_min": 0.68,
        "peak_min": 0.84,
        "zone_seed": 118,
        "biome_bias": {"plains": 0.14, "forest": 0.15, "jungle": 0.07, "snow": -0.06, "desert": -0.10},
        "terrain_profile": {"basin": 1.05, "hills": 0.90, "coast": 0.95, "ridges": 0.86, "rivers": 1.24, "pois": 0.96, "detail": 0.82},
        "land_biome_targets": {"plains": 0.37, "forest": 0.29, "jungle": 0.11, "snow": 0.05, "highland": 0.12, "peak": 0.06},
        "macro_regions": [
            {"biome": "forest", "x": 0.40, "y": 0.38, "radius": 0.30, "strength": 0.54},
            {"biome": "jungle", "x": 0.18, "y": 0.68, "radius": 0.21, "strength": 0.50},
            {"biome": "snow", "x": 0.82, "y": 0.18, "radius": 0.15, "strength": 0.28},
        ],
        "colours": {0: (15, 50, 105), 1: (200, 180, 130), 2: (110, 155, 65), 3: (50, 100, 45), 4: (25, 80, 35), 5: (215, 230, 240), 6: (180, 155, 80), 7: (80, 100, 65), 8: (190, 195, 205), 9: (150, 180, 70)},
        "weights": {"sub_bass": 0.60, "bass": 0.56, "midrange": 0.44, "presence": 0.53, "brilliance": 0.24},
    },
    "chapter3": {
        "label": "Chapter 3 - Artemis",
        "description": "A wider flipped island with a strong snow sector, visible ridgelines, and open plains supporting long traversal routes.",
        "water_level": 0.18,
        "moisture_jungle": 0.72,
        "moisture_forest": 0.51,
        "moisture_desert": 0.27,
        "moisture_snow": 0.44,
        "zone_desert": 0.66,
        "zone_snow": 0.35,
        "highland_min": 0.60,
        "peak_min": 0.78,
        "zone_seed": 233,
        "biome_bias": {"plains": 0.12, "forest": 0.02, "jungle": -0.10, "snow": 0.14, "desert": 0.00},
        "terrain_profile": {"basin": 0.96, "hills": 1.04, "coast": 1.00, "ridges": 1.12, "rivers": 1.08, "pois": 1.00, "detail": 0.98},
        "land_biome_targets": {"plains": 0.30, "forest": 0.21, "snow": 0.19, "desert": 0.08, "highland": 0.14, "peak": 0.08},
        "macro_regions": [
            {"biome": "snow", "x": 0.18, "y": 0.26, "radius": 0.28, "strength": 0.84},
            {"biome": "forest", "x": 0.78, "y": 0.34, "radius": 0.24, "strength": 0.40},
            {"biome": "desert", "x": 0.64, "y": 0.80, "radius": 0.20, "strength": 0.34},
        ],
        "colours": {0: (25, 65, 130), 1: (215, 200, 155), 2: (140, 178, 90), 3: (65, 115, 60), 4: (35, 95, 45), 5: (230, 240, 250), 6: (190, 160, 85), 7: (95, 118, 82), 8: (210, 215, 225), 9: (165, 195, 85)},
        "weights": {"sub_bass": 0.44, "bass": 0.34, "midrange": 0.60, "presence": 0.58, "brilliance": 0.48},
    },
    "chapter4": {
        "label": "Chapter 4 - Asteria",
        "description": "High-contrast island inspired by MEGA and Wilds: autumnal highlands, a neon southeast, and a jungle-crater accent instead of desert sprawl.",
        "water_level": 0.18,
        "moisture_jungle": 0.59,
        "moisture_forest": 0.43,
        "moisture_desert": 0.25,
        "moisture_snow": 0.31,
        "zone_desert": 0.71,
        "zone_snow": 0.34,
        "highland_min": 0.57,
        "peak_min": 0.75,
        "zone_seed": 314,
        "biome_bias": {"plains": 0.10, "forest": 0.08, "jungle": 0.10, "snow": -0.08, "desert": -0.18},
        "terrain_profile": {"basin": 0.92, "hills": 0.98, "coast": 1.02, "ridges": 1.18, "rivers": 0.92, "pois": 1.08, "detail": 1.08},
        "land_biome_targets": {"plains": 0.27, "forest": 0.27, "jungle": 0.15, "snow": 0.05, "highland": 0.17, "peak": 0.09},
        "macro_regions": [
            {"biome": "forest", "x": 0.34, "y": 0.38, "radius": 0.26, "strength": 0.42},
            {"biome": "jungle", "x": 0.56, "y": 0.58, "radius": 0.18, "strength": 0.72},
            {"biome": "forest", "x": 0.80, "y": 0.30, "radius": 0.21, "strength": 0.32},
        ],
        "colours": {0: (18, 55, 110), 1: (205, 185, 135), 2: (122, 164, 82), 3: (86, 112, 63), 4: (38, 98, 52), 5: (224, 232, 242), 6: (178, 156, 98), 7: (114, 120, 86), 8: (192, 196, 188), 9: (155, 185, 75)},
        "weights": {"sub_bass": 0.50, "bass": 0.42, "midrange": 0.58, "presence": 0.68, "brilliance": 0.48},
    },
    "chapter5": {
        "label": "Chapter 5 - Helios",
        "description": "Official Chapter 5 shape: west chaparral, northwest boreal forest, central grassland rail corridor, and alpine east snowfields.",
        "water_level": 0.19,
        "moisture_jungle": 0.68,
        "moisture_forest": 0.43,
        "moisture_desert": 0.29,
        "moisture_snow": 0.35,
        "zone_desert": 0.66,
        "zone_snow": 0.38,
        "highland_min": 0.61,
        "peak_min": 0.79,
        "zone_seed": 517,
        "biome_bias": {"plains": 0.13, "forest": 0.10, "jungle": -0.14, "snow": 0.11, "desert": -0.04},
        "terrain_profile": {"basin": 0.96, "hills": 0.94, "coast": 0.98, "ridges": 1.06, "rivers": 0.84, "pois": 1.04, "detail": 0.92},
        "land_biome_targets": {"plains": 0.31, "forest": 0.24, "snow": 0.18, "desert": 0.04, "highland": 0.15, "peak": 0.08},
        "macro_regions": [
            {"biome": "forest", "x": 0.24, "y": 0.26, "radius": 0.22, "strength": 0.46},
            {"biome": "plains", "x": 0.52, "y": 0.72, "radius": 0.24, "strength": 0.44},
            {"biome": "snow", "x": 0.80, "y": 0.28, "radius": 0.24, "strength": 0.82},
            {"biome": "desert", "x": 0.18, "y": 0.78, "radius": 0.16, "strength": 0.18},
        ],
        "colours": {0: (20, 60, 118), 1: (216, 197, 148), 2: (132, 170, 94), 3: (76, 112, 65), 4: (38, 93, 54), 5: (233, 239, 247), 6: (191, 162, 96), 7: (106, 118, 90), 8: (204, 210, 218), 9: (164, 194, 96)},
        "weights": {"sub_bass": 0.46, "bass": 0.43, "midrange": 0.55, "presence": 0.50, "brilliance": 0.36},
    },
    "chapter6": {
        "label": "Chapter 6 - Hunters",
        "description": "Modern Fortnite reads as shrine-country hills, maple forests, lake basins, and disciplined mountain silhouettes with sparse arid land.",
        "water_level": 0.18,
        "moisture_jungle": 0.60,
        "moisture_forest": 0.41,
        "moisture_desert": 0.25,
        "moisture_snow": 0.32,
        "zone_desert": 0.74,
        "zone_snow": 0.36,
        "highland_min": 0.59,
        "peak_min": 0.77,
        "zone_seed": 624,
        "biome_bias": {"plains": 0.10, "forest": 0.16, "jungle": 0.02, "snow": -0.02, "desert": -0.16},
        "terrain_profile": {"basin": 0.94, "hills": 0.96, "coast": 0.92, "ridges": 1.16, "rivers": 0.88, "pois": 0.96, "detail": 1.02},
        "land_biome_targets": {"plains": 0.28, "forest": 0.30, "jungle": 0.08, "snow": 0.08, "highland": 0.18, "peak": 0.08},
        "macro_regions": [
            {"biome": "forest", "x": 0.30, "y": 0.32, "radius": 0.26, "strength": 0.56},
            {"biome": "jungle", "x": 0.74, "y": 0.38, "radius": 0.18, "strength": 0.28},
            {"biome": "plains", "x": 0.48, "y": 0.74, "radius": 0.22, "strength": 0.38},
            {"biome": "snow", "x": 0.60, "y": 0.16, "radius": 0.16, "strength": 0.26},
        ],
        "colours": {0: (22, 58, 114), 1: (208, 192, 146), 2: (135, 168, 92), 3: (88, 116, 64), 4: (48, 100, 58), 5: (228, 236, 244), 6: (188, 160, 102), 7: (108, 118, 92), 8: (196, 202, 210), 9: (166, 194, 96)},
        "weights": {"sub_bass": 0.48, "bass": 0.44, "midrange": 0.52, "presence": 0.46, "brilliance": 0.42},
    },
    "arctic": {
        "label": "Arctic Wasteland",
        "description": "Permafrost island with dominant snowfields, boreal edges, and glacial highland travel lanes.",
        "water_level": 0.15,
        "moisture_jungle": 0.90,
        "moisture_forest": 0.72,
        "moisture_desert": 0.05,
        "moisture_snow": 0.22,
        "zone_desert": 0.95,
        "zone_snow": 0.05,
        "highland_min": 0.52,
        "peak_min": 0.68,
        "zone_seed": 701,
        "biome_bias": {"plains": -0.10, "forest": 0.04, "jungle": -0.30, "snow": 0.34, "desert": -0.30},
        "terrain_profile": {"basin": 0.90, "hills": 0.88, "coast": 0.94, "ridges": 1.08, "rivers": 0.74, "pois": 0.92, "detail": 1.05},
        "land_biome_targets": {"plains": 0.12, "forest": 0.14, "snow": 0.44, "highland": 0.18, "peak": 0.12},
        "macro_regions": [
            {"biome": "snow", "x": 0.50, "y": 0.50, "radius": 0.52, "strength": 0.92},
            {"biome": "forest", "x": 0.24, "y": 0.32, "radius": 0.20, "strength": 0.22},
        ],
        "colours": {0: (10, 40, 100), 1: (230, 220, 205), 2: (175, 200, 190), 3: (120, 155, 140), 4: (80, 120, 95), 5: (240, 248, 255), 6: (200, 195, 185), 7: (150, 165, 175), 8: (225, 232, 242), 9: (160, 185, 170)},
        "weights": {"sub_bass": 0.30, "bass": 0.30, "midrange": 0.68, "presence": 0.30, "brilliance": 0.82},
    },
    "desert": {
        "label": "Desert Storm",
        "description": "Arid badlands with wide exposure, mesa ridges, and only tiny cooler or wetter relief pockets.",
        "water_level": 0.14,
        "moisture_jungle": 0.85,
        "moisture_forest": 0.72,
        "moisture_desert": 0.50,
        "moisture_snow": 0.02,
        "zone_desert": 0.25,
        "zone_snow": 0.98,
        "highland_min": 0.63,
        "peak_min": 0.80,
        "zone_seed": 808,
        "biome_bias": {"plains": 0.02, "forest": -0.16, "jungle": -0.28, "snow": -0.28, "desert": 0.32},
        "terrain_profile": {"basin": 0.92, "hills": 1.00, "coast": 0.82, "ridges": 1.18, "rivers": 0.48, "pois": 0.96, "detail": 0.98},
        "land_biome_targets": {"plains": 0.18, "desert": 0.40, "highland": 0.24, "peak": 0.10, "forest": 0.08},
        "macro_regions": [
            {"biome": "desert", "x": 0.52, "y": 0.50, "radius": 0.52, "strength": 0.92},
            {"biome": "forest", "x": 0.18, "y": 0.24, "radius": 0.14, "strength": 0.10},
        ],
        "colours": {0: (60, 90, 130), 1: (225, 210, 160), 2: (210, 185, 120), 3: (170, 145, 90), 4: (140, 115, 65), 5: (235, 215, 175), 6: (215, 175, 95), 7: (165, 138, 88), 8: (190, 160, 110), 9: (180, 165, 105)},
        "weights": {"sub_bass": 0.78, "bass": 0.68, "midrange": 0.32, "presence": 0.24, "brilliance": 0.16},
    },
    "jungle": {
        "label": "Primal Jungle",
        "description": "Dense canopy island with humid lowlands, visible rivers, and only isolated elevated clearings.",
        "water_level": 0.25,
        "moisture_jungle": 0.38,
        "moisture_forest": 0.28,
        "moisture_desert": 0.05,
        "moisture_snow": 0.02,
        "zone_desert": 0.98,
        "zone_snow": 0.98,
        "highland_min": 0.70,
        "peak_min": 0.85,
        "zone_seed": 915,
        "biome_bias": {"plains": -0.08, "forest": 0.08, "jungle": 0.34, "snow": -0.30, "desert": -0.28},
        "terrain_profile": {"basin": 1.06, "hills": 0.94, "coast": 0.96, "ridges": 0.90, "rivers": 1.28, "pois": 0.92, "detail": 0.88},
        "land_biome_targets": {"plains": 0.12, "forest": 0.16, "jungle": 0.44, "highland": 0.16, "peak": 0.12},
        "macro_regions": [
            {"biome": "jungle", "x": 0.50, "y": 0.50, "radius": 0.46, "strength": 0.92},
            {"biome": "forest", "x": 0.22, "y": 0.26, "radius": 0.18, "strength": 0.18},
        ],
        "colours": {0: (15, 65, 100), 1: (180, 190, 130), 2: (90, 140, 55), 3: (45, 95, 38), 4: (20, 75, 28), 5: (160, 185, 110), 6: (130, 160, 80), 7: (70, 105, 55), 8: (100, 130, 70), 9: (120, 155, 65)},
        "weights": {"sub_bass": 0.48, "bass": 0.58, "midrange": 0.70, "presence": 0.58, "brilliance": 0.38},
    },
    "volcanic": {
        "label": "Volcanic Inferno",
        "description": "Active caldera profile with ash basins, heavy ridgelines, and scorched traversal lanes rather than lush regional diversity.",
        "water_level": 0.12,
        "moisture_jungle": 0.75,
        "moisture_forest": 0.60,
        "moisture_desert": 0.35,
        "moisture_snow": 0.02,
        "zone_desert": 0.40,
        "zone_snow": 0.95,
        "highland_min": 0.50,
        "peak_min": 0.68,
        "zone_seed": 1022,
        "biome_bias": {"plains": -0.04, "forest": -0.10, "jungle": -0.24, "snow": -0.18, "desert": 0.16},
        "terrain_profile": {"basin": 0.84, "hills": 0.90, "coast": 0.86, "ridges": 1.30, "rivers": 0.34, "pois": 0.92, "detail": 1.16},
        "land_biome_targets": {"plains": 0.12, "desert": 0.20, "highland": 0.32, "peak": 0.22, "forest": 0.08, "jungle": 0.06},
        "macro_regions": [
            {"biome": "desert", "x": 0.50, "y": 0.52, "radius": 0.42, "strength": 0.60},
        ],
        "colours": {0: (80, 20, 10), 1: (120, 55, 30), 2: (80, 70, 60), 3: (55, 80, 45), 4: (35, 65, 30), 5: (200, 175, 155), 6: (90, 60, 40), 7: (70, 55, 45), 8: (110, 80, 60), 9: (95, 90, 55)},
        "weights": {"sub_bass": 0.88, "bass": 0.78, "midrange": 0.24, "presence": 0.30, "brilliance": 0.24},
    },
}


def get_theme(name: str) -> dict:
    return UEFN_THEMES.get(name, UEFN_THEMES["chapter1"])


def blend_theme_audio_weights(weights, theme_name="chapter1", theme_mix=0.38):
    theme_weights = get_theme(theme_name).get("weights", {})
    merged = dict(weights or {})
    for key in ("sub_bass", "bass", "midrange", "presence", "brilliance"):
        audio_value = float(merged.get(key, 0.5))
        theme_value = float(theme_weights.get(key, audio_value))
        merged[key] = max(0.0, min(1.0, audio_value * (1.0 - theme_mix) + theme_value * theme_mix))
    return merged


def _normalise01(arr):
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo < 1e-9:
        return np.zeros_like(arr, dtype=np.float64)
    return (arr - lo) / (hi - lo + 1e-9)


def _anchor_field(size, x_frac, y_frac, radius_frac, falloff=1.8):
    ys = np.linspace(0.0, 1.0, size)
    xs = np.linspace(0.0, 1.0, size)
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    dist = np.sqrt((xx - x_frac) ** 2 + (yy - y_frac) ** 2)
    return np.clip(1.0 - dist / max(radius_frac, 1e-6), 0.0, 1.0) ** falloff


def build_theme_macro_fields(size, theme_name="chapter1"):
    theme = get_theme(theme_name)
    zone_seed = int(theme.get("zone_seed", 42))
    fields = {
        "plains": np.zeros((size, size), dtype=np.float64),
        "forest": np.zeros((size, size), dtype=np.float64),
        "jungle": np.zeros((size, size), dtype=np.float64),
        "snow": np.zeros((size, size), dtype=np.float64),
        "desert": np.zeros((size, size), dtype=np.float64),
    }

    warp = gaussian_filter(nn(size, 2, 0.55, 2.0, 1.15, zone_seed + 19), sigma=size * 0.03)
    for idx, region in enumerate(theme.get("macro_regions", [])):
        biome_name = str(region.get("biome", "")).lower()
        if biome_name not in fields:
            continue
        field = _anchor_field(
            size,
            float(region.get("x", 0.5)),
            float(region.get("y", 0.5)),
            float(region.get("radius", 0.24)),
            float(region.get("falloff", 1.7)),
        )
        jitter = nn(size, 2, 0.55, 2.0, 1.0 + idx * 0.11, zone_seed + 200 + idx * 31)
        field = gaussian_filter(field * (0.82 + jitter * 0.36) * (0.78 + warp * 0.44), sigma=size * 0.02)
        fields[biome_name] += field * float(region.get("strength", 0.4))

    accent_total = fields["forest"] + fields["jungle"] + fields["snow"] + fields["desert"]
    plains_pad = gaussian_filter(np.clip(1.0 - accent_total * 0.68, 0.0, 1.0), sigma=size * 0.05)
    fields["plains"] += plains_pad

    for key in fields:
        fields[key] = _normalise01(fields[key])
    return fields


def classify_biomes_themed(height, moisture, water_level=0.20, theme_name="chapter1"):
    """
    classify_biomes with per-theme thresholds and colour overrides.
    Returns (biome_array, biome_colours_dict, biome_names_dict)
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter

    th = get_theme(theme_name)
    wl = water_level if water_level is not None else th.get("water_level", 0.20)

    size  = height.shape[0]
    biome = np.zeros((size, size), dtype=np.uint8)

    zone = nn(size, 2, 0.5, 2.0, 1.0, int(th.get("zone_seed", 42)))
    moisture_smooth = gaussian_filter(moisture, sigma=size * 0.08)
    macro = build_theme_macro_fields(size, theme_name)
    bias = th.get("biome_bias", {})

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

    plains_score = (
        0.42
        + np.clip(1.0 - np.abs(moisture_smooth - 0.45) * 1.9, 0.0, 1.0) * 0.42
        + macro["plains"] * 0.78
        + float(bias.get("plains", 0.0))
    )
    forest_score = (
        np.clip((moisture_smooth - mf) / max(1.0 - mf, 1e-6), 0.0, 1.0) * 0.90
        + macro["forest"] * 1.00
        + float(bias.get("forest", 0.0))
    )
    jungle_score = (
        np.clip((moisture_smooth - mj) / max(1.0 - mj, 1e-6), 0.0, 1.0) * 0.95
        + macro["jungle"] * 1.08
        + float(bias.get("jungle", 0.0))
    )
    desert_score = (
        np.clip((md - moisture_smooth) / max(md, 1e-6), 0.0, 1.0) * 0.88
        + np.clip((zone - zd) / max(1.0 - zd, 1e-6), 0.0, 1.0) * 0.55
        + macro["desert"] * 1.10
        + float(bias.get("desert", 0.0))
    )
    snow_score = (
        np.clip((ms - moisture_smooth) / max(ms, 1e-6), 0.0, 1.0) * 0.55
        + np.clip((zs - zone) / max(zs, 1e-6), 0.0, 1.0) * 0.50
        + np.clip((height - hm) / max(pm - hm, 1e-6), 0.0, 1.0) * 0.45
        + macro["snow"] * 1.08
        + float(bias.get("snow", 0.0))
    )

    scores = np.stack((plains_score, forest_score, jungle_score, snow_score, desert_score), axis=0)
    winners = np.argmax(scores, axis=0)
    palette = np.array([2, 3, 4, 5, 6], dtype=np.uint8)
    biome[land] = palette[winners[land]]

    biome[land & (height > hm) & (height <= pm)] = 7  # highland
    biome[land & (height > pm)] = 8  # peak

    colours = th["colours"]
    names   = {0:"Water",1:"Beach",2:"Plains",3:"Forest",
               4:"Jungle",5:"Snow",6:"Desert",7:"Highland",8:"Peak",9:"Farm"}

    return biome, colours, names

def classify_biomes(height, moisture, water_level=0.20):
    """
    Fortnite-style biome classification:
    - Biome zones are LARGE (quarter-map scale) not scattered
    - Determined by a large-scale zone noise, not per-pixel height/moisture
    """
    size = height.shape[0]
    biome = np.zeros((size,size), dtype=np.uint8)

    # Large-scale zone noise — determines which QUARTER of the map is which biome
    zone = nn(size, 2, 0.5, 2.0, 1.0, 42)  # fixed seed for consistency
    moisture_smooth = gaussian_filter(moisture, sigma=size*0.08)

    biome[:] = BIOME_PLAINS  # default

    # Water and beach
    biome[height < water_level] = BIOME_WATER
    biome[(height >= water_level) & (height < water_level + 0.05)] = BIOME_BEACH

    # Large biome zones based on position in moisture/zone space
    land = height >= water_level + 0.05

    biome[land & (moisture_smooth > 0.58)] = BIOME_JUNGLE
    biome[land & (moisture_smooth > 0.42) & (moisture_smooth <= 0.58)] = BIOME_FOREST
    biome[land & (moisture_smooth < 0.32) & (zone > 0.55)] = BIOME_DESERT
    biome[land & (moisture_smooth < 0.36) & (zone <= 0.45)] = BIOME_SNOW
    biome[land & (height > 0.65) & (height <= 0.82)] = BIOME_HIGHLAND
    biome[land & (height > 0.82)] = BIOME_PEAK

    return biome

# ─────────────────────────────────────────────────────────────
# PLOT POSITIONS
# ─────────────────────────────────────────────────────────────

def find_plot_positions(height, biome, n_plots, size,
                        min_spacing=28, cluster_angle_deg=135.0,
                        cluster_spread=1.0, seed=42):
    """Find flat land positions suitable for farm plots."""
    rng = np.random.default_rng(seed + 7777)
    water_level = 0.21
    cy, cx = size//2, size//2

    # Compute flatness score — prefer gently sloping terrain
    gy, gx = np.gradient(height)
    slope = np.sqrt(gy**2 + gx**2)
    flat_score = 1 / (1 + slope * 40)

    # Farm plots go in plains/forest biomes
    farm_ok = np.isin(biome, [BIOME_PLAINS, BIOME_FOREST, BIOME_FARM])
    land_ok  = height > water_level + 0.08
    elev_ok  = (height > 0.25) & (height < 0.65)
    eligible = farm_ok & land_ok & elev_ok

    candidates = np.argwhere(eligible & (flat_score > 0.3))
    if len(candidates) == 0:
        candidates = np.argwhere(land_ok & elev_ok)
    if len(candidates) == 0:
        return []

    # Cluster around a farm zone
    angle_rad = math.radians(cluster_angle_deg)
    farm_cx = cx + int(size * 0.22 * cluster_spread * math.cos(angle_rad))
    farm_cy = cy + int(size * 0.22 * cluster_spread * math.sin(angle_rad))
    farm_cx = np.clip(farm_cx, size//8, 7*size//8)
    farm_cy = np.clip(farm_cy, size//8, 7*size//8)

    dists_to_farm = np.sqrt((candidates[:,0]-farm_cy)**2 + (candidates[:,1]-farm_cx)**2)
    weights_farm  = np.exp(-dists_to_farm / (size*0.18))
    weights_flat  = flat_score[candidates[:,0], candidates[:,1]]
    weights_total = weights_farm * weights_flat
    total_w = weights_total.sum()
    if total_w == 0: probs = None
    else: probs = weights_total / total_w

    positions = []
    max_tries = n_plots * 80
    for _ in range(max_tries):
        if len(positions) >= n_plots: break
        idx = rng.choice(len(candidates), p=probs)
        py, px = candidates[idx]
        too_close = any(math.hypot(py-ey, px-ex) < min_spacing for ey,ex in positions)
        if not too_close:
            positions.append((int(py), int(px)))

    return positions

def get_farm_cluster_info(positions, size):
    if not positions: return {"center":(size//2,size//2),"radius":0}
    cy = int(np.mean([p[0] for p in positions]))
    cx = int(np.mean([p[1] for p in positions]))
    r  = int(np.max([math.hypot(p[0]-cy, p[1]-cx) for p in positions]))
    return {"center":(cy,cx),"radius":r}

def paint_farm_biome(biome, positions, size, padding=18, seed=42):
    if not positions: return biome
    biome = biome.copy()
    for py,px in positions:
        r1,r2 = max(0,py-padding), min(size,py+padding)
        c1,c2 = max(0,px-padding), min(size,px+padding)
        biome[r1:r2, c1:c2] = np.where(
            biome[r1:r2,c1:c2] != BIOME_WATER, BIOME_FARM, BIOME_WATER)
    return biome

# ─────────────────────────────────────────────────────────────
# LAYOUT / VERSE CONSTANTS
# ─────────────────────────────────────────────────────────────

def pixel_to_world(row, col, size, world_size_cm=None):
    """Convert pixel coords to Fortnite/UEFN world cm coords.
    Defaults to DEFAULT_WORLD_SIZE_CM (double_br = 1,100,000 cm).
    Pass world_size_cm explicitly to override.
    """
    if world_size_cm is None:
        world_size_cm = DEFAULT_WORLD_SIZE_CM
    half = world_size_cm / 2
    x = (col / size) * world_size_cm - half
    z = (row / size) * world_size_cm - half
    return x, z

def build_layout(height, biome, plot_positions, size, seed, weights,
                 water_level=0.20, world_wrap=True, world_size_cm=None):
    """Build the full JSON layout for UEFN export.

    world_size_cm — physical size of the landscape in Unreal cm.
                    Defaults to DEFAULT_WORLD_SIZE_CM (double_br = 1,100,000).
                    Use WORLD_SIZE_PRESETS dict or pass any integer.
    """
    if world_size_cm is None:
        world_size_cm = DEFAULT_WORLD_SIZE_CM

    # Identify preset name for the warning message
    preset_name = next((k for k,v in WORLD_SIZE_PRESETS.items() if v == world_size_cm), "custom")
    world_partition_required = world_size_cm > UEFN_STREAMING_THRESHOLD_CM
    recommended_px = RECOMMENDED_HEIGHTMAP_SIZE.get(preset_name, size)
    direct_import_ok = size <= UEFN_DIRECT_IMPORT_MAX_PX

    verse_plots = []
    for i, (row, col) in enumerate(plot_positions):
        wx, wz = pixel_to_world(row, col, size, world_size_cm)
        elev = float(height[row, col])
        verse_plots.append({
            "index": i,
            "pixel": [int(row), int(col)],
            "world_x_cm": round(wx, 1),
            "world_z_cm": round(wz, 1),
            "elevation": round(elev, 4),
            "biome": BIOME_NAMES.get(int(biome[row, col]), "Plains"),
        })

    # Town center
    cluster = get_farm_cluster_info(plot_positions, size)
    tc_row, tc_col = cluster["center"]
    tc_x, tc_z = pixel_to_world(tc_row, tc_col, size, world_size_cm)

    # Zone centers at compass points
    offsets = [(-0.3, 0), (0.3, 0), (0, -0.3), (0, 0.3), (-0.2, -0.2), (0.2, 0.2)]
    zone_centers = []
    for dy, dx in offsets:
        zr = int(np.clip(size//2 + dy*size, 0, size-1))
        zc = int(np.clip(size//2 + dx*size, 0, size-1))
        zx, zz = pixel_to_world(zr, zc, size, world_size_cm)
        zone_centers.append({"pixel":[zr,zc],"world_x_cm":round(zx,1),"world_z_cm":round(zz,1)})

    biome_counts = {}
    for b in np.unique(biome):
        biome_counts[BIOME_NAMES.get(int(b),"?")] = int(np.sum(biome==b))
    total_px = size * size
    biome_pcts = {k: round(v/total_px*100,1) for k,v in biome_counts.items()}

    cm_per_px = world_size_cm / size

    # Streaming / import warning block — surfaced in the JSON for the UI to display
    wp_warning = None
    if world_partition_required:
        wp_warning = {
            "required": True,
            "preset": preset_name,
            "world_size_km": round(world_size_cm / 100_000, 2),
            "recommended_heightmap_px": recommended_px,
            "current_heightmap_px": size,
            "uefn_direct_import_limit_px": UEFN_DIRECT_IMPORT_MAX_PX,
            "steps": [
                "UEFN → Edit → Project Settings → World → Enable World Partition",
                "World Settings → Enable Streaming",
                "Landscape → Section Size: 63×63 quads",
                "Landscape → Sections Per Component: 2×2",
                f"Keep direct square landscape import at or below {UEFN_DIRECT_IMPORT_MAX_PX}×{UEFN_DIRECT_IMPORT_MAX_PX} px",
                f"Recommended Forge export resolution for this size: {recommended_px}×{recommended_px} px",
                "Import this heightmap via Landscape Mode → Import → select PNG",
            ]
        }
        if not direct_import_ok:
            wp_warning["steps"].append(
                f"Current requested square heightmap ({size}×{size}) exceeds the direct UEFN square import lane; use a {recommended_px}×{recommended_px} export for import."
            )

    return {
        "meta": {
            "generator": "Island Forge v3.0",
            "seed": seed,
            "size": size,
            "water_level": water_level,
            "world_wrap": world_wrap,
            "world_size_cm": world_size_cm,
            "world_size_km": round(world_size_cm / 100_000, 2),
            "world_size_preset": preset_name,
            "cm_per_pixel": round(cm_per_px, 2),
            "meters_per_pixel": round(cm_per_px / 100, 2),
            "weights": weights,
            "biome_coverage_pct": biome_pcts,
            "world_partition_warning": wp_warning,
            "streaming_recommended": world_partition_required,
            "uefn_direct_import_limit_px": UEFN_DIRECT_IMPORT_MAX_PX,
            "direct_import_resolution_ok": direct_import_ok,
        },
        "town_center": {
            "pixel": [tc_row, tc_col],
            "world_x_cm": round(tc_x, 1),
            "world_z_cm": round(tc_z, 1),
        },
        "zone_centers": zone_centers,
        "plots": verse_plots,
        "verse_constants": {
            "PLOT_COUNT":      len(verse_plots),
            "TOWN_X":          round(tc_x, 1),
            "TOWN_Z":          round(tc_z, 1),
            "WORLD_SIZE_CM":   world_size_cm,
            "WORLD_SIZE_PRESET": f'"{preset_name}"',
            "CM_PER_PIXEL":    round(cm_per_px, 2),
            "WATER_LEVEL":     round(water_level, 3),
        }
    }

# ─────────────────────────────────────────────────────────────
# PREVIEW RENDERER  — Fortnite-style map look
# ─────────────────────────────────────────────────────────────

def build_preview(height, biome, plot_positions, size, road_mask=None, biome_colours=None):
    """
    Renders a Fortnite-map-style top-down preview:
    - Biome colours (large zones)
    - Hillshading from NW light source
    - Contour lines every 0.10
    - Road overlay
    - Plot markers
    - Coastal vignette
    """
    rgb = np.zeros((size, size, 3), dtype=np.uint8)

    colours = biome_colours or BIOME_COLOURS

    # Base biome colours
    for b, col in colours.items():
        mask = biome == b
        for c in range(3):
            rgb[:,:,c][mask] = col[c]

    # Hillshading — NW directional light
    dy_s, dx_s = np.gradient(height * 0.6)
    light_y, light_x = -0.7, -0.7
    light_len = math.hypot(light_y, light_x)
    shade = -(dx_s * light_x + dy_s * light_y) / (light_len + 1e-9)
    shade = np.clip(shade * 3.5, -1, 1)
    shade_factor = 1.0 + shade * 0.4

    for c in range(3):
        ch = rgb[:,:,c].astype(np.float32)
        ch = np.clip(ch * shade_factor, 0, 255)
        rgb[:,:,c] = ch.astype(np.uint8)

    # Elevation-based brightness boost on land
    land = biome != BIOME_WATER
    elev_boost = np.clip(height * 0.3, 0, 0.25)
    for c in range(3):
        ch = rgb[:,:,c].astype(np.float32)
        ch[land] = np.clip(ch[land] + elev_boost[land] * 60, 0, 255)
        rgb[:,:,c] = ch.astype(np.uint8)

    # Contour lines every 0.10 elevation
    contour_interval = 0.10
    contour_map = (height / contour_interval).astype(int)
    gy_c, gx_c = np.gradient(contour_map.astype(float))
    contour_edge = (np.abs(gy_c) + np.abs(gx_c) > 0.5) & land
    for c in range(3):
        ch = rgb[:,:,c].astype(np.float32)
        ch[contour_edge] = np.clip(ch[contour_edge] * 0.72, 0, 255)
        rgb[:,:,c] = ch.astype(np.uint8)

    # Water depth shading — darker deeper
    water = biome == BIOME_WATER
    depth = np.clip(1 - height / 0.20, 0, 1)
    for c in range(3):
        ch = rgb[:,:,c].astype(np.float32)
        ch[water] = ch[water] * (0.5 + 0.5 * (1 - depth[water] * 0.5))
        rgb[:,:,c] = ch.astype(np.uint8)

    # Road overlay — light grey paths
    if road_mask is not None:
        road = road_mask & land
        rgb[road] = [180, 170, 155]

    # Plot markers — white squares with coloured border
    marker_r = max(3, size // 80)
    for py, px in plot_positions:
        r1 = max(0, py-marker_r); r2 = min(size, py+marker_r+1)
        c1 = max(0, px-marker_r); c2 = min(size, px+marker_r+1)
        rgb[r1:r2, c1:c2] = [255, 230, 80]   # yellow fill
        # Border
        rgb[r1:r1+1, c1:c2] = [20, 20, 20]
        rgb[r2-1:r2, c1:c2] = [20, 20, 20]
        rgb[r1:r2, c1:c1+1] = [20, 20, 20]
        rgb[r1:r2, c2-1:c2] = [20, 20, 20]

    # Coastal vignette — darken toward edges
    cy, cx = size//2, size//2
    YY, XX = np.meshgrid(np.arange(size), np.arange(size), indexing='ij')
    edge_dist = np.minimum(
        np.minimum(YY, size-1-YY),
        np.minimum(XX, size-1-XX)
    ).astype(float) / (size * 0.08)
    vignette = np.clip(edge_dist, 0, 1)
    for c in range(3):
        ch = rgb[:,:,c].astype(np.float32)
        ch = ch * (0.7 + vignette * 0.3)
        rgb[:,:,c] = np.clip(ch, 0, 255).astype(np.uint8)

    return rgb

# ─────────────────────────────────────────────────────────────
# CLI ENTRY
# ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Island Forge v3.0 — Fortnite-style terrain generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
WORLD SIZE PRESETS:
  uefn_small   →    50,000 cm  (500m)       UEFN default island
  uefn_max     →   100,000 cm  (1km)        UEFN creative max
  br_chapter2  →   550,000 cm  (5.5km)      Fortnite BR Chapter 2
  double_br    → 1,100,000 cm  (11km)       DEFAULT — 2× BR map  ← recommended
  skyrim       → 3,700,000 cm  (37km)       approx. Skyrim
  gta5         → 8,100,000 cm  (81km)       approx. GTA V

  ⚠ Islands above 1km on the widest axis should be prepared for Streaming / World Partition in UEFN.
  The generated layout.json includes step-by-step setup instructions.
        """
    )
    ap.add_argument("--size",       type=int,   default=2017,
                    help="Heightmap resolution in pixels. Forge keeps 2017 as the current direct UEFN square import ceiling; larger values are research-only.")
    ap.add_argument("--seed",       type=int,   default=42)
    ap.add_argument("--audio",      type=str,   default=None)
    ap.add_argument("--out",        type=str,   default=".")
    ap.add_argument("--water",      type=float, default=0.20)
    ap.add_argument("--sub_bass",   type=float, default=0.5)
    ap.add_argument("--bass",       type=float, default=0.5)
    ap.add_argument("--midrange",   type=float, default=0.5)
    ap.add_argument("--presence",   type=float, default=0.5)
    ap.add_argument("--brilliance", type=float, default=0.3)
    ap.add_argument("--bpm",        type=float, default=120.0)
    ap.add_argument("--world_size", type=str,   default="double_br",
                    help="World size preset name or integer cm value. Default: double_br (1,100,000 cm / 11km)")
    ap.add_argument("--world_wrap", action="store_true", default=True,
                    help="Enable edge-wrap teleporters (world_wrap_manager.verse)")
    ap.add_argument("--theme",      type=str,   default="chapter1",
                    help="Biome theme: chapter1, chapter2, chapter3, chapter4, chapter5, chapter6, arctic, desert, jungle, volcanic")
    args = ap.parse_args()

    # Resolve world size
    if args.world_size in WORLD_SIZE_PRESETS:
        world_size_cm = WORLD_SIZE_PRESETS[args.world_size]
        preset_name   = args.world_size
    else:
        try:
            world_size_cm = int(args.world_size)
            preset_name   = "custom"
        except ValueError:
            print(f"[error] Unknown world_size '{args.world_size}'. Use a preset name or integer cm value.")
            print(f"        Presets: {list(WORLD_SIZE_PRESETS.keys())}")
            return

    # World Partition warning to console
    if world_size_cm > UEFN_STREAMING_THRESHOLD_CM:
        rec_px = RECOMMENDED_HEIGHTMAP_SIZE.get(preset_name, args.size)
        print(f"""
⚠  STREAMING / PARTITION RECOMMENDED  ({'%.1f' % (world_size_cm/100_000)}km × {'%.1f' % (world_size_cm/100_000)}km)
   1. UEFN → Edit → Project Settings → World → Enable World Partition
   2. World Settings → Enable Streaming
   3. Landscape → Section Size: 63×63 quads, Sections Per Component: 2×2
   4. Keep direct square import at or below {UEFN_DIRECT_IMPORT_MAX_PX}×{UEFN_DIRECT_IMPORT_MAX_PX} px
   5. Recommended Forge export size for {preset_name}: {rec_px}×{rec_px} px
      (Current: {args.size}×{args.size}{"  ✓" if args.size == rec_px else f"  — consider --size {rec_px}"})
""")

    cm_per_px = world_size_cm / args.size
    print(f"[gen] Seed={args.seed}  Size={args.size}×{args.size}  "
          f"World={world_size_cm:,}cm ({world_size_cm/100_000:.1f}km)  "
          f"{cm_per_px:.0f}cm/px ({cm_per_px/100:.1f}m/px)  Water={args.water}  Theme={args.theme}")

    w = {"sub_bass":args.sub_bass,"bass":args.bass,"midrange":args.midrange,
         "presence":args.presence,"brilliance":args.brilliance,
         "tempo_bpm":args.bpm,"duration_s":0}
    if args.audio:
        w = analyse_audio(args.audio)
        print("[audio] Weights:", {k:round(v,3) for k,v in w.items()})

    w = blend_theme_audio_weights(w, args.theme)
    height, road_mask = generate_terrain(args.size, args.seed, w, args.water, theme_name=args.theme)
    moisture = generate_moisture(args.size, args.seed)
    biome, _, _ = classify_biomes_themed(height, moisture, args.water, theme_name=args.theme)
    plots    = find_plot_positions(height, biome, 32, args.size)
    biome    = paint_farm_biome(biome, plots, args.size)
    layout   = build_layout(height, biome, plots, args.size, args.seed, w,
                             args.water, args.world_wrap, world_size_cm)
    preview  = build_preview(height, biome, plots, args.size, road_mask)

    # ✅ NEW: Generate Verse package
    result = {
        "heightmap_normalized": height.tolist(),
        "biome_map": biome.tolist(),
        "plots_found": layout["plots"],
        "town_center": [layout["town_center"]["pixel"][0], layout["town_center"]["pixel"][1]],
        "world_size_cm": world_size_cm,
    }
    result = integrate_with_forge(result, theme=args.theme, seed=args.seed)

    # Save original files
    os.makedirs(args.out, exist_ok=True)
    hm16 = (height * 65535).astype(np.uint16)
    Image.fromarray(hm16).save(
        os.path.join(args.out, f"island_{args.seed}_heightmap.png"))
    Image.fromarray(preview, mode="RGB").save(
        os.path.join(args.out, f"island_{args.seed}_preview.png"))
    with open(os.path.join(args.out, f"island_{args.seed}_layout.json"),"w") as f:
        json.dump(layout, f, indent=2)

    # ✅ NEW: Save Verse package
    verse_dir = os.path.join(args.out, f"island_{args.seed}_verse_package")
    os.makedirs(verse_dir, exist_ok=True)
    for filename, content in result["verse_package"].items():
        filepath = os.path.join(verse_dir, filename)
        with open(filepath, "w") as f:
            f.write(content)
    
    print(f"[done] {len(plots)} plots · biomes: {layout['meta']['biome_coverage_pct']}")
    print(f"[verse] Saved {len(result['verse_package'])} files to {verse_dir}/")
    if layout["meta"].get("world_partition_warning"):
        print(f"[!] layout.json contains World Partition setup steps — check meta.world_partition_warning")

if __name__ == "__main__":
    main()
