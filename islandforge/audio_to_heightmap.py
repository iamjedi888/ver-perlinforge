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

⚠️  WORLD PARTITION WARNING  ────────────────────────────────────────────────────
  Maps larger than ~200,000 cm (2km) REQUIRE World Partition enabled in UEFN:
    UEFN → Edit → Project Settings → World → Enable World Partition
    Then: World Settings → Enable Streaming
  Without this, large landscapes will fail to load or crash the editor.
  For "double_br" and above, also set:
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

# Default world size — 2× the Fortnite BR map, requires World Partition
DEFAULT_WORLD_SIZE_CM = WORLD_SIZE_PRESETS["double_br"]  # 1,100,000 cm

# Recommended heightmap resolutions per size (UE5 valid landscape sizes)
# UE5 valid sizes: 127, 253, 505, 1009, 2017, 4033, 8129
RECOMMENDED_HEIGHTMAP_SIZE = {
    "uefn_small":   505,
    "uefn_max":    1009,
    "br_chapter2": 1009,
    "double_br":   2017,   # ~54cm/px at 11km — good detail
    "skyrim":      4033,
    "gta5":        8129,
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
    result = np.zeros((size,size), dtype=np.float64)
    amp=1.0; freq=1.0; maxv=0.0
    lin = np.linspace(0, scale, size, endpoint=False)
    xs, ys = np.meshgrid(lin, lin)
    for _ in range(octaves):
        result += amp * perlin2d(xs*freq, ys*freq, perm)
        maxv += amp; amp *= persistence; freq *= lacunarity
    return result / maxv

def nn(size, oct, per, lac, scale, seed):
    """Normalised noise 0..1"""
    n = octave_noise(size, oct, per, lac, scale, seed)
    lo,hi = n.min(), n.max()
    return (n-lo)/(hi-lo+1e-9)

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
    return np.clip(mask, 0, 1)

# ─────────────────────────────────────────────────────────────
# FORTNITE-STYLE BASE TERRAIN
# ─────────────────────────────────────────────────────────────

def build_fortnite_terrain(size, seed, w, island_mask):
    """
    Builds terrain that mimics Fortnite map structure:
    - Large flat interior bowl (natural storm funnel)
    - Coastal ridge / cliff shelf
    - 1-3 mountain ridges (asymmetric)
    - Gently rolling flatlands between them
    - Audio weights shape the style
    """
    rng = np.random.default_rng(seed + 100)
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
    bowl = dist_center * 0.35
    bowl = gaussian_filter(bowl, sigma=size*0.06)

    # ── Layer 2: Gentle rolling hills over flatlands
    # bass controls hilliness of playable area
    hills = nn(size, 4, 0.55, 2.0, 1.5 + bass * 1.5, seed+10)
    hills = gaussian_filter(hills, sigma=size*0.04)
    # Keep hills gentle — flatten the amplitude
    hills = hills * (0.12 + bass * 0.10)

    # ── Layer 3: Coastal cliff shelf
    # Inner land is raised relative to water, creating natural cliffs at coast
    # island_mask already gives us the coastal gradient
    coast_shelf = np.clip((island_mask - 0.35) * 3, 0, 1)
    coast_shelf = gaussian_filter(coast_shelf ** 0.7, sigma=size*0.025)
    coast_shelf *= (0.18 + presence * 0.15)

    # ── Layer 4: Mountain ridges (sub_bass driven)
    # Fortnite has 1-3 distinct ridges, not scattered peaks
    n_ridges = 1 + int(sub_bass * 2.5)  # 1 to 3 ridges
    ridge_terrain = np.zeros((size,size))

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

        ridge_height = 0.30 + sub_bass * 0.20
        ridge_terrain += ridge_blend * ridge_height / n_ridges

    # ── Layer 5: Fine surface detail (brilliance driven)
    detail = nn(size, 5, 0.5, 2.1, 3.0 + brilliance*2, seed+30)
    detail = gaussian_filter(detail, sigma=size*0.005)
    detail = (detail - 0.5) * (0.04 + brilliance * 0.04)

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

    return terrain

# ─────────────────────────────────────────────────────────────
# POI LANDING PADS
# ─────────────────────────────────────────────────────────────

def inject_pois(terrain, island_mask, size, seed, midrange=0.5, n_pois=None):
    """
    Flatten circular areas for POIs (named locations).
    Some are raised (hilltop town), some are lowered (valley village).
    Returns terrain + list of POI centers.
    """
    rng = np.random.default_rng(seed + 5000)
    if n_pois is None:
        n_pois = 3 + int(midrange * 4)  # 3-7 POIs

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
        poi_r = size * (0.04 + midrange * 0.025)
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

def simulate_rivers(terrain, island_mask, size, seed, midrange=0.5):
    """
    Fortnite rivers are wide, shallow, and navigable.
    They flow from high ground toward coast in gentle curves.
    """
    rng = np.random.default_rng(seed + 3000)
    n_rivers = 1 + int(midrange * 3)

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
        river_width  = size * (0.018 + midrange * 0.012)
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

def generate_terrain(size, seed, weights, water_level=0.20):
    """
    Full Fortnite-style terrain generation pipeline.
    Returns (height_array 0..1, road_mask bool array).
    """
    w          = weights
    sub_bass   = w.get("sub_bass",   0.5)
    midrange   = w.get("midrange",   0.5)
    presence   = w.get("presence",   0.5)
    bpm        = w.get("tempo_bpm",  120.0)

    # 1. Island mask
    island_mask = build_island_mask(size, seed, presence, bpm)

    # 2. Base terrain
    terrain = build_fortnite_terrain(size, seed, w, island_mask)

    # 3. POI landing pads
    terrain, poi_centers = inject_pois(terrain, island_mask, size, seed, midrange)

    # 4. Rivers
    terrain = simulate_rivers(terrain, island_mask, size, seed, midrange)

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

    return np.clip(terrain, 0, 1), road_mask

# ─────────────────────────────────────────────────────────────
# MOISTURE + BIOMES
# ─────────────────────────────────────────────────────────────

def generate_moisture(size, seed):
    return nn(size, 4, 0.5, 2.0, 2.0, seed + 999)

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
    world_partition_required = world_size_cm > 200_000
    recommended_px = RECOMMENDED_HEIGHTMAP_SIZE.get(preset_name, size)

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

    # World Partition warning block — surfaced in the JSON for the UI to display
    wp_warning = None
    if world_partition_required:
        wp_warning = {
            "required": True,
            "preset": preset_name,
            "world_size_km": round(world_size_cm / 100_000, 2),
            "recommended_heightmap_px": recommended_px,
            "current_heightmap_px": size,
            "steps": [
                "UEFN → Edit → Project Settings → World → Enable World Partition",
                "World Settings → Enable Streaming",
                "Landscape → Section Size: 63×63 quads",
                "Landscape → Sections Per Component: 2×2",
                f"Recommended heightmap resolution for this size: {recommended_px}×{recommended_px} px",
                "Import this heightmap via Landscape Mode → Import → select PNG",
            ]
        }

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

  ⚠ Maps > 2km require World Partition enabled in UEFN Project Settings.
  The generated layout.json includes step-by-step setup instructions.
        """
    )
    ap.add_argument("--size",       type=int,   default=2017,
                    help="Heightmap resolution in pixels. UE5 valid sizes: 505,1009,2017,4033. Default: 2017 (matches double_br)")
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
                    help="Biome theme: chapter1, chapter2, chapter3, chapter4, arctic, desert, jungle, volcanic")
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
    if world_size_cm > 200_000:
        rec_px = RECOMMENDED_HEIGHTMAP_SIZE.get(preset_name, args.size)
        print(f"""
⚠  WORLD PARTITION REQUIRED  ({'%.1f' % (world_size_cm/100_000)}km × {'%.1f' % (world_size_cm/100_000)}km)
   1. UEFN → Edit → Project Settings → World → Enable World Partition
   2. World Settings → Enable Streaming
   3. Landscape → Section Size: 63×63 quads, Sections Per Component: 2×2
   4. Recommended heightmap size for {preset_name}: {rec_px}×{rec_px} px
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

    height, road_mask = generate_terrain(args.size, args.seed, w, args.water)
    moisture = generate_moisture(args.size, args.seed)
    biome    = classify_biomes(height, moisture, args.water)
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
