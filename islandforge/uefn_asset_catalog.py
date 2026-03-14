"""
UEFN Asset Catalog — TriptokForge Island Forge
================================================================
Maps biome themes / chapters to Fortnite Creative gallery IDs,
modular building set pieces, and prefab reference names.

IMPORTANT — How UEFN asset referencing works:
  Epic's internal paths (/Game/Athena/Apollo/...) are cooked content
  and cannot be freely used in published islands. The officially supported
  pattern is:
    1. Declare  @editable MyProp:creative_prop_asset = creative_prop_asset{}
       in your Verse class.
    2. In the UEFN editor, drag the desired content-browser item into that slot.
    3. Call  SpawnProp(MyProp, Transform) at runtime.

  This catalog therefore maps SLOT NAMES (what we write in generated Verse)
  to CONTENT_BROWSER_HINT (what the creator drags in) + an INTERNAL_PATH
  that UEFN's File Manager can locate in the cooked content tree.
  The generated asset_manifest.json documents all slots so a creator can
  populate them systematically.

  For Chapter 5 / Chapter 6 the map code name is "Nori" (Ch5) / "Kyushu" (Ch6).
  Internal folder names follow the pattern:
    /Game/Athena/<CodeName>/Environments/...
================================================================
"""

# ── Chapter / map code names ──────────────────────────────────
CHAPTER_CODENAMES = {
    "Chapter 1": "Athena",       # original BR island
    "Chapter 2": "Apollo",       # tropical / swamp island
    "Chapter 3": "Artemis",      # snow / flipped island
    "Chapter 4": "Borealis",     # reality saplings / chrome
    "Chapter 5": "Nori",         # renegade / Greek / Wrecked
    "Chapter 6": "Kyushu",       # Japanese aesthetic, new island (S1)
}

# ── Named locations per chapter (biome cross-reference) ───────
CHAPTER_POIS = {
    "Chapter 1": {
        "Tilted Towers":    "urban",
        "Retail Row":       "suburban",
        "Pleasant Park":    "suburban",
        "Salty Springs":    "suburban",
        "Lonely Lodge":     "forest",
        "Haunted Hills":    "highland",
        "Paradise Palms":   "desert",
        "Flush Factory":    "industrial",
        "Dusty Divot":      "desert",
        "Wailing Woods":    "forest",
    },
    "Chapter 2": {
        "Holly Hedges":     "suburban",
        "Sweaty Sands":     "beach",
        "Misty Meadows":    "suburban",
        "Salty Springs":    "suburban",
        "Dirty Docks":      "industrial",
        "Lazy Lake":        "suburban",
        "Slurpy Swamp":     "swamp",
        "Coral Castle":     "beach",
        "Colossal Coliseum":"open",
        "Stealthy Stronghold":"jungle",
    },
    "Chapter 3": {
        "The Daily Bugle":  "urban",
        "Tilted Towers":    "urban",
        "Rocky Reels":      "desert",
        "Butter Barn":      "plains",
        "Chonker's Speedway":"industrial",
        "Condo Canyon":     "suburban",
        "Camp Cuddle":      "snow",
        "Logjam Lumberyard":"forest",
        "Shuffled Shrines": "jungle",
        "Chrome Crossroads":"highland",
    },
    "Chapter 4": {
        "Frenzy Fields":    "farm",
        "Shattered Slabs":  "rocky",
        "Faulty Splits":    "suburban",
        "Breakwater Bay":   "beach",
        "Steamy Springs":   "swamp",
        "Citadel":          "highland",
        "Anvil Square":     "industrial",
        "Knotty Nets":      "beach",
        "Eclipsed Estate":  "suburban",
    },
    "Chapter 5": {
        "Reckless Railways":  "industrial",
        "Ruined Reels":       "suburban",
        "Grand Glacier":      "snow",
        "Fencing Fields":     "farm",
        "Pleasant Piazza":    "suburban",
        "Classy Courts":      "suburban",
        "Lavish Lair":        "highland",
        "Nitrodrome":         "industrial",
        "Mount Olympus":      "highland",
        "Brawler's Battleground": "open",
        "Restored Reels":     "suburban",
        "Brutal Beachhead":   "beach",
    },
    "Chapter 6": {
        "Shogun's Solitude":  "highland",
        "Spirit Shrine":      "forest",
        "Seaport City":       "urban",
        "Demon's Dojo":       "highland",
        "Floating Rings":     "open",
        "Gale Gate":          "plains",
        "Paradise Cove":      "beach",
        "Grotto Gables":      "suburban",
        "Rebel's Roost":      "forest",
        "Cliffside Cauldron": "highland",
    },
}

