"""
audio_to_heightmap.py
=====================
Generates a UEFN-ready heightmap PNG + island layout JSON
from either an audio file or a numeric seed.

USAGE:
    # From audio file:
    python audio_to_heightmap.py --audio mysong.wav --output island_01

    # From seed only (no audio needed):
    python audio_to_heightmap.py --seed 42 --output island_01

    # Full options:
    python audio_to_heightmap.py --audio mysong.wav --seed 7 --size 1009
        --plots 32 --output island_01 --preview

OUTPUTS:
    island_01_heightmap.png   — 16-bit grayscale, import to UEFN landscape
    island_01_layout.json     — biome zones, plot positions, town center,
                                zone tiers — consumed by plot_registry.verse
    island_01_preview.png     — RGB colour map for visual inspection

UEFN HEIGHTMAP REQUIREMENTS:
    - 16-bit grayscale PNG
    - Dimensions: power-of-2 + 1 (513×513, 1009×1009, 2017×2017)
    - Import via: Landscape mode → Import from file
    - Scale: set Z scale to ~5000 in UEFN for good mountain heights

PIPELINE OVERVIEW:
    1. Audio (optional) → FFT → frequency bands → terrain layer weights
       - Sub-bass  (20-60Hz)   → mountain ridge amplitude
       - Bass      (60-250Hz)  → hill frequency
       - Midrange  (250-2kHz)  → detail noise scale
       - Presence  (2-8kHz)    → erosion / roughness
       - Brilliance (8-20kHz)  → micro-detail / grass variation
    2. Perlin noise (pure numpy, no external lib) → base terrain
    3. Layers blended with audio weights (or defaults if no audio)
    4. Island mask (radial falloff) — ensures ocean border
    5. Biome classification from height + moisture noise
    6. Town, farm area, zone tier boundaries placed on flat areas
    7. 32 plot positions found on flattest terrain in farm biome
"""

import argparse
import json
import math
import os
import struct
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

# ─────────────────────────────────────────────────────────────
# PERLIN NOISE — pure numpy implementation
# ─────────────────────────────────────────────────────────────

