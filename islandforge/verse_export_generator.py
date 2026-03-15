"""
UEFN Verse Export System
Generates a concrete UEFN handoff package from Forge outputs.

The package is designed around the real UEFN constraint:
- heightmap + layout + placement data can be generated automatically
- built-in Fortnite assets still need editor-side binding to generated slots
"""

import json
import random
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from uefn_asset_catalog import (
    BIOME_GALLERY_MAP,
    BIOME_THRESHOLDS,
    CHAPTER_POIS,
    FOLIAGE_DENSITY,
    UEFN_ASSET_CATALOG,
)

BIOME_PROFILE_MAP = {
    "Farm": "farmstead_cluster",
    "Plains": "suburban_outpost",
    "Forest": "woodland_hamlet",
    "Jungle": "expedition_outpost",
    "Highland": "watchtower_keep",
    "Peak": "boss_vantage",
    "Desert": "desert_waystation",
    "Snow": "snow_lodge",
    "Beach": "coastal_camp",
    "Town": "safe_town_core",
    "Urban": "service_block",
}

BIOME_POI_PREFS = {
    "Farm": {"farm", "open", "suburban"},
    "Plains": {"farm", "open", "suburban"},
    "Forest": {"forest", "jungle", "suburban"},
    "Jungle": {"jungle", "forest"},
    "Highland": {"highland"},
    "Peak": {"highland"},
    "Desert": {"desert", "open"},
    "Snow": {"snow", "highland"},
    "Beach": {"beach", "suburban"},
    "Town": {"urban", "suburban", "industrial"},
    "Urban": {"urban", "industrial"},
}

THEME_TOWN_PROFILES = {
    "Chapter 1": "classic_service_town",
    "Chapter 2": "harbor_swamp_service_town",
    "Chapter 3": "theater_motor_lodge_town",
    "Chapter 4": "field_forge_market_town",
    "Chapter 5": "luxury_riviera_service_town",
    "Chapter 6": "lantern_market_hub",
}

MATERIAL_KEYS = {
    "Water": ["water"],
    "Beach": ["sand", "terrain"],
    "Farm": ["grass", "dirt", "mud", "terrain"],
    "Plains": ["grass", "terrain"],
    "Forest": ["grass", "terrain"],
    "Jungle": ["swamp", "grass", "terrain"],
    "Desert": ["sand", "dirt", "terrain"],
    "Snow": ["snow", "ice", "terrain"],
    "Highland": ["rock", "stone", "dirt", "terrain"],
    "Peak": ["rock", "stone", "terrain"],
    "Town": ["road", "terrain"],
    "Urban": ["road", "terrain"],
}


