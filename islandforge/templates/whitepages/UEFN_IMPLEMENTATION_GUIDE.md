# TriptokForge UEFN Implementation Guide

## Purpose

This is the practical handoff guide for turning a Forge run into a usable UEFN island build.
The goal is not "random terrain plus random props." The goal is a Fortnite-readable island package with:

- a believable heightmap silhouette
- a coherent biome plan
- a clustered 32-plot farm zone near town
- chapter-aware material and gallery guidance
- generated placement data that can be bound to built-in Fortnite assets in UEFN

## Official UEFN lane

Forge should target the current official workflow, not a fake zero-editor shortcut:

1. Analyze the sound file on TriptokForge.
2. Generate a heightmap, preview, placement plan, manifest, and Verse handoff package.
3. In UEFN, create or open the destination island.
4. If the island exceeds roughly 1 km on its widest axis, enable Streaming / World Partition before import.
5. Import `heightmap.png` through Landscape Mode -> Import from File.
6. Keep the direct square landscape lane at or below `2017 x 2017`, which fits current 2048-equivalent guidance for UEFN landscape import.
7. Copy the generated Verse files into the project, build Verse, place the Verse-authored device or consumer, and bind generated slots to built-in Fortnite assets from the Fortnite content browser.
8. Launch a session, validate terrain readability, streaming cells, and asset bindings, then iterate with the next numbered Forge run.

## Current world direction

- Keep all 32 player plots in one shared cluster near the safe town.
- Put that cluster on a coastal landmass or ring so the social space reads clearly.
- Use one coherent Fortnite kit per biome instead of mixing unrelated props.
- Let Forge generate terrain, plot coordinates, placement plans, and slot manifests.
- Let the UEFN editor bind built-in Fortnite assets to the generated slot names.

## What Forge now outputs

Each run saves into `outputs/WorldName#N/` and should contain:

- `heightmap.png`
- `preview.png`
- `layout.json`
- `manifest.json`
- `placement_plan.json`
- generated Verse data files
- `verse_package.zip` when packaging succeeds

## What the generated files are for

- `heightmap.png`
  Landscape import source.

- `preview.png`
  Visual reference so you can verify coastline, plot cluster, town center, and biome readability before import.

- `layout.json`
  Metadata, plot positions, town center, zone centers, and World Partition warning data.

- `placement_plan.json`
  The concrete handoff file for town, plot, landmark, and foliage-anchor placement.

- `asset_manifest.json`
  Slot-by-slot checklist for built-in Fortnite foliage and gallery bindings.

- `landscape_config.json`
  Theme-aware material guidance and landscape import settings.

- Verse files
  Data modules and binding scaffolds for plot registry, biome summaries, foliage slots, and POI site plans.

## Important boundary

UEFN does not let a generated package silently claim arbitrary cooked Fortnite assets at publish time.
That means the correct workflow is:

1. Forge generates the terrain, layout, and binding plan.
2. UEFN imports the landscape.
3. The creator binds generated slot names to built-in Fortnite assets in the editor.
4. Project-specific Verse or devices use those bound slots at runtime.

This is still the right workflow. It is realistic, controllable, and publish-safe.

## Streaming and World Partition rule

If the selected world scale exceeds roughly 1 km on the widest axis:

1. Open `Edit -> Project Settings -> World`
2. Enable `World Partition`
3. Open `World Settings`
4. Enable `Streaming`
5. Import the generated heightmap after that

For larger worlds, also keep these defaults in mind:

- Section Size: `63x63`
- Sections Per Component: `2x2`

The same warning should appear in Forge, `layout.json`, and the generated README. The generated direct square landscape should stay at or below `2017 x 2017` for the cleanest current UEFN import lane.

## Verse and asset binding workflow

- Put the generated Verse files into the project instead of treating them like detached notes.
- Build Verse from inside UEFN after the files are added.
- Place the Verse-authored device or whichever project-specific consumer reads the generated data.
- Bind generated slot names to built-in Fortnite galleries, props, foliage, or materials in the editor.
- Treat the package as a deterministic terrain and placement contract, not an attempt to silently bypass editor ownership of Fortnite content.

## Fortnite realism rules

The package should keep following these rules:

- large readable landmasses, not noisy islands
- broad biome zones, not pixel soup
- flat playable interior space with a clearer storm-funnel shape
- deliberate POI pads and road relationships
- clustered farm plots near town
- chapter-aware gallery and material guidance
- a clear distinction between generated plan data and editor-side asset binding

## Biome kit direction

- Town center: urban, suburban, drive-in, service-town kits
- Farm cluster: coastal settlement, dock, and farmland kits
- Plains: farm, dirt-road, suburban edge kits
- Forest: jungle or woodland kits depending on chapter theme
- Highlands: fortress, ridge, or shrine-style kits
- Peaks and endgame space: heavier landmark, boss, or spectacle kits

## Recommended build order

1. Lock `player_data`
2. Lock `player_repository` mutation helpers
3. Build the combat spine
4. Stabilize NPC, XP, quest, and drop routing
5. Keep iterating Forge so every generated run is easier to import and bind in UEFN

## Next improvements

- Validate a fresh generated run directly inside UEFN and tune placement spacing from that real import
- Expand runtime Verse consumers from data-only modules into project-ready spawn managers
- Add per-theme town landmark profiles and road spline suggestions
- Add a visual import checklist inside WhitePages with screenshots

## Official references

- Creating Landscapes in Unreal Editor for Fortnite
- Streaming and HLODs in Unreal Editor for Fortnite
- Using Prefabs and Galleries in Fortnite Creative
- Programming with Verse in Unreal Editor for Fortnite
- Create Your Own Device Using Verse in Unreal Editor for Fortnite
