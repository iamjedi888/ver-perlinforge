"""
town_generator.py  —  Island Forge v3.0
========================================
Generates a Fortnite-realistic town layout that mirrors how Epic structures
named locations like Pleasant Park, Sweaty Sands, Dirty Docks, etc.

Real Fortnite town characteristics (measured from Pleasant Park / Salty Springs):
  - Town footprint:  ~350m × 350m  (35000 cm × 35000 cm)
  - Street grid:     3–4 streets each direction, ~80–100m apart
  - House lots:      ~28m × 28m  (2800 cm × 2800 cm)
  - House spacing:   ~10–14m gaps between buildings
  - Central feature: Park / plaza / landmark (~60m × 60m)
  - Outer ring:      Larger buildings (barn, warehouse, shop) on perimeter
  - Terrain:         Town sits on a gently RAISED flat pad (+2–4m above surroundings)
  - Road width:      ~6m (600 cm) paved paths between blocks

World scale:
  - Full Chapter 2 map: 550000 cm × 550000 cm  (5.5km × 5.5km)
  - Heightmap pixel at size=1025: each pixel = 550000/1025 ≈ 537 cm ≈ 5.4m
  - Town 35000cm × 35000cm = ~65 × 65 pixels at that resolution — tight but correct

This module produces:
  - plot_positions:  list of (row, col) pixel coords for each farm plot
  - town_data:       full structured JSON describing streets, lots, buildings
  - town_mask:       bool array — pixels that belong to the town footprint
  - street_mask:     bool array — pixels that are paved road
  - lot_mask:        bool array — pixels that are building lots (should be flat)
  - plaza_mask:      bool array — central plaza/park

The heightmap pipeline uses these masks to:
  1. Flatten the entire town pad to a consistent elevation
  2. Slightly raise the pad above surroundings (natural town hill)
  3. Paint roads a slightly lower elevation (drainage)
  4. Assign BIOME_TOWN to all town pixels
"""

import math
import numpy as np
from scipy.ndimage import gaussian_filter

# ─────────────────────────────────────────────────────────────
# WORLD CONSTANTS  (must match audio_to_heightmap.py)
# ─────────────────────────────────────────────────────────────

WORLD_SIZE_CM  = 100_000   # UEFN Creative island: 1km × 1km (max island size)
MAP_SIZE_PX    = 1025      # Default heightmap resolution
CM_PER_PX      = WORLD_SIZE_CM / MAP_SIZE_PX   # ≈537 cm per pixel

# Town physical dimensions (cm)
TOWN_SIZE_CM        = 36_000    # 360m × 360m footprint
STREET_WIDTH_CM     = 700       # 7m wide streets
BLOCK_SIZE_CM       = 9_000     # 90m between street centerlines
HOUSE_LOT_CM        = 2_400     # 24m × 24m house lot
HOUSE_SETBACK_CM    = 400       # 4m setback from street edge
PLAZA_SIZE_CM       = 6_500     # 65m × 65m central park/plaza
OUTER_RING_CM       = 3_200     # outer buildings are 32m wide

# Derived in pixels (at MAP_SIZE_PX=1025, CM_PER_PX≈537)
def cm_to_px(cm, size=MAP_SIZE_PX):
    cpp = WORLD_SIZE_CM / size
    return max(1, int(round(cm / cpp)))

# ─────────────────────────────────────────────────────────────
# TOWN PLACEMENT
# ─────────────────────────────────────────────────────────────