# ── Creative Gallery Set IDs ───────────────────────────────────
# These are the official gallery/prefab names visible in UEFN's
# "Place Actors > Galleries" panel. The creator drags a Gallery device
# onto the island and these IDs appear in its asset list.
CREATIVE_GALLERIES = {
    # Residential / Suburban building sets
    "suburban_house_a": {
        "gallery_id": "Athena_Residential_House_Gallery_A",
        "content_hint": "Place Actors → Galleries → Residential House Set A",
        "pieces": {
            "wall_plain":       "Prop_Residential_Wall_Plain_01",
            "wall_window":      "Prop_Residential_Wall_Window_01",
            "wall_window_lg":   "Prop_Residential_Wall_Window_Large_01",
            "wall_door":        "Prop_Residential_Wall_DoorFrame_01",
            "wall_corner":      "Prop_Residential_Wall_Corner_01",
            "floor":            "Prop_Residential_Floor_01",
            "roof_gable":       "Prop_Residential_Roof_Gable_01",
            "roof_hip":         "Prop_Residential_Roof_Hip_01",
            "roof_cap":         "Prop_Residential_Roof_Cap_01",
            "door_front":       "Prop_Residential_Door_Front_01",
            "door_garage":      "Prop_Residential_GarageDoor_01",
            "window_sash":      "Prop_Residential_Window_Sash_01",
            "porch_beam":       "Prop_Residential_Porch_Beam_01",
            "porch_railing":    "Prop_Residential_Porch_Railing_01",
            "chimney":          "Prop_Residential_Chimney_01",
            "foundation":       "Prop_Residential_Foundation_01",
        },
    },
    "suburban_house_b": {
        "gallery_id": "Athena_Residential_House_Gallery_B",
        "content_hint": "Place Actors → Galleries → Residential House Set B",
        "pieces": {
            "wall_plain":       "Prop_Residential_B_Wall_Plain_01",
            "wall_window":      "Prop_Residential_B_Wall_Window_01",
            "wall_door":        "Prop_Residential_B_Wall_DoorFrame_01",
            "floor":            "Prop_Residential_B_Floor_01",
            "roof_gable":       "Prop_Residential_B_Roof_Gable_01",
            "roof_hip":         "Prop_Residential_B_Roof_Hip_01",
            "door_front":       "Prop_Residential_B_Door_Front_01",
            "door_garage":      "Prop_Residential_B_GarageDoor_01",
            "window_sash":      "Prop_Residential_B_Window_01",
            "chimney":          "Prop_Residential_B_Chimney_01",
        },
    },
    "tilted_towers_block": {
        "gallery_id": "Athena_TiltedTowers_Gallery",
        "content_hint": "Place Actors → Galleries → Tilted Towers Set",
        "pieces": {
            "wall_brick":       "Prop_TT_Wall_Brick_01",
            "wall_concrete":    "Prop_TT_Wall_Concrete_01",
            "wall_glass":       "Prop_TT_Wall_Glass_01",
            "floor_concrete":   "Prop_TT_Floor_Concrete_01",
            "roof_flat":        "Prop_TT_Roof_Flat_01",
            "roof_parapet":     "Prop_TT_Roof_Parapet_01",
            "door_commercial":  "Prop_TT_Door_Commercial_01",
            "awning":           "Prop_TT_Awning_01",
            "sign_blank":       "Prop_TT_Sign_Blank_01",
        },
    },
    "retail_row_block": {
        "gallery_id": "Athena_RetailRow_Gallery",
        "content_hint": "Place Actors → Galleries → Retail Row Set",
        "pieces": {
            "wall_storefront":  "Prop_RR_Wall_Storefront_01",
            "wall_brick":       "Prop_RR_Wall_Brick_01",
            "awning_striped":   "Prop_RR_Awning_Striped_01",
            "floor":            "Prop_RR_Floor_01",
            "roof_sloped":      "Prop_RR_Roof_Sloped_01",
            "door_shop":        "Prop_RR_Door_Shop_01",
            "window_display":   "Prop_RR_Window_Display_01",
            "sign_grocery":     "Prop_RR_Sign_Grocery_01",
        },
    },
    "pleasant_park_block": {
        "gallery_id": "Athena_PleasantPark_Gallery",
        "content_hint": "Place Actors → Galleries → Pleasant Park Set",
        "pieces": {
            "wall_siding":      "Prop_PP_Wall_Siding_01",
            "wall_siding_w":    "Prop_PP_Wall_Siding_Window_01",
            "roof_gable":       "Prop_PP_Roof_Gable_01",
            "roof_porch":       "Prop_PP_Roof_Porch_01",
            "door_screen":      "Prop_PP_Door_Screen_01",
            "fence_picket":     "Prop_PP_Fence_Picket_01",
            "fence_post":       "Prop_PP_Fence_Post_01",
            "driveway_slab":    "Prop_PP_Driveway_Slab_01",
            "mailbox":          "Prop_PP_Mailbox_01",
        },
    },
    "industrial_block": {
        "gallery_id": "Athena_Industrial_Gallery",
        "content_hint": "Place Actors → Galleries → Industrial / Warehouse Set",
        "pieces": {
            "wall_corrugated":  "Prop_Ind_Wall_Corrugated_01",
            "wall_concrete":    "Prop_Ind_Wall_Concrete_01",
            "roof_metal":       "Prop_Ind_Roof_Metal_01",
            "floor_concrete":   "Prop_Ind_Floor_Concrete_01",
            "door_roller":      "Prop_Ind_Door_RollerDoor_01",
            "door_side":        "Prop_Ind_Door_Side_01",
            "catwalk":          "Prop_Ind_Catwalk_01",
            "pipe_lg":          "Prop_Ind_Pipe_Large_01",
            "tank":             "Prop_Ind_Tank_01",
            "chimney_ind":      "Prop_Ind_Chimney_01",
        },
    },
    "ch5_nori_suburban": {
        "gallery_id": "Nori_Suburban_Gallery",
        "content_hint": "Place Actors → Galleries → Chapter 5 Suburban Set",
        "pieces": {
            "wall_plain":       "Prop_Nori_Wall_Plain_01",
            "wall_window":      "Prop_Nori_Wall_Window_01",
            "wall_brick":       "Prop_Nori_Wall_Brick_01",
            "roof_gable":       "Prop_Nori_Roof_Gable_01",
            "roof_metal":       "Prop_Nori_Roof_Metal_01",
            "door_front":       "Prop_Nori_Door_Front_01",
            "door_garage":      "Prop_Nori_GarageDoor_01",
            "fence_wood":       "Prop_Nori_Fence_Wood_01",
            "fence_chain":      "Prop_Nori_Fence_Chain_01",
            "driveway":         "Prop_Nori_Driveway_01",
            "mailbox":          "Prop_Nori_Mailbox_01",
            "porch":            "Prop_Nori_Porch_01",
        },
    },
    "ch5_greek_landmark": {
        "gallery_id": "Nori_Greek_Gallery",
        "content_hint": "Place Actors → Galleries → Chapter 5 Greek / Olympus Set",
        "pieces": {
            "column_doric":     "Prop_Greek_Column_Doric_01",
            "column_ionic":     "Prop_Greek_Column_Ionic_01",
            "wall_marble":      "Prop_Greek_Wall_Marble_01",
            "floor_marble":     "Prop_Greek_Floor_Marble_01",
            "pediment":         "Prop_Greek_Pediment_01",
            "entablature":      "Prop_Greek_Entablature_01",
            "statue_base":      "Prop_Greek_StatueBase_01",
            "arch":             "Prop_Greek_Arch_01",
            "steps":            "Prop_Greek_Steps_01",
        },
    },
    "ch6_japanese_block": {
        "gallery_id": "Kyushu_Japanese_Gallery",
        "content_hint": "Place Actors → Galleries → Chapter 6 Japanese Architecture Set",
        "pieces": {
            "wall_shoji":       "Prop_JP_Wall_Shoji_01",
            "wall_wood":        "Prop_JP_Wall_Wood_01",
            "wall_bamboo":      "Prop_JP_Wall_Bamboo_01",
            "roof_curved":      "Prop_JP_Roof_Curved_01",
            "roof_hip":         "Prop_JP_Roof_Hip_01",
            "roof_eave":        "Prop_JP_Roof_Eave_01",
            "torii_gate":       "Prop_JP_ToriiGate_01",
            "lantern_stone":    "Prop_JP_Lantern_Stone_01",
            "wall_fence_bamboo":"Prop_JP_Fence_Bamboo_01",
            "garden_stone":     "Prop_JP_GardenStone_01",
            "floor_tatami":     "Prop_JP_Floor_Tatami_01",
            "sliding_door":     "Prop_JP_Door_Sliding_01",
        },
    },
}

