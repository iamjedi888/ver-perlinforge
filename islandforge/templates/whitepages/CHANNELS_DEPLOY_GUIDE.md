# TriptokForge Channels Guide

## Current Architecture

- Route: `routes/channels.py`
- View-model helpers: `channels_page.py`
- Template: `templates/channels.html`
- Data source: Oracle `channels` table via `oracle_db.get_channels()`
- Seed and refresh script: `seed_channels.py`

The channels page is now a Jinja template with a bounded player stage, footer consistency, and a saved resizable player width on desktop.

## Feed Rules

For the page to play reliably inside the embedded player, `embed_url` should be one of:

- Twitch channel or VOD URLs
- YouTube watch URLs
- YouTube playlist URLs
- Kick channel URLs
- Streamable URLs

Raw YouTube channel handles, search result URLs, and other non-embed pages should be treated as temporary catalog items. The page can open them externally, but they are not the long-term target.

## Refreshing The Channel Catalog

`seed_channels.py` now performs an upsert instead of skipping existing rows. That means you can refresh the live Oracle catalog with updated URLs and descriptions by rerunning the script.

Oracle usage:

```bash
cd ~/ver-perlinforge/islandforge
export ORACLE_PASSWORD='your-password'
python3 seed_channels.py
sudo systemctl restart islandforge
```

## Current Frontend Notes

- Default player size is responsive and centered.
- Desktop users can drag the bottom-right corner of the player to resize it.
- The resized width is saved locally in the browser.
- `Reset Size` returns the player to the default calculated layout.
- If a source is not embed-ready yet, the page keeps the player shell stable and switches the call-to-action to `Open Feed`.

## Channel Roadmap

### Now

- Keep the player comfortable and stable across desktop and mobile.
- Replace legacy raw channel handles with direct replay, playlist, or live-feed URLs.
- Prioritize official Fortnite, UEFN, esports, and creator-safe feeds first.

### Next

- Add a curated "embed-ready" quality pass for every category.
- Separate always-on replay feeds from external-only sources.
- Add admin metadata for `embed_ready`, `official`, and `priority`.

### Later

- Multi-view mode
- Optional companion chat
- Scheduled featured channel rail
- Admin UI for catalog curation without script edits

## Practical Rule

When adding a new channel:

1. Prefer a source that actually embeds.
2. Prefer a source that has reliable replay or always-on value.
3. If it is external-only for now, still allow it, but mark it for later replacement.
