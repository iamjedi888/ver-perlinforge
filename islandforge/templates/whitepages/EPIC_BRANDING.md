# Epic Branding

## Purpose

Document how TriptokForge should handle Epic Games marks and the local Epic logo asset pack after domain approval and official login integration.

This is a small part of the overall platform, but it is a large part of how the project got here and how the site should present that relationship correctly.

## Canonical sources

- Epic brand portal:
  `https://brand.epicgames.com/document/373#/-/logo/downloads-1`
- Epic fan content policy:
  `https://legal.epicgames.com/en-US/epicgames/fan-art-policy`

Before publishing any new Epic-mark usage, compare the live brand portal guidance against the local pack in case Epic updates the approved files or rules.

## Local asset pack in this repo

Path:

`files/photos/epicgames/epicgames-logos/`

Current files:

- `EG-Shield-2023-logo-Black.eps`
- `EG-Shield-2023-logo-Black.pdf`
- `EG-Shield-2023-logo-Black.png`
- `EG-Shield-2023-logo-Black.svg`
- `EG-Shield-2023-logo-White.eps`
- `EG-Shield-2023-logo-White.pdf`
- `EG-Shield-2023-logo-White.png`
- `EG-Shield-2023-logo-White.svg`

Preferred web-use files:

- `EG-Shield-2023-logo-Black.svg`
- `EG-Shield-2023-logo-White.svg`

## Allowed TriptokForge use

Use Epic marks only in factual, narrow contexts such as:

- Epic login and identity connection explanations
- WhitePages compliance and approval documentation
- official Epic-approval handoff notes
- clearly labeled partner, platform, or compatibility references once approval exists

Do not use Epic marks as:

- the TriptokForge primary brand
- the site favicon
- a replacement for the TriptokForge lockup
- decorative hero art unrelated to factual Epic connection
- any visual treatment that implies Epic built, owns, or endorses TriptokForge

## Handling rules

1. Start from Epic's official downloaded asset files only.
2. Do not redraw, distort, crop into a new shape, or remix Epic's shield into TriptokForge branding.
3. Keep Epic marks visually separate from the TriptokForge logo.
4. Use black or white source assets according to contrast needs rather than recoloring the mark into custom brand colors.
5. Add Epic's required fan-content disclaimer anywhere the usage falls under fan-content presentation rather than direct official approval language.
6. Re-check the brand portal and approval terms before each new public use.

## Site implementation guidance

When Epic approval is live, preferred placement is:

- auth/login guidance
- WhitePages branding/compliance section
- approval-day runbook
- clearly labeled small integration badges near Epic-specific settings

Avoid placing the Epic mark in:

- the persistent site lockup
- major nav branding
- footer identity lockups
- section titles that could imply co-brand ownership

## Approval-day checklist

1. Confirm the domain approval is complete.
2. Confirm the auth flow works on `https://triptokforge.org/auth/epic`.
3. Use only the official Epic shield assets from the local pack or a freshly verified portal download.
4. Place the logo only on factual Epic-related surfaces.
5. Confirm the required disclaimer or attribution treatment is present where needed.
6. Do a final manual review for implication risk:
   - no false endorsement
   - no fake partnership framing
   - no Epic mark becoming the main site identity

## TriptokForge rule

Epic is a platform and approval path we respect.

TriptokForge remains the primary identity.