# ── Yard / outdoor prop catalog ───────────────────────────────
OUTDOOR_PROPS = {
    "fence_picket":     "Prop_Outdoor_Fence_Picket_01",
    "fence_chain_link": "Prop_Outdoor_Fence_ChainLink_01",
    "fence_wood_rail":  "Prop_Outdoor_Fence_WoodRail_01",
    "fence_post":       "Prop_Outdoor_FencePost_01",
    "gate_picket":      "Prop_Outdoor_Gate_Picket_01",
    "gate_metal":       "Prop_Outdoor_Gate_Metal_01",
    "driveway_plain":   "Prop_Outdoor_Driveway_Concrete_01",
    "driveway_brick":   "Prop_Outdoor_Driveway_Brick_01",
    "driveway_gravel":  "Prop_Outdoor_Driveway_Gravel_01",
    "mailbox_standard": "Prop_Outdoor_Mailbox_Standard_01",
    "mailbox_post":     "Prop_Outdoor_Mailbox_Post_01",
    "street_light":     "Prop_Outdoor_StreetLight_01",
    "fire_hydrant":     "Prop_Outdoor_FireHydrant_01",
    "sidewalk_slab":    "Prop_Outdoor_Sidewalk_Slab_01",
    "garden_flower":    "Prop_Outdoor_Garden_Flowers_01",
    "garden_shrub":     "Prop_Outdoor_Garden_Shrub_01",
    "lawn_mower":       "Prop_Outdoor_LawnMower_01",
    "garbage_bin":      "Prop_Outdoor_GarbageBin_01",
    "trampoline":       "Prop_Outdoor_Trampoline_01",
    "basketball_hoop":  "Prop_Outdoor_BasketballHoop_01",
    "patio_table":      "Prop_Outdoor_PatioTable_01",
    "bbq_grill":        "Prop_Outdoor_BBQGrill_01",
    "car_sedan":        "Prop_Outdoor_Car_Sedan_01",
    "car_pickup":       "Prop_Outdoor_Car_Pickup_01",
    "car_suv":          "Prop_Outdoor_Car_SUV_01",
}

