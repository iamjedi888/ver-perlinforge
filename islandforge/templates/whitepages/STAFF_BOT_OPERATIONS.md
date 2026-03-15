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

### User

User is a low-privilege internal profile type.

Use it for:

- QA walkthrough accounts
- read-only or near-read-only staff presence
- future limited operator lanes

Do not use it as a public site signup path.

## Profile Factory

The preferred control surface is a single `Profile Factory` module in `/ops`.

Admin can choose:

- `Admin`
- `Moderator`
- `Bot Operator`
- `User`
- `Bot`

Behavior:

- human profile kinds create staff logins
- bot profile kind creates the bot identity and model configuration
- privilege overrides can grant or remove capabilities from the human defaults
- linked bot operators can be created separately for bot maintenance

## Recovery and Bootstrap

If the root admin password is lost, do not depend on old txt files.

Use the terminal account manager:

```bash
python tools/manage_ops_accounts.py list
python tools/manage_ops_accounts.py upsert-staff --username owner --display-name "Owner" --role admin --generate-password
python tools/manage_ops_accounts.py reset-password --username owner --generate-password
python tools/manage_ops_accounts.py ensure-colorstheforce --generate-password --allow-moderation
```

What this gives you:

- a named admin login for yourself
- named moderator or internal staff accounts for hired operators
- a linked `ColorsTheForce` bot-operator login
- a clean password-reset path without editing code or relying on fallback secrets

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

- OpenAI
- Google Vertex AI / Gemini
- Anthropic / Claude
- IBM watsonx.ai / Granite and partner-hosted models
- Amazon Bedrock
- NVIDIA NIM / Nemotron and partner models
- Mistral
- Meta Llama
- Cohere
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

## Bot Draft Queue

The preferred publish path for bots is now:

1. create a draft in `/ops#drafts`
2. choose the target surface:
   - `Announcement`
   - `Broadcast`
3. submit the draft for review
4. admin approves or rejects
5. admin publishes the approved draft live

Why this matters:

- bot operators can work quickly without getting silent sitewide publish power
- sitewide UI surfaces still require human approval
- bot output is auditable through the operator log
- the same workflow works for `ColorsTheForce` and future house bots

Surface notes:

- `Announcement` posts into the normal member announcement rail
- `Broadcast` publishes into the sitewide emergency UI system used for banners, tickers, blips, and modals

## Next Steps

1. Replace the shared root fallback with explicit admin accounts only.
2. Add richer bot draft surfaces like community summaries, WhitePages walkthrough drafts, and scheduled sponsor-ready posts.
3. Add per-role dashboard widgets and filtered audit views.
4. Add API-backed provider catalog refresh only if you decide it is worth the operational complexity.