def find_town_center(height, island_mask, size, seed,
                     cluster_angle_deg=135.0, cluster_spread=0.22):
    """
    Find the best pixel to place the town center.
    Criteria (in order):
      1. Well inside the island (island_mask > 0.6)
      2. Flat enough for a town pad (low slope)
      3. Not too close to the island edge
      4. Offset from map center — towns are never dead center
    Returns (row, col) of town center pixel.
    """
    rng = np.random.default_rng(seed + 42000)
    cy, cx = size // 2, size // 2

    # Target location based on cluster angle
    angle_rad = math.radians(cluster_angle_deg)
    target_row = int(np.clip(cy + math.sin(angle_rad) * cluster_spread * size,
                             size // 6, 5 * size // 6))
    target_col = int(np.clip(cx + math.cos(angle_rad) * cluster_spread * size,
                             size // 6, 5 * size // 6))

    # Flatness score
    gy, gx = np.gradient(height)
    slope = np.sqrt(gy**2 + gx**2)
    flat_score = 1.0 / (1.0 + slope * 60)

    # Search radius around target
    search_r = int(size * 0.12)
    best_score = -1
    best_pos   = (target_row, target_col)

    for _ in range(800):
        dr = rng.integers(-search_r, search_r + 1)
        dc = rng.integers(-search_r, search_r + 1)
        r  = int(np.clip(target_row + dr, size // 8, 7 * size // 8))
        c  = int(np.clip(target_col + dc, size // 8, 7 * size // 8))

        if island_mask[r, c] < 0.60:
            continue
        if height[r, c] < 0.25 or height[r, c] > 0.65:
            continue

        # Ensure entire town footprint fits on land
        town_r = cm_to_px(TOWN_SIZE_CM // 2, size)
        rmin = r - town_r; rmax = r + town_r
        cmin = c - town_r; cmax = c + town_r
        if rmin < 0 or rmax >= size or cmin < 0 or cmax >= size:
            continue
        footprint_mask = island_mask[rmin:rmax, cmin:cmax]
        if footprint_mask.min() < 0.45:
            continue

        # Score: flatness + closeness to target
        fs = float(flat_score[r, c])
        dist_to_target = math.hypot(r - target_row, c - target_col) / search_r
        score = fs * 0.7 + (1 - dist_to_target) * 0.3

        if score > best_score:
            best_score = score
            best_pos   = (r, c)

    return best_pos

# ─────────────────────────────────────────────────────────────
# STREET GRID BUILDER
# ─────────────────────────────────────────────────────────────

def build_street_grid(town_center_row, town_center_col, size,
                      n_streets_x=4, n_streets_y=4, rotation_deg=0.0):
    """
    Build a realistic street grid centred on town_center.
    
    Returns:
      streets: list of dict {axis, position_px, name, width_px}
      blocks:  list of dict {row_min, row_max, col_min, col_max, block_id}
    """
    cpp   = WORLD_SIZE_CM / size
    half  = (TOWN_SIZE_CM // 2)

    # Street positions in cm relative to town center
    # 4 streets each direction = 3 blocks between them
    # Streets at: -1.5B, -0.5B, +0.5B, +1.5B  (B = BLOCK_SIZE_CM)
    # Plus outer boundary streets at ±2B
    street_offsets_cm = []
    n_blocks = n_streets_x - 1   # spaces between streets
    for i in range(n_streets_x):
        offset = -((n_blocks / 2.0) * BLOCK_SIZE_CM) + i * BLOCK_SIZE_CM
        street_offsets_cm.append(offset)

    # Convert cm offsets to pixel offsets
    street_offsets_px = [int(round(o / cpp)) for o in street_offsets_cm]

    # Street width in pixels
    sw = max(2, cm_to_px(STREET_WIDTH_CM, size))

    streets = []
    street_names_ew = ["North Ave", "Oak Street", "Main Street", "South Blvd"]
    street_names_ns = ["West Lane", "Park Road", "East Ave", "Harbor St"]

    # East-West streets (constant row)
    for i, off_px in enumerate(street_offsets_px):
        row = town_center_row + off_px
        if 0 <= row < size:
            streets.append({
                "axis":      "EW",
                "row":       row,
                "col":       None,
                "name":      street_names_ew[i % len(street_names_ew)],
                "width_px":  sw,
                "offset_cm": street_offsets_cm[i],
            })

    # North-South streets (constant col)
    for i, off_px in enumerate(street_offsets_px):
        col = town_center_col + off_px
        if 0 <= col < size:
            streets.append({
                "axis":      "NS",
                "row":       None,
                "col":       col,
                "name":      street_names_ns[i % len(street_names_ns)],
                "width_px":  sw,
                "offset_cm": street_offsets_cm[i],
            })

    # Build block list (rectangles between streets)
    ew_rows = sorted([s["row"] for s in streets if s["axis"] == "EW"])
    ns_cols = sorted([s["col"] for s in streets if s["axis"] == "NS"])

    blocks = []
    bid    = 0
    for ri in range(len(ew_rows) - 1):
        for ci in range(len(ns_cols) - 1):
            row_min = ew_rows[ri]  + sw
            row_max = ew_rows[ri+1] - sw
            col_min = ns_cols[ci]  + sw
            col_max = ns_cols[ci+1] - sw
            if row_max > row_min and col_max > col_min:
                blocks.append({
                    "id":      bid,
                    "row_min": row_min,
                    "row_max": row_max,
                    "col_min": col_min,
                    "col_max": col_max,
                    "center_row": (row_min + row_max) // 2,
                    "center_col": (col_min + col_max) // 2,
                })
                bid += 1

    return streets, blocks

# ─────────────────────────────────────────────────────────────
# LOT PLACEMENT WITHIN BLOCKS
# ─────────────────────────────────────────────────────────────

BLOCK_TYPE_RESIDENTIAL = "residential"
BLOCK_TYPE_PLAZA       = "plaza"
BLOCK_TYPE_COMMERCIAL  = "commercial"
BLOCK_TYPE_INDUSTRIAL  = "industrial"
BLOCK_TYPE_FARM        = "farm"

def classify_blocks(blocks, town_center_row, town_center_col):
    """
    Assign each block a type based on its position relative to town center.
    Matches how Fortnite layouts work:
      - Center block(s): plaza/park
      - Inner ring: commercial (shops, gas station)
      - Mid ring: residential (houses)
      - Outer blocks: industrial/farm (barn, dock, warehouse)
    """
    if not blocks:
        return blocks

    # Find the block closest to town center — that's the plaza
    def dist_to_center(b):
        return math.hypot(b["center_row"] - town_center_row,
                          b["center_col"] - town_center_col)

    dists   = [dist_to_center(b) for b in blocks]
    max_d   = max(dists) if dists else 1
    min_d   = min(dists) if dists else 0

    for b, d in zip(blocks, dists):
        norm = (d - min_d) / (max_d - min_d + 1e-9)
        if norm < 0.10:
            b["type"] = BLOCK_TYPE_PLAZA
        elif norm < 0.45:
            b["type"] = BLOCK_TYPE_COMMERCIAL
        elif norm < 0.78:
            b["type"] = BLOCK_TYPE_RESIDENTIAL
        else:
            b["type"] = BLOCK_TYPE_INDUSTRIAL

    return blocks

def place_lots_in_block(block, size, lot_type="residential", rng=None):
    """
    Fill a block with tight lots like Fortnite does.
    Residential: rows of houses facing the street, small gap between.
    Commercial:  fewer, larger footprints.
    Industrial:  1-2 large buildings.
    Plaza:       open space with a few tree/prop markers.
    
    Returns list of lot dicts: {row, col, width_px, height_px, type, facing}
    """
    if rng is None:
        rng = np.random.default_rng(42)

    cpp         = WORLD_SIZE_CM / size
    brow_span   = block["row_max"] - block["row_min"]
    bcol_span   = block["col_max"] - block["col_min"]

    lots = []

    if lot_type == BLOCK_TYPE_PLAZA:
        # Just mark the center — plaza is open, no lots
        return []

    elif lot_type == BLOCK_TYPE_RESIDENTIAL:
        # Pack houses in a grid: 2 rows × N columns
        # Fortnite house lots: ~24m wide, ~5m gap — tightly packed
        lot_w_px = max(2, cm_to_px(HOUSE_LOT_CM, size))
        lot_h_px = max(2, cm_to_px(HOUSE_LOT_CM, size))
        gap_px   = max(1, cm_to_px(400, size))    # 4m gap between houses
        setb_px  = max(1, cm_to_px(300, size))    # small setback

        # How many fit? — no cap, fill the whole block like Fortnite does
        avail_w  = bcol_span - setb_px * 2
        avail_h  = brow_span - setb_px * 2
        cols_fit = max(1, (avail_w + gap_px) // (lot_w_px + gap_px))
        rows_fit = max(1, (avail_h + gap_px) // (lot_h_px + gap_px))

        # Fortnite: 2-3 rows of houses per block, up to 6 wide
        cols_fit = min(cols_fit, 6)
        rows_fit = min(rows_fit, 3)

        total_w = cols_fit * lot_w_px + (cols_fit - 1) * gap_px
        total_h = rows_fit * lot_h_px + (rows_fit - 1) * gap_px
        start_c = block["col_min"] + setb_px + (bcol_span - total_w) // 2
        start_r = block["row_min"] + setb_px + (brow_span - total_h) // 2

        for ri in range(rows_fit):
            for ci in range(cols_fit):
                lr = start_r + ri * (lot_h_px + gap_px)
                lc = start_c + ci * (lot_w_px + gap_px)
                lr = int(np.clip(lr, block["row_min"], block["row_max"] - lot_h_px))
                lc = int(np.clip(lc, block["col_min"], block["col_max"] - lot_w_px))
                lots.append({
                    "row":      lr,
                    "col":      lc,
                    "row_end":  lr + lot_h_px,
                    "col_end":  lc + lot_w_px,
                    "width_px": lot_w_px,
                    "height_px":lot_h_px,
                    "type":     "house",
                    "block_id": block["id"],
                })

    elif lot_type == BLOCK_TYPE_COMMERCIAL:
        # Larger lots, fewer of them — shop, diner, gas station
        lot_w_px = max(2, cm_to_px(3500, size))   # 35m wide commercial
        lot_h_px = max(2, cm_to_px(2800, size))
        gap_px   = max(1, cm_to_px(600, size))
        setb_px  = max(1, cm_to_px(300, size))

        cols_fit = max(1, min(3, (bcol_span - setb_px * 2 + gap_px) // (lot_w_px + gap_px)))
        rows_fit = 1

        total_w = cols_fit * lot_w_px + (cols_fit - 1) * gap_px
        start_c = block["col_min"] + setb_px + (bcol_span - total_w) // 2
        start_r = block["row_min"] + setb_px

        commercial_types = ["shop", "diner", "gas_station", "market", "clinic"]
        for ci in range(cols_fit):
            lc = int(start_c + ci * (lot_w_px + gap_px))
            lr = int(start_r)
            lots.append({
                "row":      lr,
                "col":      lc,
                "row_end":  lr + lot_h_px,
                "col_end":  lc + lot_w_px,
                "width_px": lot_w_px,
                "height_px":lot_h_px,
                "type":     commercial_types[ci % len(commercial_types)],
                "block_id": block["id"],
            })

    elif lot_type == BLOCK_TYPE_INDUSTRIAL:
        # 1-2 large structures: barn, warehouse, factory
        lot_w_px = max(3, int(bcol_span * 0.7))
        lot_h_px = max(3, int(brow_span * 0.7))
        start_c  = block["col_min"] + (bcol_span - lot_w_px) // 2
        start_r  = block["row_min"] + (brow_span - lot_h_px) // 2
        ind_types = ["barn", "warehouse", "silo", "dock"]
        lots.append({
            "row":      int(start_r),
            "col":      int(start_c),
            "row_end":  int(start_r + lot_h_px),
            "col_end":  int(start_c + lot_w_px),
            "width_px": lot_w_px,
            "height_px":lot_h_px,
            "type":     rng.choice(ind_types),
            "block_id": block["id"],
        })

    return lots

# ─────────────────────────────────────────────────────────────
# FARM PLOTS  — placed just outside town boundary
# ─────────────────────────────────────────────────────────────

def place_farm_plots(town_center_row, town_center_col, size,
                     n_plots=32, seed=42):
    """
    Farm plots go in a cluster DIRECTLY OUTSIDE the town boundary,
    like the farm fields you see on the edge of every Fortnite named location.
    
    Layout: organised rows of rectangular plots, like real farmland.
    Each plot is a 32m × 32m square (3200 cm), spaced 8m apart (800 cm).
    They form a grid cluster, offset from town in one direction.
    
    Returns list of (row, col) plot center pixels.
    """
    rng          = np.random.default_rng(seed + 11000)
    cpp          = WORLD_SIZE_CM / size

    plot_size_cm = 3_200    # 32m plot
    plot_gap_cm  = 900      # 9m between plots
    plot_step_cm = plot_size_cm + plot_gap_cm   # 41m center-to-center

    plot_px_size = max(2, int(plot_size_cm / cpp))
    plot_step_px = max(3, int(plot_step_cm / cpp))

    # Farm cluster offset from town center
    # Pick a direction — usually toward one edge of the island
    farm_angle   = rng.uniform(0, 2 * math.pi)
    town_r_px    = max(10, cm_to_px(TOWN_SIZE_CM // 2, size))
    # Start farm right at edge of town, 1 block gap
    gap_from_town_px = max(4, cm_to_px(2_000, size))   # 20m gap
    farm_origin_dist = town_r_px + gap_from_town_px

    # Farm origin (corner of grid)
    cols_in_row = max(2, int(math.sqrt(n_plots * 1.5)))   # wider than tall
    rows_in_col = math.ceil(n_plots / cols_in_row)

    # Total farm grid size
    grid_w_px = cols_in_row * plot_step_px
    grid_h_px = rows_in_col * plot_step_px

    # Place farm so its center is at farm_origin_dist from town center
    farm_center_r = town_center_row + int(math.sin(farm_angle) * farm_origin_dist)
    farm_center_c = town_center_col + int(math.cos(farm_angle) * farm_origin_dist)
    farm_center_r = int(np.clip(farm_center_r, grid_h_px // 2 + 2, size - grid_h_px // 2 - 2))
    farm_center_c = int(np.clip(farm_center_c, grid_w_px // 2 + 2, size - grid_w_px // 2 - 2))

    farm_r0 = farm_center_r - grid_h_px // 2
    farm_c0 = farm_center_c - grid_w_px // 2

    positions = []
    for ri in range(rows_in_col):
        for ci in range(cols_in_row):
            if len(positions) >= n_plots:
                break
            pr = farm_r0 + ri * plot_step_px + plot_step_px // 2
            pc = farm_c0 + ci * plot_step_px + plot_step_px // 2
            pr = int(np.clip(pr, 1, size - 2))
            pc = int(np.clip(pc, 1, size - 2))
            positions.append((pr, pc))

    return positions, farm_angle, (farm_center_r, farm_center_c)

# ─────────────────────────────────────────────────────────────
# MASK BUILDERS
# ─────────────────────────────────────────────────────────────

def build_town_masks(streets, blocks, lots, plot_positions, size,
                     farm_center, farm_angle, n_plots=32):
    """
    Rasterise all town geometry into boolean masks.
    Returns:
      town_mask    — everything inside town boundary
      street_mask  — paved road pixels
      lot_mask     — building footprint pixels (flatten + raise slightly)
      plaza_mask   — central open space
      farm_mask    — farm plot pixels
    """
    town_mask   = np.zeros((size, size), dtype=bool)
    street_mask = np.zeros((size, size), dtype=bool)
    lot_mask    = np.zeros((size, size), dtype=bool)
    plaza_mask  = np.zeros((size, size), dtype=bool)
    farm_mask   = np.zeros((size, size), dtype=bool)

    # Street masks
    for s in streets:
        sw_half = s["width_px"] // 2
        if s["axis"] == "EW":
            r0 = max(0, s["row"] - sw_half)
            r1 = min(size, s["row"] + sw_half + 1)
            # Only mark within town column extent
            ns_cols = sorted([st["col"] for st in streets if st["axis"] == "NS"])
            if ns_cols:
                c0 = max(0, min(ns_cols) - sw_half)
                c1 = min(size, max(ns_cols) + sw_half + 1)
                street_mask[r0:r1, c0:c1] = True
        else:
            c0 = max(0, s["col"] - sw_half)
            c1 = min(size, s["col"] + sw_half + 1)
            ew_rows = sorted([st["row"] for st in streets if st["axis"] == "EW"])
            if ew_rows:
                r0 = max(0, min(ew_rows) - sw_half)
                r1 = min(size, max(ew_rows) + sw_half + 1)
                street_mask[r0:r1, c0:c1] = True

    # Lot masks
    for lot in lots:
        r0 = max(0, lot["row"])
        r1 = min(size, lot["row_end"])
        c0 = max(0, lot["col"])
        c1 = min(size, lot["col_end"])
        if r1 > r0 and c1 > c0:
            lot_mask[r0:r1, c0:c1] = True

    # Plaza mask — central open block(s)
    for b in blocks:
        if b.get("type") == BLOCK_TYPE_PLAZA:
            r0 = max(0, b["row_min"]); r1 = min(size, b["row_max"])
            c0 = max(0, b["col_min"]); c1 = min(size, b["col_max"])
            if r1 > r0 and c1 > c0:
                plaza_mask[r0:r1, c0:c1] = True

    # Town footprint = union of all above
    town_mask = street_mask | lot_mask | plaza_mask

    # Expand town mask slightly to include sidewalks and gaps
    from scipy.ndimage import binary_dilation
    struct = np.ones((3, 3), dtype=bool)
    town_mask = binary_dilation(town_mask, structure=struct, iterations=2)

    # Farm mask — rectangular patches around each plot position
    cpp       = WORLD_SIZE_CM / size
    plot_r_px = max(2, int(3_200 / cpp / 2))   # half-width of plot in pixels

    for pr, pc in plot_positions:
        r0 = max(0, pr - plot_r_px); r1 = min(size, pr + plot_r_px)
        c0 = max(0, pc - plot_r_px); c1 = min(size, pc + plot_r_px)
        farm_mask[r0:r1, c0:c1] = True

    return town_mask, street_mask, lot_mask, plaza_mask, farm_mask

# ─────────────────────────────────────────────────────────────
# TERRAIN MODIFICATION
# ─────────────────────────────────────────────────────────────

def apply_town_to_terrain(terrain, town_mask, street_mask,
                          lot_mask, plaza_mask, farm_mask,
                          town_center_row, town_center_col):
    """
    Modify terrain array in-place to reflect town geometry:
      - Entire town pad: raised flat shelf (Fortnite towns sit on slight hills)
      - Streets: slightly lower than lots (drainage, visible contrast)
      - Lots / plaza: perfectly flat at pad elevation
      - Farm area: very flat, slightly lower than town pad
    """
    terrain = np.asarray(terrain, dtype=np.float32)
    size    = terrain.shape[0]

    # Sample target elevation at town center
    tc_elev = float(terrain[town_center_row, town_center_col])
    tc_elev = np.clip(tc_elev, 0.28, 0.58)

    # Town pad elevation — raise slightly above surroundings
    pad_elev    = tc_elev + 0.03
    street_elev = pad_elev - 0.008   # streets drain slightly
    farm_elev   = np.clip(pad_elev - 0.015, 0.22, 0.55)

    # Smooth blend radius for town border
    YY, XX = np.meshgrid(np.arange(size), np.arange(size), indexing='ij')
    dist_to_tc = np.sqrt((YY - town_center_row)**2 + (XX - town_center_col)**2)
    town_r_px  = int(np.sum(town_mask) ** 0.5)  # approx radius

    # Gaussian blend of pad elevation over town footprint
    town_float = town_mask.astype(np.float32, copy=False)
    town_blur  = gaussian_filter(town_float, sigma=max(2, town_r_px * 0.2))
    town_blend = np.clip(town_blur * 3.0, 0, 1)

    # Apply pad elevation blend
    terrain = terrain * (1 - town_blend) + pad_elev * town_blend

    # Streets: slightly recessed
    street_blend = gaussian_filter(street_mask.astype(np.float32, copy=False), sigma=0.8)
    terrain = np.where(street_mask,
                       terrain * 0.1 + street_elev * 0.9,
                       terrain)

    # Lots: precisely flat
    terrain = np.where(lot_mask,
                       terrain * 0.05 + pad_elev * 0.95,
                       terrain)

    # Plaza: flat at pad elevation
    terrain = np.where(plaza_mask,
                       terrain * 0.05 + pad_elev * 0.95,
                       terrain)

    # Farm: gently flat
    farm_blend = gaussian_filter(farm_mask.astype(np.float32, copy=False), sigma=1.5)
    terrain = terrain * (1 - farm_blend * 0.7) + farm_elev * (farm_blend * 0.7)

    # Final smooth of the whole town region to remove seams
    # Only smooth pixels near the town
    near_town = (dist_to_tc < town_r_px * 1.8)
    smoothed  = gaussian_filter(terrain, sigma=1.2)
    blend_near = np.clip((1 - dist_to_tc / (town_r_px * 1.8)), 0, 1) * 0.3
    terrain   = np.where(near_town,
                         terrain * (1 - blend_near) + smoothed * blend_near,
                         terrain)

    return terrain

# ─────────────────────────────────────────────────────────────
# BIOME PAINTING
# ─────────────────────────────────────────────────────────────

# Biome IDs (must match audio_to_heightmap.py)
BIOME_WATER  = 0
BIOME_BEACH  = 1
BIOME_PLAINS = 2
BIOME_FOREST = 3
BIOME_FARM   = 9
BIOME_TOWN   = 10   # new biome for town pixels

def paint_town_biomes(biome, town_mask, street_mask, plaza_mask, farm_mask):
    """
    Overwrite biome array in the town footprint.
    Town pixels → BIOME_TOWN
    Farm pixels → BIOME_FARM
    Water pixels are never overwritten.
    """
    biome = np.asarray(biome)
    not_water = biome != BIOME_WATER

    biome[farm_mask & not_water] = BIOME_FARM
    biome[town_mask & not_water] = BIOME_TOWN

    return biome

# ─────────────────────────────────────────────────────────────
# MAIN ENTRY  — called from generate_terrain pipeline
# ─────────────────────────────────────────────────────────────

def generate_town(terrain, biome, island_mask, size, seed, weights,
                  n_plots=32, cluster_angle_deg=135.0, cluster_spread=0.22):
    """
    Full town generation pipeline.
    
    Args:
        terrain:            float32 height array (0..1)
        biome:              uint8 biome array
        island_mask:        float32 land mask (0..1)
        size:               heightmap resolution (e.g. 1025)
        seed:               rng seed
        weights:            audio weights dict
        n_plots:            number of farm plots (default 32)
        cluster_angle_deg:  direction of farm cluster from town center
        cluster_spread:     fractional distance of town from map center
    
    Returns:
        terrain:            modified height array
        biome:              modified biome array
        plot_positions:     list of (row, col) farm plot centers
        town_data:          structured dict for JSON export
        street_mask:        bool array
        town_mask:          bool array
        farm_mask:          bool array
    """
    rng = np.random.default_rng(seed + 20000)

    # ── 1. Find town center
    town_center_row, town_center_col = find_town_center(
        terrain, island_mask, size, seed,
        cluster_angle_deg=cluster_angle_deg,
        cluster_spread=cluster_spread,
    )

    # ── 2. Build street grid
    streets, blocks = build_street_grid(
        town_center_row, town_center_col, size,
        n_streets_x=4, n_streets_y=4,
    )

    # ── 3. Classify blocks
    blocks = classify_blocks(blocks, town_center_row, town_center_col)

    # ── 4. Place lots in each block
    all_lots = []
    house_lots = []
    for b in blocks:
        lots = place_lots_in_block(b, size, lot_type=b.get("type", BLOCK_TYPE_RESIDENTIAL), rng=rng)
        all_lots.extend(lots)
        if b.get("type") == BLOCK_TYPE_RESIDENTIAL:
            house_lots.extend(lots)

    # ── 5. Farm plots — grid just outside town
    plot_positions, farm_angle, farm_center = place_farm_plots(
        town_center_row, town_center_col, size,
        n_plots=n_plots, seed=seed,
    )

    # ── 6. Build masks
    town_mask, street_mask, lot_mask, plaza_mask, farm_mask = build_town_masks(
        streets, blocks, all_lots, plot_positions, size,
        farm_center, farm_angle, n_plots=n_plots,
    )

    # ── 7. Apply to terrain
    terrain = apply_town_to_terrain(
        terrain, town_mask, street_mask,
        lot_mask, plaza_mask, farm_mask,
        town_center_row, town_center_col,
    )

    # ── 8. Paint biomes
    biome = paint_town_biomes(biome, town_mask, street_mask, plaza_mask, farm_mask)

    # ── 9. Assemble town_data export
    # Pixel → world cm
    cpp  = WORLD_SIZE_CM / size
    half = WORLD_SIZE_CM / 2

    def to_world(r, c):
        return round((c * cpp) - half, 1), round((r * cpp) - half, 1)

    tc_wx, tc_wz = to_world(town_center_row, town_center_col)

    street_data = []
    for s in streets:
        if s["axis"] == "EW":
            wx, wz = to_world(s["row"], town_center_col)
        else:
            wx, wz = to_world(town_center_row, s["col"])
        street_data.append({
            "name":   s["name"],
            "axis":   s["axis"],
            "world_x_cm": wx,
            "world_z_cm": wz,
            "width_cm":   s["width_px"] * cpp,
        })

    lot_data = []
    for lot in all_lots:
        lc_r = (lot["row"] + lot["row_end"]) // 2
        lc_c = (lot["col"] + lot["col_end"]) // 2
        lwx, lwz = to_world(lc_r, lc_c)
        lot_data.append({
            "type":       lot["type"],
            "block_id":   lot["block_id"],
            "world_x_cm": lwx,
            "world_z_cm": lwz,
            "width_cm":   round(lot["width_px"] * cpp, 1),
            "depth_cm":   round(lot["height_px"] * cpp, 1),
        })

    plot_data = []
    for i, (pr, pc) in enumerate(plot_positions):
        pwx, pwz = to_world(pr, pc)
        plot_data.append({
            "index":      i,
            "pixel":      [int(pr), int(pc)],
            "world_x_cm": pwx,
            "world_z_cm": pwz,
            "elevation":  round(float(terrain[pr, pc]), 4),
        })

    town_data = {
        "center_pixel":   [int(town_center_row), int(town_center_col)],
        "center_world_x": tc_wx,
        "center_world_z": tc_wz,
        "footprint_cm":   TOWN_SIZE_CM,
        "streets":        street_data,
        "lots":           lot_data,
        "farm_plots":     plot_data,
        "world_size_cm":  WORLD_SIZE_CM,
        "cm_per_pixel":   round(cpp, 2),
        "verse_constants": {
            "TOWN_X_CM":      tc_wx,
            "TOWN_Z_CM":      tc_wz,
            "PLOT_COUNT":     len(plot_positions),
            "WORLD_SIZE_CM":  WORLD_SIZE_CM,
            "CM_PER_PIXEL":   round(cpp, 2),
            "TOWN_SIZE_CM":   TOWN_SIZE_CM,
            "STREET_WIDTH_CM": STREET_WIDTH_CM,
            "HOUSE_LOT_CM":   HOUSE_LOT_CM,
            "FARM_PLOT_CM":   3200,
        }
    }

    return terrain, biome, plot_positions, town_data, street_mask, town_mask, farm_mask


# ─────────────────────────────────────────────────────────────
# PREVIEW OVERLAY  — called from build_preview
# ─────────────────────────────────────────────────────────────

# Town biome colour (sandy/grey — like Fortnite streets)
TOWN_COLOUR     = (158, 148, 132)   # warm grey asphalt
STREET_COLOUR   = (120, 112, 100)   # slightly darker road
PLAZA_COLOUR    = ( 80, 130,  65)   # green park
HOUSE_COLOUR    = (185, 160, 125)   # warm tan building
FARM_ROW_COLOUR = (160, 190,  80)   # bright crop green

def render_town_overlay(rgb, street_mask, town_mask, farm_mask,
                        plot_positions, blocks, all_lots, size):
    """
    Paint town geometry onto an RGB preview image.
    Called from build_preview after base biome colours are applied.
    """
    # Town streets
    rgb[town_mask]   = TOWN_COLOUR
    rgb[street_mask] = STREET_COLOUR

    # Plaza blocks
    for b in blocks:
        if b.get("type") == BLOCK_TYPE_PLAZA:
            r0,r1 = max(0,b["row_min"]), min(size,b["row_max"])
            c0,c1 = max(0,b["col_min"]), min(size,b["col_max"])
            if r1>r0 and c1>c0:
                rgb[r0:r1, c0:c1] = PLAZA_COLOUR

    # Building lots
    for lot in all_lots:
        r0,r1 = max(0,lot["row"]),    min(size,lot["row_end"])
        c0,c1 = max(0,lot["col"]),    min(size,lot["col_end"])
        if r1>r0 and c1>c0:
            if lot["type"] == "house":
                rgb[r0:r1, c0:c1] = HOUSE_COLOUR
            elif lot["type"] in ("shop","diner","gas_station","market","clinic"):
                rgb[r0:r1, c0:c1] = (150, 120, 180)   # commercial purple-ish
            elif lot["type"] in ("barn","warehouse","silo","dock"):
                rgb[r0:r1, c0:c1] = (140, 110,  80)   # industrial brown
            # Roof outline (dark 1px border)
            rgb[r0:r0+1, c0:c1]   = (40, 40, 40)
            rgb[r1-1:r1, c0:c1]   = (40, 40, 40)
            rgb[r0:r1,   c0:c0+1] = (40, 40, 40)
            rgb[r0:r1,   c1-1:c1] = (40, 40, 40)

    # Farm rows — alternating bright/dark stripes within farm mask
    farm_only = farm_mask.copy()
    rows_in_mask = np.any(farm_only, axis=1)
    for r in np.where(rows_in_mask)[0]:
        stripe = (r // 2) % 2
        col_pts = np.where(farm_only[r])[0]
        if len(col_pts) == 0:
            continue
        if stripe == 0:
            rgb[r, col_pts] = FARM_ROW_COLOUR
        else:
            # Slightly darker alternate row
            rgb[r, col_pts] = (130, 160, 55)

    # Plot center dots (yellow squares like before)
    dot_r = max(1, size // 200)
    for pr, pc in plot_positions:
        r0 = max(0, pr-dot_r); r1 = min(size, pr+dot_r+1)
        c0 = max(0, pc-dot_r); c1 = min(size, pc+dot_r+1)
        rgb[r0:r1, c0:c1] = [255, 220, 50]

    return rgb