# ── Foliage assets by chapter / biome ─────────────────────────
FOLIAGE_ASSETS = {
    "Chapter 1": {
        "Plains":   {
            "trees":  ["Prop_Foliage_Oak_01","Prop_Foliage_Oak_02"],
            "bushes": ["Prop_Foliage_Bush_Meadow_01"],
            "grass":  ["Prop_Foliage_Grass_Meadow_01"],
        },
        "Forest":   {
            "trees":  ["Prop_Foliage_Pine_01","Prop_Foliage_Oak_03"],
            "bushes": ["Prop_Foliage_Bush_Forest_01","Prop_Foliage_Bush_Forest_02"],
            "grass":  ["Prop_Foliage_Grass_Forest_01"],
        },
        "Highland": {
            "trees":  ["Prop_Foliage_Pine_02","Prop_Foliage_Pine_Bare_01"],
            "bushes": ["Prop_Foliage_Bush_Rocky_01"],
            "grass":  ["Prop_Foliage_Grass_Rocky_01"],
        },
        "Desert":   {
            "trees":  ["Prop_Foliage_Cactus_01","Prop_Foliage_Cactus_02"],
            "bushes": ["Prop_Foliage_Bush_Desert_01"],
            "grass":  ["Prop_Foliage_Grass_Desert_01"],
        },
        "Snow":     {
            "trees":  ["Prop_Foliage_Pine_Snow_01","Prop_Foliage_Pine_Snow_02"],
            "bushes": ["Prop_Foliage_Bush_Snow_01"],
            "grass":  [],
        },
    },
    "Chapter 2": {
        "Plains":   {
            "trees":  ["Prop_Apollo_Tree_Oak_01","Prop_Apollo_Tree_Palm_01"],
            "bushes": ["Prop_Apollo_Bush_Lush_01"],
            "grass":  ["Prop_Apollo_Grass_Lush_01"],
        },
        "Jungle":   {
            "trees":  ["Prop_Apollo_Tree_Jungle_01","Prop_Apollo_Tree_Jungle_02",
                       "Prop_Apollo_Tree_Rainforest_01"],
            "bushes": ["Prop_Apollo_Bush_Tropical_01","Prop_Apollo_Bush_Jungle_01"],
            "grass":  ["Prop_Apollo_Grass_Jungle_01"],
        },
        "Swamp":    {
            "trees":  ["Prop_Apollo_Tree_Swamp_01","Prop_Apollo_Tree_Swamp_02"],
            "bushes": ["Prop_Apollo_Bush_Swamp_01","Prop_Apollo_Bush_Reed_01"],
            "grass":  ["Prop_Apollo_Grass_Swamp_01"],
        },
        "Beach":    {
            "trees":  ["Prop_Apollo_Tree_Palm_01","Prop_Apollo_Tree_Palm_02"],
            "bushes": ["Prop_Apollo_Bush_Beach_01"],
            "grass":  ["Prop_Apollo_Grass_Sand_01"],
        },
    },
    "Chapter 3": {
        "Snow":     {
            "trees":  ["Prop_Artemis_Tree_SnowPine_01","Prop_Artemis_Tree_SnowPine_02"],
            "bushes": ["Prop_Artemis_Bush_Snow_01"],
            "grass":  [],
        },
        "Plains":   {
            "trees":  ["Prop_Artemis_Tree_Oak_01"],
            "bushes": ["Prop_Artemis_Bush_Tundra_01"],
            "grass":  ["Prop_Artemis_Grass_Tundra_01"],
        },
        "Jungle":   {
            "trees":  ["Prop_Artemis_Tree_Jungle_01","Prop_Artemis_Tree_Jungle_02"],
            "bushes": ["Prop_Artemis_Bush_Jungle_01"],
            "grass":  ["Prop_Artemis_Grass_Jungle_01"],
        },
    },
    "Chapter 4": {
        "Desert":   {
            "trees":  ["Prop_Borealis_Tree_Desert_01","Prop_Borealis_Cactus_01"],
            "bushes": ["Prop_Borealis_Bush_Desert_01"],
            "grass":  ["Prop_Borealis_Grass_Sand_01"],
        },
        "Rocky":    {
            "trees":  ["Prop_Borealis_Tree_Rocky_01"],
            "bushes": ["Prop_Borealis_Bush_Rocky_01"],
            "grass":  ["Prop_Borealis_Grass_Rocky_01"],
        },
        "Plains":   {
            "trees":  ["Prop_Borealis_Tree_Oak_01","Prop_Borealis_Tree_Maple_01"],
            "bushes": ["Prop_Borealis_Bush_Plains_01"],
            "grass":  ["Prop_Borealis_Grass_Plains_01"],
        },
        "Jungle":   {
            "trees":  ["Prop_Borealis_Tree_Jungle_01","Prop_Borealis_Tree_Rainforest_01"],
            "bushes": ["Prop_Borealis_Bush_Jungle_Dense_01"],
            "grass":  ["Prop_Borealis_Grass_Jungle_01"],
        },
    },
    "Chapter 5": {
        "Plains":   {
            "trees":  ["Prop_Nori_Tree_Oak_01","Prop_Nori_Tree_Birch_01"],
            "bushes": ["Prop_Nori_Bush_Plains_01"],
            "grass":  ["Prop_Nori_Grass_Plains_01"],
        },
        "Snow":     {
            "trees":  ["Prop_Nori_Tree_SnowPine_01","Prop_Nori_Tree_SnowFir_01"],
            "bushes": ["Prop_Nori_Bush_Snow_01"],
            "grass":  [],
        },
        "Highland": {
            "trees":  ["Prop_Nori_Tree_Rocky_01","Prop_Nori_Tree_Dead_01"],
            "bushes": ["Prop_Nori_Bush_Rocky_01"],
            "grass":  ["Prop_Nori_Grass_Rocky_01"],
        },
        "Farm":     {
            "trees":  ["Prop_Nori_Tree_Oak_01"],
            "bushes": ["Prop_Nori_Bush_Hedge_01"],
            "grass":  ["Prop_Nori_Grass_Wheat_01"],
        },
        "Desert":   {
            "trees":  ["Prop_Nori_Cactus_01"],
            "bushes": ["Prop_Nori_Bush_Desert_01"],
            "grass":  ["Prop_Nori_Grass_Desert_01"],
        },
    },
    "Chapter 6": {
        "Forest":   {
            "trees":  ["Prop_Kyushu_Tree_Bamboo_01","Prop_Kyushu_Tree_Maple_01",
                       "Prop_Kyushu_Tree_Pine_01"],
            "bushes": ["Prop_Kyushu_Bush_Bamboo_01","Prop_Kyushu_Bush_Fern_01"],
            "grass":  ["Prop_Kyushu_Grass_01"],
        },
        "Highland": {
            "trees":  ["Prop_Kyushu_Tree_Pine_01","Prop_Kyushu_Tree_Bonsai_01"],
            "bushes": ["Prop_Kyushu_Bush_Rocky_01"],
            "grass":  ["Prop_Kyushu_Grass_Rocky_01"],
        },
        "Plains":   {
            "trees":  ["Prop_Kyushu_Tree_Maple_01","Prop_Kyushu_Tree_Cherry_01"],
            "bushes": ["Prop_Kyushu_Bush_Flowers_01"],
            "grass":  ["Prop_Kyushu_Grass_01"],
        },
        "Beach":    {
            "trees":  ["Prop_Kyushu_Tree_Palm_01"],
            "bushes": ["Prop_Kyushu_Bush_Beach_01"],
            "grass":  ["Prop_Kyushu_Grass_Sand_01"],
        },
    },
}

