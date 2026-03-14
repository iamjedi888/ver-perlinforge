"""
prefab_composer.py — TriptokForge Weighted Residential Lot System
=================================================================
Generates a realistic, randomised residential property by composing
building-set gallery pieces in their correct spatial positions.

Lot anatomy (top-down view; street = SOUTH edge = Y=0):

        ┌──────────────── BACK YARD ─────────────────┐
        │  [shed / pool / trampoline / bbq]           │
  FENCE │                                              │ FENCE
        │          HOUSE BODY (walls + roof)           │
        │     [porch]                 [garage]         │
  ──────┼──────────────────────────────────────────────┼──────
  fence │  DRIVEWAY (if garage)  │ MAILBOX │ SIDEWALK  │ fence
  ──────┴──────────────────────────────────────────────┴──────
                           S T R E E T

All measurements in centimetres (UEFN native unit).
Coordinates are relative to lot SW corner (lot_origin_x, lot_origin_z).
UE convention used: X=east, Y=up/elevation, Z=south→north depth.
"""

import random
from typing import Dict, List, Optional, Tuple

# ── Lot geometry constants (cm) ───────────────────────────────
LOT_W         = 2_400   # lot width  (east-west)
LOT_D         = 2_800   # lot depth  (north, into yard)

HOUSE_W       = 1_400   # house body width
HOUSE_D       =   900   # house body depth
HOUSE_H       =   350   # single storey height
WALL_PANEL_W  =   400   # standard gallery wall panel width
WALL_T        =    20   # wall thickness
ROOF_OVERHANG =    60

GARAGE_W      =   700   # attached garage width
GARAGE_D      =   750   # attached garage depth
GARAGE_H      =   310

SETBACK_MIN   =   400   # front setback (street → house face)
SETBACK_MAX   =   650

# ── Element probabilities ─────────────────────────────────────
PROBS = {
    "garage_attached":  0.55,
    "garage_detached":  0.15,
    "front_porch":      0.50,
    "chimney":          0.40,
    "second_floor":     0.25,
    "fence_front":      0.70,
    "fence_side":       0.80,
    "fence_back":       0.85,
    "gate":             0.60,
    "driveway":         0.75,
    "mailbox":          0.90,
    "sidewalk":         0.85,
    "street_light":     0.40,
    "car_parked":       0.50,
    "garden_beds":      0.55,
    "patio":            0.40,
    "bbq_grill":        0.35,
    "trampoline":       0.15,
    "basketball_hoop":  0.20,
    "backyard_tree":    0.65,
    "backyard_shed":    0.20,
}

# ── Style weight tables ───────────────────────────────────────
FENCE_STYLES = {
    "Plains":    [("fence_picket",0.6),("fence_wood_rail",0.3),("fence_chain_link",0.1)],
    "Farm":      [("fence_wood_rail",0.6),("fence_picket",0.3),("fence_chain_link",0.1)],
    "Forest":    [("fence_wood_rail",0.7),("fence_picket",0.3)],
    "Jungle":    [("fence_chain_link",0.6),("fence_wood_rail",0.4)],
    "Desert":    [("fence_chain_link",0.5),("fence_wood_rail",0.3),("fence_picket",0.2)],
    "Snow":      [("fence_picket",0.5),("fence_wood_rail",0.5)],
    "Beach":     [("fence_picket",0.7),("fence_wood_rail",0.3)],
    "Highland":  [("fence_chain_link",0.5),("fence_wood_rail",0.5)],
    "Town":      [("fence_picket",0.5),("fence_chain_link",0.3),("fence_wood_rail",0.2)],
    "default":   [("fence_picket",0.5),("fence_wood_rail",0.3),("fence_chain_link",0.2)],
}

ROOF_STYLES = {
    "suburban_house_a":    [("roof_gable",0.6),("roof_hip",0.3),("roof_flat",0.1)],
    "suburban_house_b":    [("roof_gable",0.5),("roof_hip",0.4),("roof_flat",0.1)],
    "pleasant_park_block": [("roof_gable",0.7),("roof_porch",0.2),("roof_hip",0.1)],
    "ch5_nori_suburban":   [("roof_gable",0.45),("roof_metal",0.45),("roof_hip",0.1)],
    "default":             [("roof_gable",0.6),("roof_hip",0.4)],
}

