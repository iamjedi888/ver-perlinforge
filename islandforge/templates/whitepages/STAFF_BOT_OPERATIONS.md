# Staff + Bot Operations

## Purpose

This document defines the staff and bot control model for TriptokForge.

- `/ops` is the role-aware operator console.
- `/admin` remains the legacy full-control shell.
- Bot profiles such as `ColorsTheForce` are site-owned operator entities, not fake public user identities.

## Roles

### Admin

Admin can:

- create, update, and remove staff accounts
- create, update, and remove bot profiles
- use the legacy `/admin` modules for channels, broadcasts, announcements, and other site controls
- moderate and remove community posts
- review the operator audit log

### Moderator

Moderator can:

- edit and remove community posts
- review the moderation queue
- use no channel, broadcast, or system-control modules

Moderator cannot:

- create staff logins
- change bot profile settings
- use legacy admin modules

### Bot Operator

Bot Operator can:

- edit the linked bot profile assigned to that staff account
- tune bot scope, surfaces, tone, provider, family, model, and prompt guardrails
- review the audit rail

Bot Operator cannot:

- edit unrelated bot profiles
- use channel, broadcast, or staff modules
- operate as a silent full admin

## ColorsTheForce

Recommended defaults:

- slug: `colorstheforce`
- display name: `ColorsTheForce`
- badge: `AI Moderator`
- role label: `Moderator`
- language: `American English`

Scope priorities:

- Fortnite and UEFN
- code and computer languages
- interpersonal communication and moderation tone
- Nintendo, Microsoft, and Epic ecosystem literacy
- animals, nature, conservation, and positive community standards
- sponsorship and business-minded brand posture

Guardrails:

- clearly label it as an in-house TriptokForge AI moderator
- never claim to be an official Epic, Nintendo, or Microsoft representative
- require human approval for destructive or sitewide actions

## Provider Catalog

The provider dropdown in `/ops` is curated from official vendor documentation rather than fetched live on every page load.

Current anchors:

- Google Vertex AI / Gemini
- IBM watsonx.ai / Granite and partner-hosted models
- NVIDIA NIM / Nemotron and partner models
- Meta Llama
- Hugging Face Inference Providers

Why curated:

- stable admin UX
- predictable naming
- no runtime dependency on vendor sites
- easier internal documentation and guardrails

## Login Model

Short term:

- root admin password remains available as a fallback by leaving username blank on `/ops`

Long term:

- create named staff logins for every human staff member
- create linked bot-operator accounts for bots that need ongoing tuning
- rotate the root fallback and move it to protected server env only

## Next Steps

1. Replace the shared root fallback with explicit admin accounts only.
2. Add bot draft-post workflows with approval before publish.
3. Add per-role dashboard widgets and filtered audit views.
4. Add API-backed provider catalog refresh only if you decide it is worth the operational complexity.
