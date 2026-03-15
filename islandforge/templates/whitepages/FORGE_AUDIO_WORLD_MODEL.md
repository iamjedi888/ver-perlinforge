# Forge Audio World Model

Target design for Island Forge as an audio-driven world generator.

## Core idea

Take a real sound file, analyze it into musical and spectral features, transform those features into terrain-driving signals, and produce a believable UEFN handoff bundle rather than a random abstract map.

## Intended pipeline

1. `Audio ingest`
   - accept a user-uploaded sound file
   - normalize basic playback info
   - extract BPM, duration, onset density, loudness contour, spectral centroid, low-end energy, midrange energy, presence, brilliance, and dynamic contrast

2. `Signal profile`
   - derive a stable audio fingerprint from the extracted values
   - compute terrain weights, biome bias, landmark pressure, coastline pressure, traversal openness, and settlement spacing
   - keep this step deterministic for the same file + seed

3. `Noise field generation`
   - produce a grayscale base field or layered noise map that reflects the audio profile
   - use audio-weighted octaves, frequency emphasis, and rhythm-driven modulation
   - treat the grayscale field as one intermediate artifact, not the final terrain

4. `Perlin or fractal remap`
   - convert the intermediate field into a more natural terrain surface
   - blend perlin, ridged noise, erosion-like masks, coast shaping, river or basin passes, and traversal smoothing
   - keep the result readable at Fortnite play scale

5. `Biome classification`
   - classify terrain into believable biome regions
   - use elevation, moisture, slope, openness, and audio-derived weighting
   - bias the output toward the selected Fortnite chapter or climate theme

6. `Gameplay layout`
   - place town center
   - place farms or plot clusters
   - reserve traversal lanes, overlooks, water edges, and landmark zones
   - keep spacing usable for real Fortnite combat and exploration

7. `UEFN handoff bundle`
   - `heightmap.png`
   - `preview.png`
   - `layout.json`
   - `manifest.json`
   - `placement_plan.json`
   - generated Verse modules
   - `verse_package.zip` when packaging succeeds

8. `UEFN editor import`
   - create or open the target island in UEFN
   - if the island exceeds roughly 1 km on the widest axis, enable Streaming / World Partition before import
   - import `heightmap.png` through Landscape Mode -> Import from File
   - keep the direct square landscape lane at or below `2017 x 2017`, which fits current 2048-equivalent guidance
   - copy the generated Verse files into the project, build Verse, place the Verse-authored device or data consumer, and bind generated slots to built-in Fortnite assets in the editor

## Design rules

- The same audio file and seed should generate the same world family.
- The map should read like a plausible Fortnite island, not noise art.
- Large-world generation must clearly flag World Partition requirements.
- Generated Verse should describe placement intent and slot bindings, not pretend to bypass UEFN editor ownership.
- Builtin Fortnite assets should remain the target asset lane unless a custom project explicitly expands beyond that.
- Forge should follow the real UEFN sequence: website analysis and generation first, then landscape import, content-browser binding, and Verse/device placement inside UEFN.

## What good looks like

- bass-heavy music pushes stronger macro terrain and grounded massing
- bright, energetic tracks increase sharper ridges, detail, or denser points of interest
- softer ambient tracks produce wider traversal space, less aggressive verticality, and calmer biome transitions
- the preview image, biome layout, and gameplay spacing all feel like they belong together

## Immediate execution target

The next practical Forge milestone is:

1. make audio analysis the primary driver of generation
2. preserve deterministic seed behavior
3. improve the terrain field so it stops feeling arbitrary
4. generate UEFN-ready metadata that matches the terrain outcome
5. validate several runs in real UEFN import flow and tune from those results