DRIVEWAY_STYLES = {
    "Plains":  [("driveway_plain",0.7),("driveway_brick",0.2),("driveway_gravel",0.1)],
    "Farm":    [("driveway_gravel",0.6),("driveway_plain",0.4)],
    "Desert":  [("driveway_gravel",0.6),("driveway_plain",0.4)],
    "default": [("driveway_plain",0.6),("driveway_brick",0.3),("driveway_gravel",0.1)],
}

CAR_TYPES = [("car_sedan",0.45),("car_pickup",0.30),("car_suv",0.25)]


# ── Helpers ───────────────────────────────────────────────────

def _weighted_choice(rng: random.Random, choices: List[Tuple]) -> str:
    items, weights = zip(*choices)
    return rng.choices(list(items), weights=list(weights), k=1)[0]

def _roll(rng: random.Random, prob: float) -> bool:
    return rng.random() < prob

def _scale(length_cm: float, panel_w: float = WALL_PANEL_W) -> float:
    return max(0.1, length_cm / panel_w)


# ── Lot Composer ──────────────────────────────────────────────

class LotComposer:
    """
    Composes a single residential lot into a flat list of prop placements.

    Each placement dict:
      slot_name  : str   — unique @editable slot name in generated Verse
      prop_id    : str   — content-browser asset name (from gallery catalog)
      x_cm       : float — world X (east)
      y_cm       : float — elevation (UE Y-up)
      z_cm       : float — world Z (north, depth from street)
      yaw_deg    : float — rotation around vertical axis
      scale_x/y/z: float — non-uniform scale
      category   : str   — "structure" | "fence" | "prop" | "foliage"
      note       : str   — human-readable label
    """

    def __init__(self, seed: int, lot_index: int, biome: str, gallery: str,
                 lot_origin_x: float = 0.0, lot_origin_z: float = 0.0):
        self.rng       = random.Random(seed * 31337 + lot_index)
        self.idx       = lot_index
        self.biome     = biome
        self.gallery   = gallery
        self.ox        = lot_origin_x
        self.oz        = lot_origin_z
        self.pieces: List[Dict] = []

        # Randomise lot parameters
        self.setback           = self.rng.randint(SETBACK_MIN, SETBACK_MAX)
        self.has_att_garage    = _roll(self.rng, PROBS["garage_attached"])
        self.has_det_garage    = (not self.has_att_garage and
                                  _roll(self.rng, PROBS["garage_detached"]))
        self.has_driveway      = self.has_att_garage or self.has_det_garage or _roll(self.rng, 0.35)
        self.has_porch         = _roll(self.rng, PROBS["front_porch"])
        self.has_chimney       = _roll(self.rng, PROBS["chimney"])
        self.two_storey        = _roll(self.rng, PROBS["second_floor"])
        self.garage_side       = "right" if self.rng.random() > 0.4 else "left"

        self.roof_style   = _weighted_choice(self.rng, ROOF_STYLES.get(gallery, ROOF_STYLES["default"]))
        self.fence_style  = _weighted_choice(self.rng, FENCE_STYLES.get(biome, FENCE_STYLES["default"]))
        self.drive_style  = _weighted_choice(self.rng, DRIVEWAY_STYLES.get(biome, DRIVEWAY_STYLES["default"]))

        self._house_bounds: Optional[Tuple] = None
        self._garage_cx: Optional[float]    = None

    # ── Internal helpers ──────────────────────────────────────

    def _gp(self, piece_key: str) -> str:
        """Resolve a gallery piece key to its prop_id string."""
        from uefn_asset_catalog import CREATIVE_GALLERIES
        return CREATIVE_GALLERIES.get(self.gallery, {}).get("pieces", {}).get(
            piece_key, f"Prop_{self.gallery}_{piece_key}")

    def _add(self, slot: str, prop: str,
             x: float, y_depth: float, elev: float = 0.0,
             yaw: float = 0.0,
             sx: float = 1.0, sy: float = 1.0, sz: float = 1.0,
             category: str = "prop", note: str = ""):
        self.pieces.append({
            "slot_name": slot,
            "prop_id":   prop,
            "x_cm":      self.ox + x,
            "y_cm":      elev,
            "z_cm":      self.oz + y_depth,
            "yaw_deg":   yaw,
            "scale_x":   sx,
            "scale_y":   sy,
            "scale_z":   sz,
            "category":  category,
            "note":      note,
        })

    # ── House body ────────────────────────────────────────────

    def _build_house(self):
        hx0 = (LOT_W - HOUSE_W) / 2
        hy0 = self.setback
        hx1 = hx0 + HOUSE_W
        hy1 = hy0 + HOUSE_D
        self._house_bounds = (hx0, hy0, hx1, hy1)

        storeys = 2 if self.two_storey else 1
        for s in range(storeys):
            base_z = s * HOUSE_H
            # Walls: front, back, left, right
            wall_defs = [
                ("front", hx0, hy0,      HOUSE_W, 0.0),
                ("back",  hx0, hy1,      HOUSE_W, 0.0),
                ("left",  hx0, hy0,      HOUSE_D, 90.0),
                ("right", hx1, hy0,      HOUSE_D, 90.0),
            ]
            for face, wx, wy, wlen, wyaw in wall_defs:
                if s == 0 and face == "front":
                    piece = self._gp("wall_door")
                elif face in ("front","back"):
                    piece = self._gp("wall_window")
                else:
                    piece = self._gp("wall_plain")
                self._add(f"h_s{s}_wall_{face}", piece,
                          wx, wy, base_z, wyaw,
                          sx=_scale(wlen), sz=_scale(HOUSE_H, HOUSE_H),
                          category="structure",
                          note=f"House storey {s} {face} wall")

        # Floor slab
        self._add("h_floor", self._gp("floor"),
                  hx0, hy0, 0,
                  sx=_scale(HOUSE_W), sy=_scale(HOUSE_D),
                  category="structure", note="House floor slab")

        # Roof
        rz = storeys * HOUSE_H
        self._add("h_roof", self._gp(self.roof_style),
                  hx0 - ROOF_OVERHANG, hy0 - ROOF_OVERHANG, rz,
                  sx=_scale(HOUSE_W + 2*ROOF_OVERHANG),
                  sy=_scale(HOUSE_D + 2*ROOF_OVERHANG),
                  category="structure", note=f"House roof ({self.roof_style})")

        # Front door
        self._add("h_door_front", self._gp("door_front"),
                  hx0 + HOUSE_W*0.45, hy0, 0,
                  category="structure", note="Front door")

        # Windows — two per side wall
        for side, wx in [("l", hx0), ("r", hx1 - WALL_T)]:
            for wi, wy in enumerate([hy0 + HOUSE_D*0.3, hy0 + HOUSE_D*0.7]):
                self._add(f"h_win_{side}_{wi}", self._gp("window_sash"),
                          wx, wy, HOUSE_H*0.4,
                          yaw=90, category="structure", note=f"Side window {side}{wi}")

        # Chimney
        if self.has_chimney:
            self._add("h_chimney", self._gp("chimney"),
                      hx0 + HOUSE_W*0.7, hy0 + HOUSE_D*0.6, 0,
                      sz=_scale(storeys*HOUSE_H + 150, HOUSE_H),
                      category="structure", note="Chimney")

    # ── Porch ─────────────────────────────────────────────────

    def _build_porch(self):
        if not self.has_porch:
            return
        hx0, hy0, hx1, _ = self._house_bounds
        porch_d = 300
        self._add("h_porch", self._gp("porch_beam"),
                  hx0, hy0 - porch_d, 0,
                  sx=_scale(HOUSE_W), sy=_scale(porch_d),
                  category="structure", note="Front porch deck")
        self._add("h_porch_rail", self._gp("porch_railing"),
                  hx0, hy0 - porch_d, HOUSE_H*0.4,
                  sx=_scale(HOUSE_W), category="structure", note="Porch railing")

    # ── Garage ────────────────────────────────────────────────

    def _build_garage(self):
        hx0, hy0, hx1, hy1 = self._house_bounds
        if self.has_att_garage:
            # Attached beside house
            gx = hx1 if self.garage_side == "right" else hx0 - GARAGE_W
            gy = hy0
            self._add("g_wall_front", self._gp("wall_plain"),
                      gx, gy, 0,
                      sx=_scale(GARAGE_W), sz=_scale(GARAGE_H, HOUSE_H),
                      category="structure", note="Garage front wall")
            self._add("g_door", self._gp("door_garage"),
                      gx + 50, gy, 0,
                      sx=_scale(GARAGE_W - 100), sz=_scale(GARAGE_H, HOUSE_H),
                      category="structure", note="Garage door")
            self._add("g_roof", self._gp(self.roof_style),
                      gx, gy, GARAGE_H,
                      sx=_scale(GARAGE_W), sy=_scale(GARAGE_D),
                      category="structure", note="Garage roof")
            self._garage_cx = gx + GARAGE_W / 2

        elif self.has_det_garage:
            # Detached at back-corner of lot
            gx = LOT_W - GARAGE_W - 150
            gy = LOT_D - GARAGE_D - 150
            self._add("g_det_front", self._gp("wall_plain"),
                      gx, gy, 0,
                      sx=_scale(GARAGE_W), sz=_scale(GARAGE_H, HOUSE_H),
                      category="structure", note="Detached garage front")
            self._add("g_det_door", self._gp("door_garage"),
                      gx + 50, gy, 0,
                      sx=_scale(GARAGE_W - 100), sz=_scale(GARAGE_H, HOUSE_H),
                      category="structure", note="Detached garage door")
            self._garage_cx = gx + GARAGE_W / 2

    # ── Driveway ──────────────────────────────────────────────

    def _build_driveway(self):
        if not self.has_driveway:
            return
        cx = self._garage_cx if self._garage_cx else LOT_W * 0.65
        dw = 360
        dep = self.setback + 200
        self._add("driveway", self.drive_style,
                  cx - dw/2, 0, -5,
                  sx=_scale(dw), sy=_scale(dep),
                  category="prop", note=f"Driveway ({self.drive_style})")
        if _roll(self.rng, PROBS["car_parked"]):
            car = _weighted_choice(self.rng, CAR_TYPES)
            self._add("driveway_car", car,
                      cx - 100, dep * 0.5, 0,
                      yaw=self.rng.choice([0, 180]),
                      category="prop", note=f"Parked {car}")

    # ── Fences ────────────────────────────────────────────────

    def _build_fences(self):
        fp = self.fence_style
        drive_gap_x  = self._garage_cx - 200 if self._garage_cx else LOT_W * 0.55
        gate_x       = LOT_W * 0.30

        # Front fence (two segments bracketing the gate/driveway opening)
        if _roll(self.rng, PROBS["fence_front"]):
            opening_x = drive_gap_x if self.has_driveway else gate_x
            left_len  = opening_x - 100
            right_start = opening_x + 250

            if left_len > 100:
                self._add("fence_fl", fp, 0, 0, 0, sx=_scale(left_len),
                          category="fence", note="Front fence left segment")
            if _roll(self.rng, PROBS["gate"]):
                gate_prop = "gate_picket" if "picket" in fp else "gate_metal"
                self._add("fence_gate", gate_prop, opening_x - 100, 0, 0,
                          sx=_scale(200), category="fence", note="Front gate")
            right_len = LOT_W - right_start
            if right_len > 100:
                self._add("fence_fr", fp, right_start, 0, 0, sx=_scale(right_len),
                          category="fence", note="Front fence right segment")

            # Corner posts
            for px in (0, LOT_W):
                self._add(f"fence_post_{px}", "fence_post", px, 0, 0,
                          category="fence", note="Fence corner post")

        # Side fences
        if _roll(self.rng, PROBS["fence_side"]):
            self._add("fence_sl", fp, 0, 0, 0, yaw=90,
                      sx=_scale(LOT_D), category="fence", note="West side fence")
            self._add("fence_sr", fp, LOT_W, 0, 0, yaw=90,
                      sx=_scale(LOT_D), category="fence", note="East side fence")

        # Back fence
        if _roll(self.rng, PROBS["fence_back"]):
            self._add("fence_back", fp, 0, LOT_D, 0, sx=_scale(LOT_W),
                      category="fence", note="Back fence")

    # ── Street props ──────────────────────────────────────────

    def _build_street(self):
        if _roll(self.rng, PROBS["mailbox"]):
            self._add("mailbox", "mailbox_standard", LOT_W*0.15, -90, 0,
                      category="prop", note="Mailbox")
        if _roll(self.rng, PROBS["sidewalk"]):
            self._add("sidewalk", "sidewalk_slab", 0, -130, -3,
                      sx=_scale(LOT_W), sy=_scale(130),
                      category="prop", note="Sidewalk slab")
        if _roll(self.rng, PROBS["street_light"]):
            self._add("street_light", "street_light", LOT_W*0.85, -110, 0,
                      category="prop", note="Street light")

    # ── Yard details ──────────────────────────────────────────

    def _build_yard(self):
        _, hy0, _, hy1 = self._house_bounds

        # Front garden beds flanking front door
        if _roll(self.rng, PROBS["garden_beds"]):
            hx0 = self._house_bounds[0]
            self._add("garden_l", "garden_flower", hx0 + 80, hy0 - 180, 0,
                      category="prop", note="Garden bed left")
            self._add("garden_r", "garden_flower", hx0 + HOUSE_W - 200, hy0 - 180, 0,
                      category="prop", note="Garden bed right")

        # Back yard props
        if _roll(self.rng, PROBS["patio"]):
            self._add("patio_table", "patio_table", LOT_W*0.5, hy1+280, 0,
                      category="prop", note="Patio set")
        if _roll(self.rng, PROBS["bbq_grill"]):
            self._add("bbq_grill", "bbq_grill", LOT_W*0.65, hy1+180, 0,
                      category="prop", note="BBQ grill")
        if _roll(self.rng, PROBS["trampoline"]):
            self._add("trampoline", "trampoline", LOT_W*0.3, hy1+650, 0,
                      category="prop", note="Trampoline")
        if _roll(self.rng, PROBS["basketball_hoop"]):
            hoop_x = self._house_bounds[0] + HOUSE_W*0.5
            self._add("bball_hoop", "basketball_hoop",
                      hoop_x, self.setback - 120, 0,
                      category="prop", note="Basketball hoop (driveway side)")
        if _roll(self.rng, PROBS["backyard_tree"]):
            tx = self.rng.randint(200, LOT_W - 200)
            ty = self.rng.randint(hy1 + 300, LOT_D - 200)
            self._add("back_tree", "garden_shrub", tx, ty, 0,
                      sz=self.rng.uniform(1.2, 2.0),
                      category="foliage", note="Backyard tree")
        if _roll(self.rng, PROBS["backyard_shed"]):
            self._add("back_shed", "Prop_Shed_01",
                      LOT_W - 600, LOT_D - 700, 0,
                      category="structure", note="Garden shed")

    # ── Public API ────────────────────────────────────────────

    def compose(self) -> List[Dict]:
        """Build the full lot. Returns list of piece placement dicts."""
        self._build_house()
        self._build_porch()
        self._build_garage()
        self._build_driveway()
        self._build_fences()
        self._build_street()
        self._build_yard()
        return self.pieces