def make_permutation(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    p = np.arange(256, dtype=np.int32)
    rng.shuffle(p)
    return np.tile(p, 2)

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def lerp(a, b, t):
    return a + t * (b - a)

def grad(h, x, y):
    """Gradient function for 2D Perlin."""
    h = h & 3
    u = np.where(h < 2, x, y)
    v = np.where(h < 2, y, x)
    return np.where(h & 1, -u, u) + np.where(h & 2, -v, v)

def perlin2d(x: np.ndarray, y: np.ndarray, perm: np.ndarray) -> np.ndarray:
    """Vectorised 2D Perlin noise, returns values in [-1, 1]."""
    xi = x.astype(int) & 255
    yi = y.astype(int) & 255
    xf = x - np.floor(x)
    yf = y - np.floor(y)
    u = fade(xf)
    v = fade(yf)

    aa = perm[perm[xi]     + yi    ]
    ab = perm[perm[xi]     + yi + 1]
    ba = perm[perm[xi + 1] + yi    ]
    bb = perm[perm[xi + 1] + yi + 1]

    x1 = lerp(grad(aa, xf,     yf    ), grad(ba, xf - 1, yf    ), u)
    x2 = lerp(grad(ab, xf,     yf - 1), grad(bb, xf - 1, yf - 1), u)
    return lerp(x1, x2, v)

def octave_noise(size: int, octaves: int, persistence: float,
                 lacunarity: float, scale: float, seed: int) -> np.ndarray:
    """Fractal Brownian Motion — sum of Perlin octaves."""
    perm = make_permutation(seed)
    result = np.zeros((size, size), dtype=np.float64)
    amplitude = 1.0
    frequency = 1.0
    max_val = 0.0

    lin = np.linspace(0, scale, size, endpoint=False)
    xs, ys = np.meshgrid(lin, lin)

    for _ in range(octaves):
        result += amplitude * perlin2d(xs * frequency, ys * frequency, perm)
        max_val += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    return result / max_val  # normalise to [-1, 1]

# ─────────────────────────────────────────────────────────────
# AUDIO ANALYSIS — extract frequency band energies
# Falls back gracefully if audio file is missing or unreadable
# ─────────────────────────────────────────────────────────────

def analyse_audio(path: str) -> dict:
    """
    Returns normalised energy per frequency band (0.0–1.0).
    Falls back to equal weights if audio unavailable.
    """
    default = {
        "sub_bass": 0.5,
        "bass": 0.5,
        "midrange": 0.5,
        "presence": 0.5,
        "brilliance": 0.5,
        "tempo_bpm": 120.0,
        "duration_s": 60.0,
    }

    SUPPORTED = (".wav", ".mp3", ".flac", ".ogg", ".aac", ".m4a", ".aiff", ".opus")

    try:
        import subprocess, tempfile
        from scipy.io import wavfile

        ext = os.path.splitext(path)[1].lower()

        if ext not in SUPPORTED:
            print(f"[audio] Unsupported format '{ext}' — using defaults.")
            return default

        # Transcode any format to temp WAV via ffmpeg (if available)
        # Falls back to scipy direct read for .wav
        work_path = path
        tmp_wav = None

        if ext != ".wav":
            ffmpeg = subprocess.run(["which", "ffmpeg"],
                                    capture_output=True).stdout.strip()
            if not ffmpeg:
                print("[audio] ffmpeg not found — only .wav supported without it.")
                return default
            tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_wav.close()
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", path,
                 "-ac", "1", "-ar", "44100",
                 "-sample_fmt", "s16", tmp_wav.name],
                capture_output=True
            )
            if result.returncode != 0:
                print(f"[audio] ffmpeg transcode failed — using defaults.")
                return default
            work_path = tmp_wav.name
            print(f"[audio] Transcoded {ext} → wav via ffmpeg")

        # Read with scipy (handles more WAV variants than wave module)
        framerate, raw = wavfile.read(work_path)
        if tmp_wav:
            os.unlink(tmp_wav.name)

        # Normalise to float64
        if raw.dtype == np.int16:
            samples = raw.astype(np.float64) / 32768.0
        elif raw.dtype == np.int32:
            samples = raw.astype(np.float64) / 2147483648.0
        elif raw.dtype == np.float32:
            samples = raw.astype(np.float64)
        else:
            samples = raw.astype(np.float64)

        # Mix to mono
        if samples.ndim > 1:
            samples = samples.mean(axis=1)

        duration_s = len(samples) / framerate

        # FFT on first 60s max
        max_samples = int(min(duration_s, 60) * framerate)
        chunk = samples[:max_samples]
        fft_mag = np.abs(np.fft.rfft(chunk))
        freqs   = np.fft.rfftfreq(len(chunk), d=1.0 / framerate)

        def band_energy(lo, hi):
            mask = (freqs >= lo) & (freqs < hi)
            return float(np.mean(fft_mag[mask])) if mask.any() else 0.0

        bands = {
            "sub_bass":  band_energy(20,   60),
            "bass":      band_energy(60,   250),
            "midrange":  band_energy(250,  2000),
            "presence":  band_energy(2000, 8000),
            "brilliance":band_energy(8000, 20000),
        }

        # Normalise each band 0–1
        max_e = max(bands.values()) or 1.0
        for k in bands:
            bands[k] = bands[k] / max_e

        # Rough BPM via autocorrelation on amplitude envelope
        hop = 512
        envelope = np.array([
            np.sqrt(np.mean(chunk[i:i+hop]**2))
            for i in range(0, len(chunk) - hop, hop)
        ])
        corr = np.correlate(envelope, envelope, mode="full")
        corr = corr[len(corr)//2:]
        # Search 60–180 BPM range
        bpm_lo = int(framerate / hop * 60 / 180)
        bpm_hi = int(framerate / hop * 60 / 60)
        bpm_lo = max(1, bpm_lo)
        bpm_hi = min(len(corr) - 1, bpm_hi)
        peak   = np.argmax(corr[bpm_lo:bpm_hi]) + bpm_lo
        bpm    = (framerate / hop) * 60.0 / peak if peak > 0 else 120.0

        bands["tempo_bpm"]  = round(bpm, 1)
        bands["duration_s"] = round(duration_s, 1)
        print(f"[audio] Analysed: {duration_s:.1f}s  BPM≈{bpm:.0f}  "
              f"bass={bands['bass']:.2f}  mid={bands['midrange']:.2f}")
        return bands

    except Exception as e:
        print(f"[audio] Analysis failed ({e}) — using default weights.")
        return default

# ─────────────────────────────────────────────────────────────
# TERRAIN GENERATION
# ─────────────────────────────────────────────────────────────

def generate_terrain(size: int, seed: int, weights: dict,
                     water_level: float = 0.20) -> np.ndarray:
    """
    Combines multiple noise layers weighted by audio band energies.
    water_level: 0.0-0.5 — height below which terrain is ocean.
      0.0 = no water (full landmass), 0.5 = heavily flooded.
      Default 0.20 = normal island with ocean border.
    Returns float64 array normalised to [0, 1].
    """
    w = weights

    # Layer 1 — large elevation (sub_bass drives amplitude)
    elevation = octave_noise(size, octaves=8, persistence=0.5,
                             lacunarity=2.0,
                             scale=3.0 + w["sub_bass"] * 2.0,
                             seed=seed)

    # Layer 2 — rolling roughness (bass drives frequency)
    roughness = octave_noise(size, octaves=6, persistence=0.6,
                             lacunarity=2.1,
                             scale=6.0 + w["bass"] * 3.0,
                             seed=seed + 1)

    # Layer 3 — terrain detail (midrange)
    detail = octave_noise(size, octaves=4, persistence=0.45,
                          lacunarity=2.0,
                          scale=12.0,
                          seed=seed + 2)

    terrain = elevation * 0.60 + roughness * 0.30 + detail * 0.10

    # Radial island mask — ocean border guaranteed
    cx = cy = size / 2.0
    ys, xs = np.ogrid[:size, :size]
    dist = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    mask = np.clip(1.0 - (dist / (size * 0.44))**3, 0.0, 1.0)
    terrain = terrain * mask

    # Smooth before redistribution to avoid sharp quantisation edges
    terrain = gaussian_filter(terrain, sigma=2.0)

    # Normalise to [0, 1]
    lo, hi = terrain.min(), terrain.max()
    terrain = (terrain - lo) / (hi - lo + 1e-9)

    # Redistribute land pixels to fill full [0.20, 1.0] range
    # This guarantees biome coverage regardless of noise seed
    land_mask = mask > 0.15
    land_vals = terrain[land_mask]
    ranks = np.argsort(np.argsort(land_vals))
    norm = ranks / (len(land_vals) - 1.0)
    terrain[land_mask] = 0.20 + norm * 0.80
    # Ocean pixels stay near 0 naturally

    # Flatten central town plateau
    town_r = int(size * 0.06)
    town_cx = int(size * 0.5)
    town_cy = int(size * 0.5)
    r0 = max(0, town_cy - town_r)
    r1 = min(size, town_cy + town_r)
    c0 = max(0, town_cx - town_r)
    c1 = min(size, town_cx + town_r)
    ty, tx = np.mgrid[r0:r1, c0:c1]
    td = np.sqrt((tx - town_cx)**2 + (ty - town_cy)**2)
    blend = np.clip(td / town_r, 0.0, 1.0)
    target_h = 0.38
    terrain[r0:r1, c0:c1] = (
        terrain[r0:r1, c0:c1] * blend + target_h * (1.0 - blend)
    )

    # Water level — clamp anything below threshold to flat ocean floor
    # Creates hard coastline, inner lakes, rivers where terrain dips
    if water_level > 0.0:
        below_water = terrain < water_level
        # Flatten to a shallow ocean-floor value (slightly below water line)
        terrain[below_water] = water_level * 0.5

    return terrain


# ─────────────────────────────────────────────────────────────
# MOISTURE MAP — second noise layer for biome classification
# ─────────────────────────────────────────────────────────────

def generate_moisture(size: int, seed: int) -> np.ndarray:
    m = octave_noise(size, octaves=6, persistence=0.5,
                     lacunarity=2.0, scale=3.0, seed=seed + 99)
    lo, hi = m.min(), m.max()
    return (m - lo) / (hi - lo + 1e-9)

# ─────────────────────────────────────────────────────────────
# BIOME CLASSIFICATION
# Returns int array: 0=Ocean 1=Plains 2=Forest 3=Highland 4=Mountain 5=Peak
# ─────────────────────────────────────────────────────────────

BIOME_OCEAN     = 0
BIOME_PLAINS    = 1
BIOME_FOREST    = 2
BIOME_HIGHLAND  = 3
BIOME_MOUNTAIN  = 4
BIOME_PEAK      = 5
BIOME_FARM      = 6   # Farm town cluster — adjacent to town, all plots here

BIOME_NAMES = {
    0: "Ocean", 1: "Plains", 2: "Forest",
    3: "Highland", 4: "Mountain", 5: "Peak", 6: "Farm Town"
}

BIOME_COLOURS = {
    0: (30,  80,  150),   # Ocean — blue
    1: (160, 210, 100),   # Plains — light green
    2: (60,  140,  60),   # Forest — dark green
    3: (140, 170, 100),   # Highland — olive
    4: (120, 100,  80),   # Mountain — brown
    5: (240, 240, 240),   # Peak — white/snow
    6: (210, 160,  60),   # Farm Town — warm amber/earth
}

# Zone tier per biome (matches zone_manager tiers)
BIOME_ZONE_TIER = {
    0: 0,  # Ocean — safe/unreachable
    1: 1,  # Plains — open world
    2: 1,  # Forest — open world
    3: 2,  # Highland — mid
    4: 3,  # Mountain — hard
    5: 4,  # Peak — nightmare
    6: 0,  # Farm Town — safe zone (home base)
}

def classify_biomes(height: np.ndarray, moisture: np.ndarray,
                    water_level: float = 0.20) -> np.ndarray:
    biome = np.zeros(height.shape, dtype=np.int32)
    wl = water_level
    # Ocean — below water line
    biome[height < wl] = BIOME_OCEAN
    # Plains / Forest — low land (water_level to water_level+0.20)
    low_lo = wl
    low_hi = wl + 0.20
    mid_hi = wl + 0.38
    low = (height >= low_lo) & (height < low_hi)
    biome[low] = np.where(moisture[low] > 0.55, BIOME_FOREST, BIOME_PLAINS)
    # Plains / Forest — mid land
    mid = (height >= low_hi) & (height < mid_hi)
    biome[mid] = np.where(moisture[mid] > 0.45, BIOME_FOREST, BIOME_PLAINS)
    # Highland
    biome[(height >= mid_hi) & (height < mid_hi + 0.16)] = BIOME_HIGHLAND
    # Mountain
    biome[(height >= mid_hi + 0.16) & (height < mid_hi + 0.30)] = BIOME_MOUNTAIN
    # Peak
    biome[height >= mid_hi + 0.30] = BIOME_PEAK
    return biome


# ─────────────────────────────────────────────────────────────
# FARM CLUSTER FINDER
# Places all plots in a single tight cluster adjacent to town.
# cluster_angle_deg: compass direction from town (0=N, 90=E, 180=S, 270=W)
# cluster_spread: 0.5=tight grid, 1.5=loose spread
# Returns (positions, cluster_center, cluster_radius_px)
# ─────────────────────────────────────────────────────────────

def find_plot_positions(height: np.ndarray, biome: np.ndarray,
                        n_plots: int, size: int,
                        min_spacing: int = 28,
                        cluster_angle_deg: float = 135.0,
                        cluster_spread: float = 1.0) -> list:
    """
    Places all N farm plots in a single geographic cluster adjacent to town.
    All plots end up in the BIOME_FARM zone (painted separately).
    cluster_angle_deg: direction from town center (0=North, 90=East etc)
    cluster_spread: multiplier on plot spacing — tighter = more village-like
    """
    cx = cy = size // 2

    # Convert compass angle to pixel direction
    # 0=N means row decreases (up in image), 90=E means col increases
    angle_rad = math.radians(cluster_angle_deg)
    dir_col =  math.sin(angle_rad)   # East component
    dir_row = -math.cos(angle_rad)   # North component (row decreases going N)

    # Cluster center — place it just outside town plateau
    # Town radius ~6% of size, cluster starts at ~14%, center at ~22%
    cluster_dist = size * 0.20
    cluster_cx = int(cx + dir_col * cluster_dist)
    cluster_cy = int(cy + dir_row * cluster_dist)
    cluster_cx = max(min_spacing, min(size - min_spacing, cluster_cx))
    cluster_cy = max(min_spacing, min(size - min_spacing, cluster_cy))

    # Grid layout — arrange plots in a near-square grid around cluster center
    cols_in_grid = max(1, int(math.ceil(math.sqrt(n_plots))))
    rows_in_grid = max(1, int(math.ceil(n_plots / cols_in_grid)))
    step = int(min_spacing * cluster_spread)

    # Offset grid so it's centered on cluster_cx, cluster_cy
    grid_w = (cols_in_grid - 1) * step
    grid_h = (rows_in_grid - 1) * step
    start_col = cluster_cx - grid_w // 2
    start_row = cluster_cy - grid_h // 2

    positions = []
    for gi in range(n_plots):
        gr = gi // cols_in_grid
        gc = gi % cols_in_grid
        rc = start_row + gr * step
        cc = start_col + gc * step
        # Clamp to valid image bounds
        rc = max(2, min(size - 2, rc))
        cc = max(2, min(size - 2, cc))
        positions.append((rc, cc))

    return positions


def get_farm_cluster_info(positions: list, size: int) -> dict:
    """Returns center pixel and radius of the farm cluster."""
    if not positions:
        return {"cx": size//2, "cy": size//2, "radius_px": 0}
    rows = [p[0] for p in positions]
    cols = [p[1] for p in positions]
    cy = int(np.mean(rows))
    cx = int(np.mean(cols))
    dists = [math.sqrt((r-cy)**2 + (c-cx)**2) for r,c in positions]
    radius = int(max(dists) + 20) if dists else 20
    return {"cx": cx, "cy": cy, "radius_px": radius}


def paint_farm_biome(biome: np.ndarray, positions: list,
                     size: int, padding: int = 18) -> np.ndarray:
    """
    Overwrites a circular region around the farm cluster with BIOME_FARM.
    This creates the distinct farm town biome zone on the map.
    """
    info = get_farm_cluster_info(positions, size)
    cx, cy = info["cx"], info["cy"]
    radius = info["radius_px"] + padding
    ys, xs = np.ogrid[:size, :size]
    dist = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    biome = biome.copy()
    biome[dist <= radius] = BIOME_FARM
    return biome

# ─────────────────────────────────────────────────────────────
# PIXEL → UEFN WORLD COORDINATE CONVERSION
# UEFN island = 2017×2017m, pixel 0,0 = world -100850, -100850
# (assuming 1009 pixel heightmap with 200cm/pixel scale)
# ─────────────────────────────────────────────────────────────

def pixel_to_world(row: int, col: int, size: int,
                   world_size_cm: int = 201700) -> tuple:
    """Returns (X, Y, Z) in UEFN world units (cm)."""
    half = world_size_cm / 2.0
    cell = world_size_cm / size
    x = col * cell - half
    y = row * cell - half
    return (round(x), round(y), 0)

# ─────────────────────────────────────────────────────────────
# LAYOUT JSON GENERATION
# ─────────────────────────────────────────────────────────────

def build_layout(height: np.ndarray, biome: np.ndarray,
                 plot_positions: list, size: int, seed: int,
                 weights: dict, water_level: float = 0.20,
                 world_wrap: bool = True) -> dict:
    cx = cy = size // 2
    town_world = pixel_to_world(cy, cx, size)

    # Farm cluster info
    farm_info = get_farm_cluster_info(plot_positions, size)
    farm_wx, farm_wy, farm_wz = pixel_to_world(farm_info["cy"], farm_info["cx"], size)
    farm_radius_cm = int(farm_info["radius_px"] / size * 201700)

    # Zone tier boundaries — radial rings mapped to biome tiers
    zone_radii_pct = [0.0, 0.18, 0.30, 0.42, 0.54]
    zone_tiers = []
    for i in range(len(zone_radii_pct) - 1):
        r_inner = zone_radii_pct[i]
        r_outer = zone_radii_pct[i + 1]
        center_w = pixel_to_world(cy, cx, size)
        radius_cm = int(r_outer * 201700 / 2)
        zone_tiers.append({
            "zone_index": i,
            "tier": i + 1,
            "center_x": center_w[0],
            "center_y": center_w[1],
            "radius_cm": radius_cm,
            "biome_hint": BIOME_NAMES.get(i + 1, "Plains"),
        })

    # Plot positions
    plots = []
    for i, (row, col) in enumerate(plot_positions):
        wx, wy, _ = pixel_to_world(row, col, size)
        h_val = float(height[row, col])
        b_val = int(biome[row, col])
        plots.append({
            "plot_index": i,
            "pixel_row": int(row),
            "pixel_col": int(col),
            "world_x_cm": wx,
            "world_y_cm": wy,
            "world_z_cm": int(h_val * 50000),  # Z scale 500m range
            "biome": BIOME_NAMES.get(b_val, "Plains"),
            "zone_tier": BIOME_ZONE_TIER.get(b_val, 1),
        })

    # Biome distribution summary
    total = float(size * size)
    biome_pct = {
        BIOME_NAMES[b]: round(float(np.sum(biome == b)) / total * 100, 1)
        for b in BIOME_NAMES
    }

    return {
        "meta": {
            "seed": seed,
            "size_px": size,
            "world_size_cm": 201700,
            "audio_weights": weights,
            "n_plots": len(plots),
            "water_level": water_level,
            "world_wrap": world_wrap,
        },
        "town_center": {
            "world_x_cm": town_world[0],
            "world_y_cm": town_world[1],
            "world_z_cm": int(float(height[cy, cx]) * 50000),
        },
        "zone_tiers": zone_tiers,
        "farm_cluster": {
            "world_x_cm": farm_wx,
            "world_y_cm": farm_wy,
            "world_z_cm": farm_wz,
            "radius_cm":  farm_radius_cm,
            "n_plots":    len(plots),
        },
        "plots": plots,
        "biome_distribution_pct": biome_pct,
        "verse_constants": {
            "comment": "Paste these into plot_registry.verse",
            "PLOT_COUNT": len(plots),
            "WORLD_SIZE_CM": 201700,
            "TOWN_X": town_world[0],
            "TOWN_Y": town_world[1],
            "WORLD_WRAP": world_wrap,
            "WATER_LEVEL_NORMALIZED": round(water_level, 3),
            "FARM_CENTER_X": farm_wx,
            "FARM_CENTER_Y": farm_wy,
            "FARM_RADIUS_CM": farm_radius_cm,
            "PLOT_POSITIONS": [
                [p["world_x_cm"], p["world_y_cm"], p["world_z_cm"]]
                for p in plots
            ],
            "ZONE_TIER_RADII_CM": [z["radius_cm"] for z in zone_tiers],
        }
    }

# ─────────────────────────────────────────────────────────────
# PREVIEW IMAGE
# ─────────────────────────────────────────────────────────────

def build_preview(height: np.ndarray, biome: np.ndarray,
                  plot_positions: list, size: int) -> np.ndarray:
    """Returns HxWx3 uint8 RGB array."""
    rgb = np.zeros((size, size, 3), dtype=np.uint8)

    for b_id, colour in BIOME_COLOURS.items():
        mask = biome == b_id
        rgb[mask] = colour

    # Ocean depth shading — deeper = darker blue
    ocean_mask = biome == BIOME_OCEAN
    if ocean_mask.any():
        depth = 1.0 - height  # invert — lower height = deeper
        deep_col  = np.array([15,  40, 120], dtype=np.float32)
        shore_col = np.array([50, 120, 200], dtype=np.float32)
        d = depth[ocean_mask][:, np.newaxis]
        rgb[ocean_mask] = np.clip(shore_col * (1-d) + deep_col * d, 0, 255).astype(np.uint8)

    # Shade by height
    shade = (height * 0.4 + 0.6)
    rgb = np.clip(rgb * shade[:, :, np.newaxis], 0, 255).astype(np.uint8)

    # Draw plot markers — red 5×5 squares
    for row, col in plot_positions:
        r0 = max(0, row - 3)
        r1 = min(size, row + 3)
        c0 = max(0, col - 3)
        c1 = min(size, col + 3)
        rgb[r0:r1, c0:c1] = (220, 40, 40)

    # Town center marker — yellow
    cx = cy = size // 2
    rgb[cy-5:cy+5, cx-5:cx+5] = (240, 220, 40)

    return rgb

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate UEFN heightmap + island layout from audio or seed"
    )
    parser.add_argument("--audio",   type=str, default=None,
                        help="Path to .wav audio file (optional)")
    parser.add_argument("--seed",    type=int, default=42,
                        help="Random seed for noise generation (default 42)")
    parser.add_argument("--size",    type=int, default=1009,
                        choices=[513, 1009, 2017],
                        help="Heightmap resolution (default 1009)")
    parser.add_argument("--plots",   type=int, default=32,
                        help="Number of farm plots to place (default 32)")
    parser.add_argument("--output",  type=str, default="island",
                        help="Output filename prefix (default 'island')")
    parser.add_argument("--preview", action="store_true",
                        help="Save RGB preview image")
    parser.add_argument("--spacing", type=int, default=40,
                        help="Min pixel spacing between plots (default 40)")
    args = parser.parse_args()

    print(f"[gen] Seed={args.seed}  Size={args.size}×{args.size}  "
          f"Plots={args.plots}")

    # Step 1 — Audio analysis
    if args.audio:
        print(f"[gen] Analysing audio: {args.audio}")
        weights = analyse_audio(args.audio)
    else:
        print("[gen] No audio — using default weights")
        weights = {
            "sub_bass": 0.5, "bass": 0.5, "midrange": 0.5,
            "presence": 0.5, "brilliance": 0.5,
            "tempo_bpm": 120.0, "duration_s": 0.0,
        }

    # Step 2 — Terrain + moisture
    print("[gen] Generating terrain...")
    height   = generate_terrain(args.size, args.seed, weights)
    moisture = generate_moisture(args.size, args.seed)

    # Step 3 — Biome classification
    print("[gen] Classifying biomes...")
    biome = classify_biomes(height, moisture)

    # Step 4 — Plot positions
    print(f"[gen] Finding {args.plots} plot positions...")
    plots = find_plot_positions(height, biome, args.plots,
                                args.size, args.spacing)
    print(f"[gen] Found {len(plots)} plot positions")

    # Step 5 — Layout JSON
    print("[gen] Building layout JSON...")
    layout = build_layout(height, biome, plots, args.size, args.seed, weights)

    # Step 6 — Heightmap PNG (16-bit grayscale)
    print("[gen] Saving heightmap PNG...")
    hm_16 = (height * 65535).astype(np.uint16)
    hm_img = Image.fromarray(hm_16)
    hm_path = f"{args.output}_heightmap.png"
    hm_img.save(hm_path)
    print(f"[out] Heightmap: {hm_path}")

    # Step 7 — Layout JSON
    json_path = f"{args.output}_layout.json"
    with open(json_path, "w") as f:
        json.dump(layout, f, indent=2)
    print(f"[out] Layout:    {json_path}")

    # Step 8 — Preview
    if args.preview:
        print("[gen] Saving preview image...")
        preview_rgb = build_preview(height, biome, plots, args.size)
        prev_img = Image.fromarray(preview_rgb, mode="RGB")
        prev_path = f"{args.output}_preview.png"
        prev_img.save(prev_path)
        print(f"[out] Preview:   {prev_path}")

    # Step 9 — Print Verse constants summary
    vc = layout["verse_constants"]
    print("\n── Verse Constants (paste into plot_registry.verse) ──")
    print(f"  PLOT_COUNT    : {vc['PLOT_COUNT']}")
    print(f"  TOWN_X        : {vc['TOWN_X']}")
    print(f"  TOWN_Y        : {vc['TOWN_Y']}")
    print(f"  ZONE_RADII_CM : {vc['ZONE_TIER_RADII_CM']}")
    print(f"  Biome spread  : {layout['biome_distribution_pct']}")
    print("──────────────────────────────────────────────────────")
    print("[done]")


if __name__ == "__main__":
    main()
