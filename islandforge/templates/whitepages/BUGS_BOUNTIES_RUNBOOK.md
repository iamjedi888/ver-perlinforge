# Bugs + Bounties Runbook

Internal TriptokForge reference for bug intake, exploit triage, reward decisions, and future public disclosure policy.

## Current recommendation

Do not launch a public bug bounty page yet.

The correct first step is a staff-only runbook:

- intake path
- severity ladder
- owner assignment
- patch/validate flow
- reward decision model
- out-of-scope list

Once that is stable, a public responsible-disclosure page can be opened with a smaller surface area.

## Why this matters

TriptokForge now has:

- Epic-authenticated member flows
- staff/admin logins
- bot operators
- sitewide broadcasts
- Oracle-backed member and content records
- generated Forge artifacts

That means exploit reports should no longer be handled ad hoc in DMs or chat logs. A bug/bounty lane keeps response disciplined and auditable.

## Severity model

### S1 - Critical

Examples:

- admin or ops auth bypass
- staff privilege escalation to admin
- secret leakage
- direct Oracle or OCI data exposure
- destructive bot or broadcast takeover

Action:

- freeze the affected surface
- rotate exposed secrets
- preserve logs
- patch before discussing reward handling

### S2 - High

Examples:

- moderator or bot-operator privilege escalation
- private member data exposure
- abuse of unpublished content controls
- cross-account access to generated Forge outputs

Action:

- hotfix quickly
- confirm blast radius
- add regression coverage
- then review reward eligibility

### S3 - Medium

Examples:

- queue/workflow bypass
- channel moderation loopholes
- WhitePages gating mistakes
- incorrect access to non-sensitive content

Action:

- backlog as high-priority product bug
- patch on the next cycle
- document exact repro

### S4 - Low

Examples:

- layout defects
- copy drift
- weak UX warnings
- visual-only state issues

Action:

- track normally unless it blocks an important user journey

## Reward philosophy

TriptokForge does not need a rigid public cash table on day one.

Better starting model:

- discretionary reward
- store credit / platform recognition / custom thanks
- manual bounty for strong good-faith reports

Only formalize tiers later if a public program is launched.

## Out of scope

Do not encourage or reward testing against systems TriptokForge does not own.

Examples out of scope:

- Epic account systems
- EOS internals
- Fortnite services
- Oracle control-plane services
- GitHub platform bugs
- Cloud or vendor platform issues outside TriptokForge code

Also out of scope:

- phishing or social engineering
- denial-of-service
- spam or mass automation
- unnecessary retention of accessed data
- public disclosure before fix/approval

## Intake workflow

1. Create an internal case with date, reporter, surface, severity, and repro.
2. Assign owner: admin, moderation, infra, or content operations.
3. Reproduce safely.
4. Patch and validate.
5. Decide reward/recognition outcome.
6. Record a short postmortem if the issue touched auth, data, bots, or public trust.

## Public program later

If TriptokForge later opens a public security or bounty page, include:

- exact contact method
- allowed testing scope
- prohibited activity
- safe-harbor statement
- reward disclaimer
- response expectations

Until then, keep the full runbook staff-only.
