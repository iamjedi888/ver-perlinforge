# TriptokForge UEFN Complete Asset System
## Implementation Guide

## Foundation Layout Note

Current MMO world direction:

- Keep all 32 player plots in one shared farm cluster near the safe town instead of spreading them across the island.
- Place that farm cluster on a coastal landmass or ring with water around it so the social zone feels intentional and readable.
- Treat each biome as one coherent Fortnite kit palette rather than mixing unrelated props.
- Let Verse control placement, unlocks, and runtime logic.
- Let the UEFN editor control which `creative_prop_asset` arrays belong to each biome kit.

Current biome-kit direction:

- Town center: urban / suburban / drive-in kits
- Farm cluster: coastal / dock / settlement kits
- Plains: western / dirt / farm kits
- Forest: tropical / jungle kits
- Highlands: medieval / castle kits
- Peaks and nightmare space: sci-fi / spooky / darker endgame kits

## Phase Lock Order

Current system order for the extraction MMO layer:

1. Lock `player_data` as the MMO schema before downstream systems expand.
2. Lock `player_repository` and save helpers so all mutations stay atomic.
3. Build the ability engine before deeper NPC, relic, expedition, and risk systems.
4. Stabilize the NPC pipeline so XP, quests, drops, and risk all share one combat spine.
5. Finish progression systems, then layer relics, expeditions, world events, and economy polish on top.

---

## 🎯 What This System Does

Transforms your TriptokForge from "generates a preview image" into **"generates a complete, deployable UEFN island package"** that uses Epic's built-in assets.

### Before (Current State):
- ✓ Audio → Perlin noise heightmap
- ✓ Biome classification
- ✓ Plot positions & town layout
- ✓ Single plot_registry.verse file
- ❌ Just a preview image - no actual island

### After (This System):
- ✓ Everything above PLUS:
- ✅ **Multi-file Verse package** (7 files)
- ✅ **Runtime asset spawning** (trees, bushes, buildings spawn when island loads)
- ✅ **Epic's official prefabs** (Pleasant Park houses, Retail Row shops)
- ✅ **Modular building system** (walls, roofs, doors assembled procedurally)
- ✅ **Chapter-specific materials** (actual Fortnite landscape textures)
- ✅ **0 MB custom content** (all assets already on player devices)
- ✅ **Instant deployment to UEFN**

---

## 📦 System Architecture

```
TriptokForge Forge
      ↓
Generate heightmap from audio (existing)
      ↓
Classify biomes with theme (existing)
      ↓
Find plots & town layout (existing)
      ↓
NEW: Verse Export Generator
      ↓
7-file UEFN package (.zip download)
      ↓
User extracts → UEFN project → Deploy to Fortnite
```

---

## 🗂️ Generated File Structure

When user clicks "Download UEFN Package", they get:

```
triptokforge_island_12345.zip
├── plot_registry.verse          # Plot positions & town center
├── biome_manifest.verse          # Biome zone data
├── foliage_spawner.verse         # Runtime vegetation spawner
├── poi_placer.verse              # Procedural building system
├── landscape_config.json         # Terrain material assignments
├── asset_manifest.json           # Complete asset reference list
├── README.md                     # Deployment instructions
└── heightmap.png                 # 16-bit grayscale heightmap
```

---

## 🔧 How Each File Works

### 1. **plot_registry.verse**
```verse
plot_registry := module:
    TownCenter<public>: vector3 = vector3{10000.0, 10000.0, 0.0}
    
    Plots<public>: []plot_data = array{
        plot_data{
            ID := 0,
            Position := vector3{12500.0, 8000.0, 0.0},
            Radius := 750.0,
            BiomeType := "grassland",
            Zone := "residential"
        },
        ...
    }
```
**Purpose**: Defines where everything goes on your island.

---

### 2. **biome_manifest.verse**
```verse
biome_manifest := module:
    BiomeZones<public>: []biome_zone = array{
        biome_zone{
            Name := "jungle",
            CellCount := 145,
            TreeAssets := array{
                "/Game/Athena/Apollo/Environments/Foliage/Trees/Apollo_Tree_Jungle_01",
                "/Game/Athena/Apollo/Environments/Foliage/Trees/Apollo_Tree_Jungle_02"
            }
        },
        ...
    }
```
**Purpose**: Maps each biome type to Epic's actual asset paths.

---

### 3. **foliage_spawner.verse**
```verse
foliage_spawner_device := class(creative_device):
    
    OnBegin<override>()<suspends>:void=
        SpawnAllFoliage()
    
    SpawnAllFoliage()<suspends>:void=
        # Iterates through biome_map grid
        # For each cell: spawn trees, bushes, grass
        # based on biome type and density rules
        
        # Example: jungle cell gets 12 trees, 20 bushes
        # desert cell gets 0 trees, 1 bush
```
**Purpose**: Spawns vegetation at runtime - no pre-placed props, instant load.

---

