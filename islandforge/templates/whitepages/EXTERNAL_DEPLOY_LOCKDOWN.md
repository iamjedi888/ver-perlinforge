# External Deploy Lockdown

## Goal

Keep `Oracle + systemd + nginx` as the only production deploy path for TriptokForge.

## Current repo state

As of 2026-03-15, the live repository does not contain:

- `vercel.json`
- `wrangler.toml`
- `.github/workflows/` deploy automation for Vercel or Cloudflare
- Cloudflare Pages or Workers config files

That means any Vercel or Cloudflare deployment still happening is being triggered by an external Git integration, not by tracked repo config.

## Lockdown checklist

1. In Vercel, remove or disconnect the project that is linked to this GitHub repo.
2. In Cloudflare Pages or Workers, remove Git integration for this repo or delete the linked project.
3. In GitHub, reduce repository access for installed apps so only the repo and deploy path you actually want remain connected.
4. Keep Oracle as the only deploy target:
   - `git pull origin main`
   - `sudo systemctl restart islandforge`
5. Do not add Vercel or Cloudflare config files back into this repo unless you intentionally change deployment strategy later.

## Repo hardening

The repo now ignores common local deploy-platform folders:

- `.vercel/`
- `.wrangler/`
- `.cloudflare/`

This does not disable those platforms by itself, but it prevents local platform metadata from being accidentally committed and reintroducing confusion later.

The Flask entrypoint now also refuses to boot automatically when typical Vercel or Cloudflare Pages runtime variables are present, unless you explicitly set:

- `ALLOW_NON_ORACLE_DEPLOY=1`

## Official references

- Vercel Git and repository controls:
  `https://vercel.com/docs/deployments/git`
- Cloudflare Pages GitHub integration:
  `https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/`
- GitHub app repository access controls:
  `https://docs.github.com/en/apps/using-github-apps/reviewing-and-modifying-installed-github-app-permissions`

## TriptokForge rule

Primary production authority is:

- Oracle VM
- Oracle secrets
- Oracle systemd service
- Oracle health check

Vercel and Cloudflare should be treated as disconnected unless you intentionally create a separate future surface for them.
