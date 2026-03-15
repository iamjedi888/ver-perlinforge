# TriptokForge Arena Roadmap

## Purpose

Build a real esports wing for the site instead of leaving arena intent scattered between channels, leaderboard, feed, and old notes.

Current live route:

- `/arena`

## Core concept

The arena should feel like a premium console deck:

- theater screen at the front for featured match, replay, or finals-night briefing
- giant leaderboard wall to the left
- popcorn and concession counter behind the seating
- right-side ops rail for tournament control, team surfaces, clips, and schedule
- Ironman UI meets motorsport pit wall meets luxury tuner garage

## Phase order

1. Spectator Room
   - roamable A-Frame room
   - leaderboard wall
   - main theater screen
   - camera focus presets
   - right-rail ops stack

2. Tournament Ops
   - check-in desk
   - lane schedule
   - rule cards
   - finals-night messaging
   - admin quick actions

3. Replay Lab
   - VOD shelves
   - clip review cards
   - coaching notes
   - player spotlight panels

4. Team Garage
   - squad cards
   - roster bays
   - season calendar
   - standings snapshots

5. Broadcast Booth
   - caster desk
   - sponsor surfaces
   - event title cards
   - hero clips

6. Prize Vault
   - reward tracks
   - ticket sinks
   - featured unlocks
   - event cosmetics and merch messaging

## Site subsection ideas

- Arena
- Tournaments
- Replay Lab
- Team Garage
- Broadcast Booth
- Stats Lab
- Clips
- Rules Center
- Check-In Desk
- Prize Vault

## Data sources to aggregate

- site members and wins from Oracle
- channel catalog for live watch routing
- announcements for ops signal
- Fortnite public ecosystem data
- tournament state once admin tools exist

## Asset workflow

Fab and Megascans links are useful as source lockers, but direct anonymous model URIs are not the same thing as public website links.

Recommended pipeline:

1. Acquire asset through Fab with authenticated Epic account
2. Export GLB or engine-ready files
3. Optimize mesh and textures
4. Host approved web models under `/static/models/arena/`
5. Replace procedural stand-ins in `templates/arena.html` and `static/js/arena.js`

## Candidate source packs

- Theater Interior
  - https://www.fab.com/listings/72f2981d-e02f-4641-9fb6-5bbb0fb9d5ef
- Ultimate Cinema & Movie Theater - Auditorium, Lobby & Snacks
  - https://www.fab.com/listings/7efdc1c8-0d4d-4ff2-bf99-d4a374d018dd
- Movie Theater Pack - Realistic Movie Theater Props
  - https://www.fab.com/listings/110c753b-78d2-4028-8a4d-3b196bae136c
- Stylized Popcorn Machine / Cart - Game Ready
  - https://www.fab.com/listings/6b850edd-ea1a-4840-915a-027de4aa71fe
- Sci-Fi Wall Display Panel - Modular Futuristic Screen
  - https://www.fab.com/listings/6f9d35eb-0ddd-48d9-96fa-60d8955f5c10
- Unfinished Building
  - https://www.fab.com/listings/25f2e7e5-5cca-48a5-99a3-35c38b8240ac
- Abandoned Warehouse
  - https://www.fab.com/listings/eb6fd9a2-9658-42cb-966c-90e5099b4aa3
