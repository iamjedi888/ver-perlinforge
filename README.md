# TriptokForge

**Fortnite esports platform + UEFN island generator.**  
Live at [triptokforge.org](https://triptokforge.org) · By [EuphoriÆ Studios](https://github.com/iamjedi888)

---

## What it does

- **Island Forge** — Upload any audio file. It analyzes frequency bands and generates a UEFN-ready 16-bit heightmap. Bass becomes mountains, rhythm becomes rivers, tone determines biomes. Supports world sizes from 500m to 81km.
- **Town Generator** — Procedural Fortnite-realistic town layout with named streets, zoned blocks, farm plots, and exact UEFN coordinates.
- **Epic OAuth** — Login with your real Epic Games account. Member dashboard with live Fortnite stats and holographic player card.
- **Platform** — Gallery, jukebox, community, esports feed, and developer reference for Verse/UEFN.

---

## Stack

- Python / Flask / gunicorn
- NumPy, SciPy, Pillow, librosa
- Oracle Cloud (ARM Ampere, Ubuntu 22.04)
- nginx + Let's Encrypt SSL
- Epic Games OAuth2

---

## Routes

| Route | Description |
|-------|-------------|
| `/` | Homepage |
| `/forge` | Island Forge (heightmap generator) |
| `/dashboard` | Member dashboard (Epic login required) |
| `/gallery` | Generated island gallery |
| `/feed` | Esports feed |
| `/jukebox` | Community jukebox |
| `/community` | Members + announcements |
| `/dev` | Verse/UEFN developer reference |
| `/admin` | Admin panel (password protected) |

---

## API

```
POST /generate
{
  "seed": 42,
  "size": 2017,
  "world_size": "double_br",
  "weights": { "sub_bass": 0.8, "tempo_bpm": 140, ... }
}
→ { preview_b64, plots_found, biome_stats, verse_constants, town_center, world_size_cm }
```

**World size presets:** `uefn_small` (500m) · `uefn_max` (1km) · `br_chapter2` (5.5km) · `double_br` (11km) · `skyrim` (37km) · `gta5` (81km)

---

## Deploy

See [DEPLOY.md](./DEPLOY.md) for Oracle VM setup, systemd service config, nginx, and 502 diagnosis.

---

## Verse files

32 Verse files for the TriptokForge RPG system live in the repo root. Boot order, biome system, farm economy, zone tiers, and NPC director are all documented in DEPLOY.md.

---

## License

Private — EuphoriÆ Studios 2026