# ── Terrain material layer assets by chapter ──────────────────
TERRAIN_MATERIALS = {
    "Chapter 1": {
        "terrain":  "M_Athena_Landscape_01",
        "grass":    "M_Athena_Landscape_Grass_01",
        "dirt":     "M_Athena_Landscape_Dirt_01",
        "stone":    "M_Athena_Landscape_Stone_01",
        "sand":     "M_Athena_Landscape_Sand_01",
        "snow":     "M_Athena_Landscape_Snow_01",
        "road":     "M_Athena_Road_01",
        "water":    "M_Athena_Water_01",
    },
    "Chapter 2": {
        "terrain":  "M_Apollo_Landscape_01",
        "grass":    "M_Apollo_Landscape_Grass_Lush_01",
        "dirt":     "M_Apollo_Landscape_Dirt_01",
        "sand":     "M_Apollo_Landscape_Sand_Tropical_01",
        "swamp":    "M_Apollo_Landscape_Swamp_01",
        "road":     "M_Apollo_Road_01",
        "water":    "M_Apollo_Water_01",
    },
    "Chapter 3": {
        "terrain":  "M_Artemis_Landscape_01",
        "snow":     "M_Artemis_Landscape_Snow_01",
        "ice":      "M_Artemis_Landscape_Ice_01",
        "grass":    "M_Artemis_Landscape_Grass_01",
        "dirt":     "M_Artemis_Landscape_Dirt_01",
        "road":     "M_Artemis_Road_01",
        "water":    "M_Artemis_Water_01",
    },
    "Chapter 4": {
        "terrain":  "M_Borealis_Landscape_01",
        "sand":     "M_Borealis_Landscape_Sand_01",
        "rock":     "M_Borealis_Landscape_Rock_01",
        "grass":    "M_Borealis_Landscape_Grass_01",
        "chrome":   "M_Borealis_Landscape_Chrome_01",
        "road":     "M_Borealis_Road_01",
        "water":    "M_Borealis_Water_01",
    },
    "Chapter 5": {
        "terrain":  "M_Nori_Landscape_01",
        "grass":    "M_Nori_Landscape_Grass_01",
        "snow":     "M_Nori_Landscape_Snow_01",
        "sand":     "M_Nori_Landscape_Sand_01",
        "rock":     "M_Nori_Landscape_Rock_01",
        "mud":      "M_Nori_Landscape_Mud_01",
        "road":     "M_Nori_Road_01",
        "water":    "M_Nori_Water_01",
    },
    "Chapter 6": {
        "terrain":  "M_Kyushu_Landscape_01",
        "grass":    "M_Kyushu_Landscape_Grass_01",
        "rock":     "M_Kyushu_Landscape_Rock_01",
        "sand":     "M_Kyushu_Landscape_Sand_01",
        "cherry":   "M_Kyushu_Landscape_CherryBlossom_01",
        "road":     "M_Kyushu_Road_Stone_01",
        "water":    "M_Kyushu_Water_01",
    },
}