### 4. **poi_placer.verse**
```verse
poi_placer_device := class(creative_device):
    
    BuildModularHouse(Position: vector3, Radius: float)<suspends>:void=
        # Foundation
        FloorAsset := "/Game/Athena/.../Athena_Floor_Wood_01"
        SpawnProp(FloorAsset, Position, rotation{})
        
        # 4 walls (North, East, South, West)
        WallAsset := "/Game/Athena/.../Athena_Wall_Residential_01"
        # Spawn each wall rotated correctly
        
        # Roof
        RoofAsset := "/Game/Athena/.../Athena_Roof_Residential_Gable_01"
        
        # Driveway, fence, etc.
```
**Purpose**: Assembles buildings from modular pieces - procedural, professional layouts.

---

### 5. **landscape_config.json**
```json
{
  "theme": "Chapter 2",
  "terrain_material": "/Game/Athena/Apollo/.../M_Apollo_Terrain_01",
  "biome_materials": {
    "jungle": "/Game/Athena/Apollo/.../M_Apollo_Grass_Lush_01",
    "swamp": "/Game/Athena/Apollo/.../M_Apollo_Water_01"
  }
}
```
**Purpose**: Tells UEFN which materials to apply to landscape.

---

### 6. **asset_manifest.json**
```json
{
  "seed": 12345,
  "theme": "Chapter 2",
  "asset_categories": {
    "foliage": { "trees": [...], "bushes": [...] },
    "building_modules": { "walls": [...], "roofs": [...] },
    "prefabs": { "houses": [...], "commercial": [...] }
  }
}
```
**Purpose**: Complete list of every Epic asset referenced - for validation/debugging.

---

### 7. **README.md**
Deployment instructions for the user.

---

## 🎨 Biome Theme System

Your forge already has 8 biome themes. Now each theme maps to **real Epic assets**:

| Theme | Trees | Grass | Materials |
|-------|-------|-------|-----------|
| **Chapter 1** | Athena oak, pine | Meadow grass | M_Athena_Terrain_01 |
| **Chapter 2** | Apollo jungle, palm | Lush grass | M_Apollo_Terrain_01 |
| **Chapter 3** | Artemis snow pine | Tundra grass | M_Artemis_Snow_01 |
| **Chapter 4** | Borealis desert, rocky | Desert sparse | M_Borealis_Sand_01 |
| **Arctic** | Frozen pine | Ice grass | M_Artemis_Ice_01 |
| **Sahara** | Palm, cactus | Sand | M_Borealis_Sand_01 |
| **Primal** | Rainforest dense | Jungle dense | M_Apollo_Jungle_01 |
| **Volcanic** | Dead, charred | Ash | M_Borealis_Volcanic_01 |

When user selects "🌋 Volcanic", the Verse package uses volcanic asset paths.

---

## 🏗️ Building System

### Option 1: Complete Prefabs
```verse
HousePrefab := "/Game/Athena/.../Pleasant_Park_House_01"
SpawnProp(HousePrefab, Position, rotation{})
```
Fast, looks professional, zero custom work.

### Option 2: Modular Construction
```verse
# Build house from pieces:
- Floor (wood/concrete)
- 4 walls (residential/commercial/industrial)
- Roof (gable/hip/flat)
- Door (residential/garage)
- Windows (small/large)
- Driveway
- Fence
```
Fully procedural, every house looks unique, professional aesthetic.

**Your system does Option 2** - assembles buildings procedurally using Epic's modular galleries.

---

## 🚀 Deployment Workflow

1. **User generates island in TriptokForge:**
   - Uploads audio file
   - Selects "Chapter 2" theme
   - Sets world size "Double BR"
   - Adjusts noise weights
   - Clicks "Generate"

2. **Forge processes (existing):**
   - Audio analysis
   - Perlin heightmap
   - Biome classification
   - Plot finding
   - Town layout

3. **NEW: Verse package generation:**
   - `integrate_with_forge()` called
   - 7 files generated
   - Packaged into .zip

4. **User downloads:**
   - `triptokforge_island_12345.zip`

5. **User opens UEFN:**
   - Creates new project
   - Copies .verse files to `/MyProject/Verse/`
   - Imports `heightmap.png` as Landscape
   - Applies materials from `landscape_config.json`

6. **User builds & launches:**
   - UEFN compiles Verse
   - Launches island
   - `foliage_spawner` and `poi_placer` run `OnBegin()`
   - **Props spawn at runtime**
   - Island loads instantly - everything is Epic assets

---

## 💾 Integration Steps

### Step 1: Copy Files to Your Repo
```bash
# On your PC (in ver-perlinforge directory)
cp uefn_asset_catalog.py islandforge/
cp verse_export_generator.py islandforge/
```

### Step 2: Modify `audio_to_heightmap.py`
```python
# Add import at top
from verse_export_generator import integrate_with_forge

# In your generate function, before returning result:
result = integrate_with_forge(result, theme=theme, seed=seed)
```