class VerseExportGenerator:
    """Generates a complete, data-rich UEFN package for Forge outputs."""

    def __init__(self, seed: int, theme: str, world_size_cm: int):
        self.seed = seed
        self.theme = theme
        self.world_size_cm = world_size_cm
        self.random = random.Random(seed)

    def generate_full_package(
        self,
        biome_map: List[List[str]],
        plot_data: List[Dict],
        town_center: Tuple[float, float],
        heightmap: List[List[float]],
    ) -> Dict[str, str]:
        """Generate the package files for a single Forge run."""
        self.grid_size = len(biome_map) or len(heightmap) or 0
        zone_summary = self._summarize_biomes(biome_map)
        landmark_hints = self._build_landmark_hints(zone_summary)
        foliage_anchors = self._build_foliage_anchors(biome_map, heightmap)
        poi_sites = self._build_poi_sites(plot_data, town_center, landmark_hints)
        asset_slots = self._build_asset_slots(zone_summary)
        placement_plan = self._build_placement_plan(
            zone_summary,
            plot_data,
            town_center,
            foliage_anchors,
            poi_sites,
            landmark_hints,
        )

        return {
            "plot_registry.verse": self._generate_plot_registry(plot_data, town_center),
            "biome_manifest.verse": self._generate_biome_manifest(
                zone_summary, foliage_anchors, landmark_hints
            ),
            "foliage_spawner.verse": self._generate_foliage_spawner(
                asset_slots, foliage_anchors
            ),
            "poi_placer.verse": self._generate_poi_placer(poi_sites, landmark_hints),
            "landscape_config.json": self._generate_landscape_config(
                zone_summary, landmark_hints
            ),
            "asset_manifest.json": self._generate_asset_manifest(
                zone_summary, asset_slots, landmark_hints
            ),
            "placement_plan.json": json.dumps(placement_plan, indent=2),
            "README.md": self._generate_readme(zone_summary, asset_slots, landmark_hints),
        }

    def _coerce_biome(self, value) -> str:
        text = str(value or "Plains").strip() or "Plains"
        return text[0].upper() + text[1:]

    def _grid_to_world(self, row: int, col: int) -> Tuple[float, float]:
        size = max(self.grid_size, 1)
        half = self.world_size_cm / 2.0
        world_x = (col / size) * self.world_size_cm - half
        world_z = (row / size) * self.world_size_cm - half
        return round(world_x, 1), round(world_z, 1)

    def _verse_string(self, value: str) -> str:
        text = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
        return f'"{text}"'

    def _verse_string_list(self, values: List[str]) -> str:
        if not values:
            return "array{}"
        items = ", ".join(self._verse_string(value) for value in values)
        return f"array{{{items}}}"

    def _preferred_galleries_for_biome(self, biome_name: str) -> List[str]:
        galleries = list(BIOME_GALLERY_MAP.get(biome_name, ["suburban_house_a"]))

        if self.theme == "Chapter 5":
            if biome_name in {"Farm", "Plains", "Town", "Snow"}:
                galleries.insert(0, "ch5_nori_suburban")
            if biome_name in {"Highland", "Peak"}:
                galleries.insert(0, "ch5_greek_landmark")
        elif self.theme == "Chapter 6":
            if biome_name in {"Forest", "Plains", "Highland", "Town"}:
                galleries.insert(0, "ch6_japanese_block")

        ordered = []
        seen = set()
        for gallery in galleries:
            if gallery in UEFN_ASSET_CATALOG["building_modules"] and gallery not in seen:
                ordered.append(gallery)
                seen.add(gallery)
        return ordered or ["suburban_house_a"]

    def _material_for_biome(self, biome_name: str) -> str:
        materials = UEFN_ASSET_CATALOG["materials"].get(self.theme, {})
        for key in MATERIAL_KEYS.get(biome_name, ["terrain"]):
            if key in materials:
                return materials[key]
        return materials.get("terrain", "")

    def _foliage_assets_for_biome(self, biome_name: str) -> Dict[str, List[str]]:
        theme_foliage = UEFN_ASSET_CATALOG["foliage"].get(self.theme, {})
        if biome_name in theme_foliage:
            return theme_foliage[biome_name]
        return (
            UEFN_ASSET_CATALOG["foliage"].get("Chapter 1", {}).get(biome_name, {})
            or {}
        )

    def _summarize_biomes(self, biome_map: List[List[str]]) -> Dict[str, Dict]:
        counts = Counter()
        for row in biome_map:
            for cell in row:
                counts[self._coerce_biome(cell)] += 1

        total = sum(counts.values()) or 1
        summary = {}
        for biome_name, count in counts.most_common():
            density = FOLIAGE_DENSITY.get(biome_name, {"trees": 0, "bushes": 0, "grass": 0})
            summary[biome_name] = {
                "cell_count": count,
                "coverage_pct": round((count / total) * 100, 2),
                "preferred_galleries": self._preferred_galleries_for_biome(biome_name),
                "primary_material": self._material_for_biome(biome_name),
                "foliage_density": density,
            }
        return summary

    def _build_landmark_hints(self, zone_summary: Dict[str, Dict]) -> List[str]:
        chapter_pois = CHAPTER_POIS.get(self.theme, {})
        if not chapter_pois:
            return []

        dominant_biomes = [name for name in zone_summary.keys() if name != "Water"][:4]
        if not dominant_biomes:
            dominant_biomes = list(zone_summary.keys())[:4]
        preferred_categories = set()
        for biome_name in dominant_biomes:
            preferred_categories.update(BIOME_POI_PREFS.get(biome_name, set()))

        matched = []
        fallback = []
        for poi_name, category in chapter_pois.items():
            if category in preferred_categories:
                matched.append(poi_name)
            else:
                fallback.append(poi_name)

        ordered = []
        for name in matched + fallback:
            if name not in ordered:
                ordered.append(name)
        return ordered[:5]

    def _build_foliage_anchors(
        self, biome_map: List[List[str]], heightmap: List[List[float]]
    ) -> List[Dict]:
        if not biome_map:
            return []

        size = len(biome_map)
        step = max(1, size // 18)
        limit_per_biome = 14
        counters = defaultdict(int)
        anchors = []

        for row in range(step // 2, size, step):
            for col in range(step // 2, size, step):
                biome_name = self._coerce_biome(biome_map[row][col])
                if biome_name == "Water" or counters[biome_name] >= limit_per_biome:
                    continue

                elevation = 0.0
                if row < len(heightmap) and col < len(heightmap[row]):
                    elevation = float(heightmap[row][col])
                if biome_name not in {"Beach", "Water"} and elevation < 0.05:
                    continue

                density = FOLIAGE_DENSITY.get(
                    biome_name, {"trees": 0, "bushes": 0, "grass": 0}
                )
                world_x, world_z = self._grid_to_world(row, col)
                anchors.append(
                    {
                        "biome": biome_name,
                        "row": row,
                        "col": col,
                        "position": [world_x, world_z, 0.0],
                        "tree_count": density.get("trees", 0),
                        "bush_count": density.get("bushes", 0),
                        "grass_count": density.get("grass", 0),
                        "scatter_radius_cm": max(
                            800.0,
                            float(
                                300.0
                                + (density.get("trees", 0) * 140)
                                + (density.get("bushes", 0) * 40)
                            ),
                        ),
                        "preferred_gallery": self._preferred_galleries_for_biome(biome_name)[0],
                    }
                )
                counters[biome_name] += 1
        return anchors

    def _plot_profile_for_biome(self, biome_name: str) -> str:
        return BIOME_PROFILE_MAP.get(biome_name, "suburban_outpost")

    def _town_profile(self) -> str:
        return THEME_TOWN_PROFILES.get(self.theme, "service_town")

    def _build_poi_sites(
        self, plot_data: List[Dict], town_center: Tuple[float, float], landmark_hints: List[str]
    ) -> List[Dict]:
        sites = [
            {
                "id": -1,
                "name": "Town Core",
                "position": [round(float(town_center[0]), 1), round(float(town_center[1]), 1), 0.0],
                "biome": "Town",
                "profile": self._town_profile(),
                "radius_cm": max(3200.0, round(self.world_size_cm * 0.035, 1)),
                "preferred_galleries": self._preferred_galleries_for_biome("Town"),
                "landmark_hint": landmark_hints[0] if landmark_hints else "Town Center",
            }
        ]

        for plot in plot_data:
            biome_name = self._coerce_biome(plot.get("biome", "Plains"))
            sites.append(
                {
                    "id": int(plot.get("index", len(sites))),
                    "name": f"Plot {int(plot.get('index', len(sites))):02d}",
                    "position": [
                        round(float(plot.get("world_x_cm", 0.0)), 1),
                        round(float(plot.get("world_z_cm", 0.0)), 1),
                        0.0,
                    ],
                    "biome": biome_name,
                    "profile": self._plot_profile_for_biome(biome_name),
                    "radius_cm": 1400.0 if biome_name == "Farm" else 1200.0,
                    "preferred_galleries": self._preferred_galleries_for_biome(biome_name),
                    "landmark_hint": landmark_hints[
                        min(
                            len(sites) % max(len(landmark_hints), 1),
                            max(len(landmark_hints) - 1, 0),
                        )
                    ]
                    if landmark_hints
                    else biome_name,
                }
            )
        return sites

    def _build_asset_slots(self, zone_summary: Dict[str, Dict]) -> List[Dict]:
        slots = []
        for biome_name, data in zone_summary.items():
            if biome_name == "Water":
                continue
            slot_prefix = biome_name.replace(" ", "")
            foliage_assets = self._foliage_assets_for_biome(biome_name)
            for asset_type in ("trees", "bushes", "grass"):
                suggestions = foliage_assets.get(asset_type, [])
                if suggestions:
                    slots.append(
                        {
                            "slot_name": f"{slot_prefix}{asset_type.title()}",
                            "biome": biome_name,
                            "asset_type": asset_type,
                            "content_hint": f"Bind {biome_name} {asset_type} using built-in Fortnite content",
                            "suggested_assets": suggestions,
                        }
                    )

            primary_gallery = data["preferred_galleries"][0]
            secondary_gallery = (
                data["preferred_galleries"][1]
                if len(data["preferred_galleries"]) > 1
                else primary_gallery
            )
            for slot_name, gallery_key in (
                ("GalleryPrimary", primary_gallery),
                ("GallerySecondary", secondary_gallery),
            ):
                gallery = UEFN_ASSET_CATALOG["building_modules"].get(gallery_key, {})
                slots.append(
                    {
                        "slot_name": f"{slot_prefix}{slot_name}",
                        "biome": biome_name,
                        "asset_type": "gallery",
                        "content_hint": gallery.get("content_hint", ""),
                        "suggested_assets": list((gallery.get("pieces") or {}).values())[:8],
                        "gallery_id": gallery.get("gallery_id", gallery_key),
                    }
                )
        return slots

    def _build_placement_plan(
        self,
        zone_summary: Dict[str, Dict],
        plot_data: List[Dict],
        town_center: Tuple[float, float],
        foliage_anchors: List[Dict],
        poi_sites: List[Dict],
        landmark_hints: List[str],
    ) -> Dict:
        return {
            "seed": self.seed,
            "theme": self.theme,
            "world_size_cm": self.world_size_cm,
            "world_size_km": round(self.world_size_cm / 100_000, 2),
            "world_partition_required": self.world_size_cm > 200_000,
            "town_center": {
                "world_x_cm": round(float(town_center[0]), 1),
                "world_z_cm": round(float(town_center[1]), 1),
            },
            "landmark_hints": landmark_hints,
            "zone_summary": zone_summary,
            "plots": plot_data,
            "poi_sites": poi_sites,
            "foliage_anchors": foliage_anchors,
            "uefn_contract": {
                "automatic": [
                    "Heightmap silhouette",
                    "Biome coverage summary",
                    "Plot registry",
                    "Placement plan",
                    "Theme-aware material guidance",
                ],
                "editor_required": [
                    "Enable World Partition when flagged",
                    "Import heightmap.png",
                    "Bind generated slot names to built-in Fortnite assets",
                    "Replace placeholder runtime spawning with project-specific devices or Verse managers",
                ],
            },
        }

    def _generate_plot_registry(
        self, plot_data: List[Dict], town_center: Tuple[float, float]
    ) -> str:
        lines = [
            "# TriptokForge Plot Registry",
            f"# Seed: {self.seed} | Theme: {self.theme}",
            "",
            "using { /UnrealEngine.com/Temporary/SpatialMath }",
            "",
            "plot_registry := module:",
            f"    Theme<public>: string = {self._verse_string(self.theme)}",
            f"    TownProfile<public>: string = {self._verse_string(self._town_profile())}",
            (
                "    TownCenter<public>: vector3 = "
                f"vector3{{{float(town_center[0]):.1f}, {float(town_center[1]):.1f}, 0.0}}"
            ),
            "",
            "    Plots<public>: []plot_data = array{",
        ]

        for plot in plot_data:
            biome_name = self._coerce_biome(plot.get("biome", "Plains"))
            lines.extend(
                [
                    "        plot_data{",
                    f"            ID := {int(plot.get('index', 0))},",
                    (
                        "            Position := "
                        f"vector3{{{float(plot.get('world_x_cm', 0.0)):.1f}, "
                        f"{float(plot.get('world_z_cm', 0.0)):.1f}, 0.0}},"
                    ),
                    f"            BiomeType := {self._verse_string(biome_name)},",
                    f"            Elevation := {float(plot.get('elevation', 0.0)):.4f},",
                    f"            Profile := {self._verse_string(self._plot_profile_for_biome(biome_name))},",
                    f"            PreferredGallery := {self._verse_string(self._preferred_galleries_for_biome(biome_name)[0])}",
                    "        },",
                ]
            )

        lines.extend(
            [
                "    }",
                "",
                "plot_data := struct:",
                "    ID: int",
                "    Position: vector3",
                "    BiomeType: string",
                "    Elevation: float",
                "    Profile: string",
                "    PreferredGallery: string",
            ]
        )
        return "\n".join(lines)

    def _generate_biome_manifest(
        self, zone_summary: Dict[str, Dict], foliage_anchors: List[Dict], landmark_hints: List[str]
    ) -> str:
        lines = [
            f"# Biome Manifest - Theme: {self.theme}",
            "",
            "using { /UnrealEngine.com/Temporary/SpatialMath }",
            "",
            "biome_manifest := module:",
            f"    Theme<public>: string = {self._verse_string(self.theme)}",
            f"    DominantPOIHints<public>: []string = {self._verse_string_list(landmark_hints)}",
            "",
            "    BiomeZones<public>: []biome_zone = array{",
        ]

        for biome_name, data in zone_summary.items():
            lines.extend(
                [
                    "        biome_zone{",
                    f"            Name := {self._verse_string(biome_name)},",
                    f"            CellCount := {int(data['cell_count'])},",
                    f"            CoveragePct := {float(data['coverage_pct']):.2f},",
                    f"            PrimaryMaterial := {self._verse_string(data['primary_material'])},",
                    f"            PreferredGalleries := {self._verse_string_list(data['preferred_galleries'])}",
                    "        },",
                ]
            )

        lines.extend(
            [
                "    }",
                "",
                "    FoliageAnchors<public>: []foliage_anchor = array{",
            ]
        )

        for anchor in foliage_anchors:
            lines.extend(
                [
                    "        foliage_anchor{",
                    f"            BiomeName := {self._verse_string(anchor['biome'])},",
                    (
                        "            Position := "
                        f"vector3{{{anchor['position'][0]:.1f}, {anchor['position'][1]:.1f}, 0.0}},"
                    ),
                    f"            TreeCount := {int(anchor['tree_count'])},",
                    f"            BushCount := {int(anchor['bush_count'])},",
                    f"            GrassCount := {int(anchor['grass_count'])},",
                    f"            PreferredGallery := {self._verse_string(anchor['preferred_gallery'])}",
                    "        },",
                ]
            )

        lines.extend(
            [
                "    }",
                "",
                "biome_zone := struct:",
                "    Name: string",
                "    CellCount: int",
                "    CoveragePct: float",
                "    PrimaryMaterial: string",
                "    PreferredGalleries: []string",
                "",
                "foliage_anchor := struct:",
                "    BiomeName: string",
                "    Position: vector3",
                "    TreeCount: int",
                "    BushCount: int",
                "    GrassCount: int",
                "    PreferredGallery: string",
            ]
        )
        return "\n".join(lines)

    def _generate_foliage_spawner(
        self, asset_slots: List[Dict], foliage_anchors: List[Dict]
    ) -> str:
        lines = [
            "# Foliage Spawner Data",
            "# Bind matching creative_prop_asset arrays in UEFN using the slot names below.",
            "",
            "using { /UnrealEngine.com/Temporary/SpatialMath }",
            "",
            "foliage_spawner := module:",
            "    BindingSlots<public>: []foliage_binding_slot = array{",
        ]

        for slot in asset_slots:
            if slot["asset_type"] == "gallery":
                continue
            lines.extend(
                [
                    "        foliage_binding_slot{",
                    f"            SlotName := {self._verse_string(slot['slot_name'])},",
                    f"            BiomeName := {self._verse_string(slot['biome'])},",
                    f"            AssetType := {self._verse_string(slot['asset_type'])},",
                    f"            ContentHint := {self._verse_string(slot['content_hint'])},",
                    f"            SuggestedAssets := {self._verse_string_list(slot['suggested_assets'])}",
                    "        },",
                ]
            )

        lines.extend(
            [
                "    }",
                "",
                "    SpawnAnchors<public>: []foliage_spawn_anchor = array{",
            ]
        )

        for anchor in foliage_anchors:
            slot_prefix = anchor["biome"].replace(" ", "")
            lines.extend(
                [
                    "        foliage_spawn_anchor{",
                    f"            SlotPrefix := {self._verse_string(slot_prefix)},",
                    (
                        "            Position := "
                        f"vector3{{{anchor['position'][0]:.1f}, {anchor['position'][1]:.1f}, 0.0}},"
                    ),
                    f"            ScatterRadiusCm := {float(anchor['scatter_radius_cm']):.1f},",
                    f"            TreeCount := {int(anchor['tree_count'])},",
                    f"            BushCount := {int(anchor['bush_count'])},",
                    f"            GrassCount := {int(anchor['grass_count'])}",
                    "        },",
                ]
            )

        lines.extend(
            [
                "    }",
                "",
                "foliage_binding_slot := struct:",
                "    SlotName: string",
                "    BiomeName: string",
                "    AssetType: string",
                "    ContentHint: string",
                "    SuggestedAssets: []string",
                "",
                "foliage_spawn_anchor := struct:",
                "    SlotPrefix: string",
                "    Position: vector3",
                "    ScatterRadiusCm: float",
                "    TreeCount: int",
                "    BushCount: int",
                "    GrassCount: int",
            ]
        )
        return "\n".join(lines)

    def _generate_poi_placer(self, poi_sites: List[Dict], landmark_hints: List[str]) -> str:
        lines = [
            "# POI Placement Plan",
            "# Use this as the data source for town, farm, and landmark placement in UEFN.",
            "",
            "using { /UnrealEngine.com/Temporary/SpatialMath }",
            "",
            "poi_placer := module:",
            f"    Theme<public>: string = {self._verse_string(self.theme)}",
            f"    TownProfile<public>: string = {self._verse_string(self._town_profile())}",
            f"    LandmarkHints<public>: []string = {self._verse_string_list(landmark_hints)}",
            "",
            "    Sites<public>: []poi_site = array{",
        ]

        for site in poi_sites:
            lines.extend(
                [
                    "        poi_site{",
                    f"            ID := {int(site['id'])},",
                    f"            Name := {self._verse_string(site['name'])},",
                    (
                        "            Position := "
                        f"vector3{{{site['position'][0]:.1f}, {site['position'][1]:.1f}, 0.0}},"
                    ),
                    f"            BiomeType := {self._verse_string(site['biome'])},",
                    f"            Profile := {self._verse_string(site['profile'])},",
                    f"            RadiusCm := {float(site['radius_cm']):.1f},",
                    f"            LandmarkHint := {self._verse_string(site['landmark_hint'])},",
                    f"            PreferredGalleries := {self._verse_string_list(site['preferred_galleries'])}",
                    "        },",
                ]
            )

        lines.extend(
            [
                "    }",
                "",
                "poi_site := struct:",
                "    ID: int",
                "    Name: string",
                "    Position: vector3",
                "    BiomeType: string",
                "    Profile: string",
                "    RadiusCm: float",
                "    LandmarkHint: string",
                "    PreferredGalleries: []string",
            ]
        )
        return "\n".join(lines)

    def _generate_landscape_config(
        self, zone_summary: Dict[str, Dict], landmark_hints: List[str]
    ) -> str:
        materials = UEFN_ASSET_CATALOG["materials"].get(self.theme, {})
        config = {
            "theme": self.theme,
            "seed": self.seed,
            "world_size_cm": self.world_size_cm,
            "world_size_km": round(self.world_size_cm / 100_000, 2),
            "grid_resolution": self.grid_size,
            "terrain_material": materials.get("terrain", ""),
            "biome_thresholds": BIOME_THRESHOLDS.get(self.theme, {}),
            "biome_materials": {
                biome_name: data["primary_material"] for biome_name, data in zone_summary.items()
            },
            "biome_gallery_profiles": {
                biome_name: data["preferred_galleries"] for biome_name, data in zone_summary.items()
            },
            "import_settings": {
                "world_partition_required": self.world_size_cm > 200_000,
                "enable_streaming": self.world_size_cm > 200_000,
                "section_size_quads": 63,
                "sections_per_component": "2x2",
                "heightmap_resolution_px": self.grid_size,
            },
            "landmark_hints": landmark_hints,
        }
        return json.dumps(config, indent=2)

    def _generate_asset_manifest(
        self, zone_summary: Dict[str, Dict], asset_slots: List[Dict], landmark_hints: List[str]
    ) -> str:
        gallery_profiles = {}
        unique_assets = set()
        for biome_name, data in zone_summary.items():
            if biome_name == "Water":
                continue
            gallery_profiles[biome_name] = []
            for gallery_key in data["preferred_galleries"]:
                gallery = UEFN_ASSET_CATALOG["building_modules"].get(gallery_key, {})
                piece_ids = list((gallery.get("pieces") or {}).values())
                gallery_profiles[biome_name].append(
                    {
                        "key": gallery_key,
                        "gallery_id": gallery.get("gallery_id", ""),
                        "content_hint": gallery.get("content_hint", ""),
                        "piece_ids": piece_ids,
                    }
                )
                unique_assets.add(gallery.get("gallery_id", gallery_key))
                unique_assets.update(piece_ids)

        for slot in asset_slots:
            unique_assets.update(slot.get("suggested_assets", []))

        manifest = {
            "seed": self.seed,
            "theme": self.theme,
            "world_size_cm": self.world_size_cm,
            "world_size_km": round(self.world_size_cm / 100_000, 2),
            "asset_count": len([asset for asset in unique_assets if asset]),
            "landmark_hints": landmark_hints,
            "binding_slots": asset_slots,
            "gallery_profiles": gallery_profiles,
            "materials": UEFN_ASSET_CATALOG["materials"].get(self.theme, {}),
            "zone_summary": zone_summary,
            "uefn_contract": {
                "built_in_assets_only": True,
                "editor_binding_required": True,
                "custom_download_assets_required": False,
            },
        }
        return json.dumps(manifest, indent=2)

    def _generate_readme(
        self, zone_summary: Dict[str, Dict], asset_slots: List[Dict], landmark_hints: List[str]
    ) -> str:
        needs_world_partition = self.world_size_cm > 200_000
        file_list = [
            "plot_registry.verse",
            "biome_manifest.verse",
            "foliage_spawner.verse",
            "poi_placer.verse",
            "landscape_config.json",
            "asset_manifest.json",
            "placement_plan.json",
            "README.md",
        ]
        dominant_biomes = ", ".join([name for name in zone_summary.keys() if name != "Water"][:4]) or "Plains"
        slot_count = len(asset_slots)

        return f"""# TriptokForge UEFN Island Package
Seed: {self.seed}
Theme: {self.theme}
World Size: {self.world_size_cm} cm ({self.world_size_cm / 100_000:.2f} km)

## What this package gives you

- Fortnite-shaped heightmap data driven by Forge audio analysis
- Theme-aware biome breakdown instead of one generic biome pass
- Plot, town, and landmark placement plans tied to the chosen chapter theme
- Binding slot names for built-in Fortnite foliage and gallery sets
- A numbered run package that can be compared against previous runs

Dominant biomes in this run: {dominant_biomes}
Theme landmark references: {", ".join(landmark_hints) if landmark_hints else "None generated"}

## Files

{chr(10).join(f"- {name}" for name in file_list)}

## What is automatic now

- Heightmap silhouette and preview generation
- Plot registry and town center coordinates
- Theme-aware material guidance
- Foliage anchor sampling and density planning
- Gallery recommendations per biome and plot profile

## What still requires UEFN editor work

1. {"Enable World Partition in Edit -> Project Settings -> World and enable Streaming in World Settings before import." if needs_world_partition else "World Partition is optional at this size, but still recommended if you expect heavy runtime spawning or future scale growth."}
2. Import `heightmap.png` in Landscape Mode using the same resolution shown in Forge.
3. Copy the generated Verse files into your project or extract `verse_package.zip` there.
4. Open `asset_manifest.json` and bind the generated slot names to built-in Fortnite content in the UEFN editor.
5. Use `placement_plan.json` and `poi_placer.verse` to align town landmarks, farm plots, roads, and gallery kits.
6. Launch a session, validate streaming cells and town readability, then iterate with the next numbered Forge run instead of overwriting this one.

## Binding rule

UEFN does not let a generated file silently grab arbitrary cooked Fortnite props at publish time.
The correct workflow is:
- generated files declare the plan
- the editor binds the built-in assets
- your Verse or device logic spawns or references those assets by the same slot names

This package is designed to make that workflow systematic instead of guesswork.

## Slot count

This run generated {slot_count} binding slots across foliage and gallery profiles.
Use `asset_manifest.json` as the master checklist when wiring them in UEFN.
"""


def integrate_with_forge(result_data: Dict, theme: str, seed: int) -> Dict:
    """
    Integrate Forge result data with the export generator.
    """
    generator = VerseExportGenerator(
        seed=seed,
        theme=theme,
        world_size_cm=result_data.get("world_size_cm", 1_100_000),
    )

    biome_map_raw = result_data.get("biome_map", [])
    if biome_map_raw and hasattr(biome_map_raw, "tolist"):
        biome_map_raw = biome_map_raw.tolist()

    biome_names = {
        0: "Water",
        1: "Beach",
        2: "Plains",
        3: "Forest",
        4: "Jungle",
        5: "Snow",
        6: "Desert",
        7: "Highland",
        8: "Peak",
        9: "Farm",
    }
    biome_map = []
    for row in biome_map_raw:
        biome_row = []
        for cell in row:
            if isinstance(cell, (int, float)):
                biome_row.append(biome_names.get(int(cell), "Plains"))
            else:
                biome_row.append(str(cell))
        biome_map.append(biome_row)

    town_center_data = result_data.get("town_center", [0, 0])
    if isinstance(town_center_data, dict):
        town_center = (
            float(town_center_data.get("world_x_cm", 0)),
            float(town_center_data.get("world_z_cm", 0)),
        )
    elif isinstance(town_center_data, (list, tuple)) and len(town_center_data) == 2:
        town_center = (float(town_center_data[0]), float(town_center_data[1]))
    else:
        town_center = (0.0, 0.0)

    result_data["verse_package"] = generator.generate_full_package(
        biome_map=biome_map,
        plot_data=result_data.get("plots_found", []),
        town_center=town_center,
        heightmap=result_data.get("heightmap_normalized", []),
    )
    return result_data