# ── Game mode device class names (Verse API) ──────────────────
GAME_DEVICES = {
    "player_spawner":         "player_spawner_device",
    "item_spawner":           "item_spawner_device",
    "chest_spawner":          "chest_spawner_device",
    "ammo_spawner":           "ammo_spawner_device",
    "storm_controller":       "storm_controller_device",
    "storm_beacon":           "storm_beacon_device",
    "elimination_manager":    "elimination_manager_device",
    "zone_controller":        "zone_controller_device",
    "spawn_pad":              "spawn_pad_device",
    "respawn_device":         "respawn_device",
    "score_manager":          "score_manager_device",
    "end_game_device":        "end_game_device",
    "timer_device":           "timer_device",
    "hud_message":            "hud_message_device",
    "button":                 "button_device",
    "trigger":                "trigger_device",
    "creature_spawner":       "creature_spawner_device",
    "guard_spawner":          "guard_spawner_device",
    "mutator_zone":           "mutator_zone_device",
    "beacon":                 "beacon_device",
}

# ── Biome → preferred gallery set mapping ─────────────────────
BIOME_GALLERY_MAP = {
    "Plains":   ["suburban_house_a", "suburban_house_b", "pleasant_park_block"],
    "Forest":   ["suburban_house_b", "pleasant_park_block"],
    "Jungle":   ["industrial_block"],
    "Highland": ["industrial_block", "suburban_house_b"],
    "Desert":   ["suburban_house_a"],
    "Snow":     ["suburban_house_b", "ch5_nori_suburban"],
    "Beach":    ["pleasant_park_block", "suburban_house_a"],
    "Swamp":    ["industrial_block"],
    "Farm":     ["pleasant_park_block", "suburban_house_a"],
    "Town":     ["tilted_towers_block", "retail_row_block", "suburban_house_a",
                 "suburban_house_b", "pleasant_park_block"],
    "Urban":    ["tilted_towers_block", "retail_row_block"],
    "Industrial": ["industrial_block"],
    "Japanese": ["ch6_japanese_block"],
    "Greek":    ["ch5_greek_landmark"],
}

