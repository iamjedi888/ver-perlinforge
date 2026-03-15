# TriptokForge Channels Guide

## Current Architecture

- Route: `routes/channels.py`
- View-model helpers: `channels_page.py`
- Template: `templates/channels.html`
- Data source: Oracle `channels` table via `oracle_db.get_channels()`
- Seed and refresh script: `seed_channels.py`

The channels page now behaves more like the news page: curated scopes, stable player sizing, richer stage fallback cards, and clear separation between replay feeds, live feeds, and external feed pages.

## Scope Model

The current channel scopes are:

- `Fortnite`
- `Builders`
- `Arena`
- `Signal`
- `Community`
- `Chill`

Those scopes are derived in `channels_page.py` so the frontend can stay consistent even before the Oracle catalog is reseeded.

## Feed Rules

Preferred source order:

1. Direct replay or playlist URLs that embed reliably.
2. Official `/videos` or `/streams` feeds when a source is better opened directly.
3. Live channel embeds only when they still make sense offline.

Current feed labels on the page:

- `Replay`: embeddable YouTube videos, playlists, Twitch VODs, or Streamable clips.
- `Live`: embeddable Twitch or Kick channels.
- `Feed`: official channel or watch pages that should open directly.

## Current Catalog Direction

`seed_channels.py` now leans harder on:

- official Fortnite watch surfaces
- official YouTube `/videos` or `/streams` feeds
- official UEFN starter playlist links
- themed video rows around artists, companies, teams, creators, or systems instead of brittle dead one-off links

That keeps the page more comfortable than a catalog full of dead or weak raw channel handles.

## Refreshing The Channel Catalog

`seed_channels.py` performs an upsert instead of skipping existing rows. Rerun it on Oracle whenever you want the live catalog to match the current curated list.

Oracle usage:

```bash
cd ~/ver-perlinforge/islandforge
read -s ORACLE_PASSWORD
export ORACLE_PASSWORD
python3 seed_channels.py
unset ORACLE_PASSWORD
sudo systemctl restart islandforge
```

## Frontend Notes

- Default player size is responsive and centered.
- Desktop users can drag the bottom-right corner of the player to resize it.
- The resized width is saved locally in the browser.
- `Reset Size` returns the player to the default calculated layout.
- The guide now exposes scope chips plus `Replay`, `Live`, and `Feed` badges.
- If a source is not embed-ready yet, the page keeps the player shell stable and renders a proper feed-state card instead of a black stage.

## Channel Roadmap

### Now

- Keep the player comfortable and stable across desktop and mobile.
- Refresh the Oracle catalog toward official replay, playlist, and feed URLs.
- Keep channel scopes aligned with the calmer curation strategy already used on `/news`.
- Keep each row anchored to a real theme, artist, player, team, company, or system.

### Next

- Add admin metadata for `embed_ready`, `official`, `scope`, and `priority`.
- Separate always-on replay rails from live event rails.
- Add a featured rail for Fortnite, UEFN, and esports priority sources.

### Later

- Multi-view mode
- Optional companion chat
- Admin UI for catalog curation without script edits
- Better source-health tracking for stale or broken feeds