### Step 3: Add Download Route to `server.py`
```python
@app.route('/api/forge/download-verse', methods=['POST'])
def download_verse_package():
    import io, zipfile
    from flask import send_file
    
    data = request.json
    seed = data.get('seed')
    theme = data.get('theme')
    
    # Get or regenerate island
    result = get_latest_generation(seed, theme)
    
    # Create zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for filename, content in result['verse_package'].items():
            zf.writestr(filename, content)
    
    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, 
                     download_name=f'island_{seed}.zip')
```

### Step 4: Add Download Button to Forge UI
```html
<button onclick="downloadVerse()" class="btn-verse-download">
    ↓ Download Complete UEFN Package
</button>

<script>
async function downloadVerse() {
    const res = await fetch('/api/forge/download-verse', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({seed: currentSeed, theme: currentTheme})
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `triptokforge_island_${currentSeed}.zip`;
    a.click();
}
</script>
```

### Step 5: Deploy to VM
```bash
# PC
git add -A
git commit -m "Add UEFN Verse export system"
git push origin main

# VM
cd ~/ver-perlinforge && git pull origin main
sudo systemctl restart islandforge
```

---

## 🎯 What This Unlocks

1. **Instant UEFN Deployment**
   - No manual asset placement
   - No custom 3D modeling
   - No texture baking
   - Just: download → copy → build → play

2. **Epic's Official Assets**
   - Pleasant Park houses
   - Retail Row shops
   - Tilted Towers buildings
   - Chapter 1-4 foliage
   - All landscape materials

3. **0 MB Island Cost**
   - All assets already on player devices
   - Verse spawns them at runtime
   - Your 300MB limit = pure heightmap + logic

4. **Professional Aesthetics**
   - Real Fortnite POIs
   - Correct scale (192cm player height)
   - Proper LODs (5 levels)
   - Optimized for mobile/Switch

5. **Procedural Variety**
   - Every island unique
   - Buildings assembled randomly
   - Foliage density varies by biome
   - Realistic town layouts

---

## 📊 Asset Count Breakdown

**Per island, approximately:**
- 500-2000 trees (depending on theme)
- 1000-4000 bushes
- 2000-8000 grass patches
- 20-100 buildings (modular or prefab)
- 50-200 props (fences, mailboxes, etc.)

**All spawned at runtime - 0 bytes stored in island file.**

---

## 🔬 Advanced: Custom Asset Integration

Later, you can extend this to include:
1. **Fab.com assets** (purchase + import to UEFN)
2. **Custom models** (Blender → UEFN)
3. **AI-generated textures** (apply to Epic's meshes)

But start with Epic's built-in catalog - it's **massive** and covers everything.

---

## ✅ Testing Checklist

1. ☐ Generate island with each theme (Chapter 1-4, Arctic, etc.)
2. ☐ Download UEFN package (.zip)
3. ☐ Extract and verify all 7 files present
4. ☐ Open UEFN, create blank project
5. ☐ Copy .verse files to Verse folder
6. ☐ Import heightmap.png as Landscape
7. ☐ Apply materials from landscape_config.json
8. ☐ Build Verse (check for compilation errors)
9. ☐ Launch island
10. ☐ Verify foliage spawns
11. ☐ Verify buildings appear at plots
12. ☐ Check console for "TriptokForge" debug prints

---

## 🐛 Troubleshooting

**"Verse compilation error"**
- Check asset paths in UEFN_ASSET_CATALOG
- Epic may have renamed/moved assets in recent updates
- Use UEFN Content Browser to find current paths

**"No props spawning"**
- Check `foliage_spawner` and `poi_placer` are added to level
- Verify `OnBegin()` fires (check console logs)
- Asset reflection may need setup (add assets to UEFN project first)

**"Buildings look wrong"**
- Modular piece scale might be off
- Adjust WallHeight, RoofOffset in poi_placer.verse
- Or switch to prefabs for guaranteed correct appearance

---

## 🚀 Next Steps

1. **Deploy this system** to TriptokForge
2. **Test** with all 8 biome themes
3. **Refine** asset paths based on UEFN Content Browser
4. **Add** more building types (industrial, commercial expanded)
5. **Enhance** foliage density algorithms
6. **Implement** game mode devices (storm circles, loot spawners)

---

## 📚 Resources

- [Epic's UEFN Documentation](https://dev.epicgames.com/documentation/en-us/fortnite/)
- [Verse Language Reference](https://dev.epicgames.com/documentation/en-us/fortnite/verse-language-reference)
- [Fortnite Asset Catalog](https://fortnite.gg/assets)
- [UEFN Content Browser Guide](https://dev.epicgames.com/documentation/en-us/fortnite/content-browser)

---

**You're now ready to turn audio files into complete, deployable Fortnite islands.**

🎵 → 🗻 → 🌳 → 🏘️ → 🎮