# ── Foliage density per biome ─────────────────────────────────
FOLIAGE_DENSITY = {
    "Jungle":   {"trees": 12, "bushes": 20, "grass": 40},
    "Forest":   {"trees": 8,  "bushes": 12, "grass": 25},
    "Swamp":    {"trees": 6,  "bushes": 15, "grass": 35},
    "Plains":   {"trees": 2,  "bushes": 5,  "grass": 30},
    "Farm":     {"trees": 1,  "bushes": 3,  "grass": 20},
    "Beach":    {"trees": 2,  "bushes": 3,  "grass": 10},
    "Desert":   {"trees": 0,  "bushes": 1,  "grass": 3},
    "Snow":     {"trees": 4,  "bushes": 3,  "grass": 5},
    "Highland": {"trees": 3,  "bushes": 6,  "grass": 12},
    "Rocky":    {"trees": 1,  "bushes": 3,  "grass": 5},
    "Town":     {"trees": 1,  "bushes": 2,  "grass": 8},
    "Urban":    {"trees": 0,  "bushes": 1,  "grass": 3},
    "Water":    {"trees": 0,  "bushes": 0,  "grass": 0},
    "Peak":     {"trees": 0,  "bushes": 1,  "grass": 2},
    "Japanese": {"trees": 4,  "bushes": 6,  "grass": 15},
    "Greek":    {"trees": 2,  "bushes": 4,  "grass": 10},
}

