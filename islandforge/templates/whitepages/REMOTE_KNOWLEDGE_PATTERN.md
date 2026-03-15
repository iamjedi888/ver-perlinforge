# Remote Knowledge Pattern

## Core idea

Do not mirror a giant archive into Oracle.

Do not even require TriptokForge to store the full archive locally unless there is a specific need.

Instead, use a **pointer manifest**:

- one small JSON file hosted from GitHub Pages or another GitHub-served static location
- each item contains title, tags, summary, and source URLs
- the site reads that manifest and decides what to link, summarize, or surface

## Why this is better

- almost no Oracle storage usage
- almost no Oracle database writes
- simple site integration
- easy to reuse in WhitePages, bots, ops tools, and future dashboards

## Important security truth

If the browser can read it directly, it is **public**, not encrypted.

You can make it:

- signed
- hashed
- versioned
- integrity-checked

But that is not the same as encryption.

If you want a source to stay private:

- keep the full source in a private GitHub repo
- store only public-safe metadata in the manifest
- let bots or admin tools fetch the private source server-side only when needed

## Recommended split

### Public-safe manifest

Contains:

- title
- tags
- short summary
- repo URL
- public reference URL
- optional raw URL
- recommended surfaces
- integrity hint

Used by:

- WhitePages directory pages
- featured resource cards
- bot post drafting
- walkthrough linking

### Private source

Contains:

- full playbooks
- private notes
- bot instructions
- internal architecture docs

Access pattern:

- fetched only server-side
- admin or bot-operator initiated
- not exposed directly to public browser clients

## What the site should do

### WhitePages

- show a directory of curated knowledge items
- group by tags like `3D`, `UEFN`, `dashboard`, `bot`, `broadcast`
- link out to source repos and notes

### Bots

- read one item from the manifest
- optionally fetch full source if allowed
- draft:
  - informational posts
  - walkthroughs
  - upgrade notes
  - moderation playbooks

### Admin / Ops

- choose source item
- review summary
- publish as draft or approved post

## One-line integration model

The cleanest site-level integration is one configured URL:

```text
KNOWLEDGE_MANIFEST_URL=https://your-pages-site.example/knowledge/manifest.json
```

Everything else fans out from that.

## Recommendation

Adopt this in phases:

1. pointer manifest only
2. WhitePages directory from that manifest
3. bot/admin draft-post flow from selected manifest items
4. optional private-source digestion for admin-only workflows