# ── Block-level composer ──────────────────────────────────────

def compose_residential_block(
    seed: int,
    block_origin_x: float,
    block_origin_z: float,
    lots_wide: int,
    lots_deep: int,
    biome: str,
    chapter: str = "Chapter 1",
) -> Dict:
    """
    Compose a full residential block (grid of lots, back-to-back rows).

    Returns:
      {
        "block_origin":  {x_cm, z_cm},
        "lots":          [ {lot_index, lot_origin, gallery, pieces, facing} ],
        "slot_registry": { slot_name: prop_id }   # all unique @editable slots
      }
    """
    from uefn_asset_catalog import BIOME_GALLERY_MAP

    rng = random.Random(seed)
    gallery_pool = BIOME_GALLERY_MAP.get(biome, BIOME_GALLERY_MAP.get("Plains", ["suburban_house_a"]))

    lots_out   = []
    slot_reg   = {}
    ROW_STRIDE = LOT_D + SETBACK_MAX + 300   # north stride per row pair

    for row in range(lots_deep):
        facing_south = (row % 2 == 0)
        for col in range(lots_wide):
            lot_idx = row * lots_wide + col
            gal = rng.choice(gallery_pool)
            lox = block_origin_x + col * (LOT_W + 150)
            loz = block_origin_z + (row // 2) * ROW_STRIDE + (0 if facing_south else LOT_D + SETBACK_MAX)

            composer = LotComposer(
                seed=seed, lot_index=lot_idx, biome=biome, gallery=gal,
                lot_origin_x=lox, lot_origin_z=loz,
            )
            pieces = composer.compose()

            if not facing_south:
                # Mirror lot 180° so back yards face each other
                for p in pieces:
                    p["x_cm"] = lox + LOT_W - (p["x_cm"] - lox)
                    p["z_cm"] = loz + LOT_D - (p["z_cm"] - loz)
                    p["yaw_deg"] = (p["yaw_deg"] + 180) % 360

            for p in pieces:
                slot_reg[p["slot_name"]] = p["prop_id"]

            lots_out.append({
                "lot_index":  lot_idx,
                "lot_origin": {"x_cm": lox, "z_cm": loz},
                "facing":     "south" if facing_south else "north",
                "gallery":    gal,
                "biome":      biome,
                "pieces":     pieces,
            })

    return {
        "block_origin":  {"x_cm": block_origin_x, "z_cm": block_origin_z},
        "lots":          lots_out,
        "slot_registry": slot_reg,
    }


# ── Verse code generator ──────────────────────────────────────

def generate_verse_slot_declarations(slot_registry: Dict[str, str],
                                     device_class: str = "lot_prefab_placer") -> str:
    """
    Generate Verse @editable slot declarations for all required props.
    The creator drags the corresponding UEFN content item onto each slot.
    """
    lines = [
        "# Auto-generated by TriptokForge prefab_composer",
        "# Assign each @editable slot to the matching content item in UEFN.",
        "",
        "using { /Fortnite.com/Devices }",
        "using { /Verse.org/Simulation }",
        "using { /UnrealEngine.com/Temporary/SpatialMath }",
        "",
        f"{device_class} := class(creative_device):",
        "",
    ]
    for slot in sorted(slot_registry):
        prop = slot_registry[slot]
        var  = slot.replace("-", "_").replace(" ", "_")
        lines.append(f"    @editable {var}: creative_prop_asset = creative_prop_asset{{}}  # {prop}")

    lines += [
        "",
        "    OnBegin<override>()<suspends>:void=",
        "        spawn{ PlaceAllProps() }",
        "",
        "    PlaceAllProps()<suspends>:void=",
        "        # SpawnProp calls injected here by poi_placer.verse generator",
        "        Print(\"TriptokForge lot placer ready\")",
    ]
    return "\n".join(lines)


def generate_verse_spawn_calls(pieces: List[Dict], slot_registry: Dict[str, str],
                               indent: str = "        ") -> str:
    """
    Generate the SpawnProp() call block for a list of piece placements.
    Uses officially documented UEFN Verse API:
      SpawnProp(PropAsset, Transform) -> ?creative_prop
    """
    lines = []
    for p in pieces:
        slot = p["slot_name"].replace("-","_").replace(" ","_")
        x, y, z = p["x_cm"], p["y_cm"], p["z_cm"]
        yaw_r = p["yaw_deg"] * 3.14159 / 180.0
        sx, sy, sz = p.get("scale_x",1), p.get("scale_y",1), p.get("scale_z",1)
        lines.append(
            f"{indent}# {p['note']}"
        )
        lines.append(
            f"{indent}if (Prop_{slot} := SpawnProp({slot},"
            f" Transform{{Translation:=vector3{{X:={x:.1f},Y:={y:.1f},Z:={z:.1f}}},"
            f"Rotation:=MakeRotation(vector3{{X:=0.0,Y:=1.0,Z:=0.0}},{yaw_r:.4f}),"
            f"Scale:=vector3{{X:={sx:.3f},Y:={sy:.3f},Z:={sz:.3f}}}}}))"
            f":{{Prop_{slot}.Show()}}"
        )
    return "\n".join(lines)