# ── Legacy alias (keep compatibility with verse_export_generator) ──
UEFN_ASSET_CATALOG = {
    "foliage":          FOLIAGE_ASSETS,
    "building_modules": CREATIVE_GALLERIES,
    "prefabs":          CREATIVE_GALLERIES,
    "props":            OUTDOOR_PROPS,
    "materials":        TERRAIN_MATERIALS,
    "game_devices":     GAME_DEVICES,
}

# Biome thresholds (moisture-based, for classify_biomes)
BIOME_THRESHOLDS = {
    "Chapter 1":  {"Desert":(0,.15),"Plains":(.15,.45),"Forest":(.45,.65),"Highland":(.65,.85),"Snow":(.85,1)},
    "Chapter 2":  {"Swamp":(0,.12),"Plains":(.12,.35),"Jungle":(.35,.6),"Forest":(.6,.8),"Highland":(.8,1)},
    "Chapter 3":  {"Plains":(0,.2),"Forest":(.2,.4),"Highland":(.4,.7),"Snow":(.7,1)},
    "Chapter 4":  {"Desert":(0,.25),"Rocky":(.25,.5),"Plains":(.5,.7),"Jungle":(.7,1)},
    "Chapter 5":  {"Desert":(0,.15),"Plains":(.15,.4),"Forest":(.4,.6),"Highland":(.6,.8),"Snow":(.8,1)},
    "Chapter 6":  {"Beach":(0,.1),"Plains":(.1,.35),"Forest":(.35,.65),"Highland":(.65,.85),"Snow":(.85,1)},
}
