# Member Hub Roadmap

## Vision

The member area should feel like a private room, not a default account page.

- One wall: generated island previews, named saves, and build history
- One wall: player cards, badges, linked systems, and TriptokForge-native achievements
- Main screen: premium telemetry deck with ticker rails, deltas, timeline charts, heatmaps, ranked ladders, and ecosystem cards
- Visual direction: Bloomberg terminal precision + JARVIS control room + luxury motorsport garage

## Real data surfaces

### Available now
- Epic-authenticated identity and session state
- Oracle platform data: islands, uploads, tickets, announcements, room theme, member profile state
- Public Fortnite surfaces: shop, cosmetics, later published-island analytics
- Keyed Fortnite stat snapshots when `FORTNITE_API_KEY` is configured

### Future but valid
- TriptokForge-native achievements, ranks, and badges stored in Oracle
- Product-specific EOS stats/achievements for systems we own and configure
- Tournament history, match archive, replay metadata, and channel preferences

### Not a valid assumption
- universal saved player data across unrelated Epic games
- arbitrary private game telemetry from every title just because the player logged in with Epic

## Room layout target

### Island wall
- masonry or panel-grid of generated previews
- hover card with seed, run folder, world size, theme, plots, and generated date
- quick actions: open save, download package, promote to featured, compare runs

### Player wall
- identity card
- locker / skin card
- rank / role card
- achievement / badge cards
- ecosystem cards for linked services

### Main screen
- ticker rail for deltas and live notes
- stat cards with positive / negative movement
- chart stack:
  - timeline
  - heatmap by hour/day
  - category volume
  - ladder / leaderboard panel
  - event feed

## Build phases

1. Stabilize current dashboard telemetry from real site data
2. Add island wall from saved forge runs
3. Add player-card rack and badge model
4. Add delta math and trend tracking for stats
5. Add time heatmap and event feed
6. Add immersive 3D or faux-3D panels after the real data rails exist

## Design rules

- keep the dashboard readable first
- no fake “live” data if the backend cannot source it
- prefer Oracle-backed member history over hardcoded placeholders
- layer animation carefully so charts stay usable
- treat the main screen as a control surface, not a poster wall
