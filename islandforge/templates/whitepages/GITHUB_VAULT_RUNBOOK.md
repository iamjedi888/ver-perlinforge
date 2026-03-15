# GitHub Vault Runbook

## Goal

Turn years of GitHub work across multiple accounts into one organized knowledge vault that TriptokForge can reference without storing that full corpus in Oracle.

## Best Architecture

Use a separate repository as the vault index.

Recommended shape:

- `triptokforge-repo-vault` or `forge-knowledge-vault`
- generated static manifest JSON
- grouped markdown notes or generated HTML pages
- optional GitHub Pages publish for public-safe metadata only

Keep Oracle out of the heavy path.

Oracle should store:

- only small curated metadata if you need it in-app
- bookmarks or featured repo references
- no full repo archive or large docs corpus

GitHub should store:

- repo metadata index
- generated manifest
- screenshots and lightweight docs
- release assets if you want larger downloadable bundles

## Private vs Public

Important tradeoff:

- a **private** GitHub repo is good for your own internal archive
- a **public or sanitized** GitHub Pages/manifest repo is better if the site needs to fetch the data directly

If the site must show content without authenticating to GitHub, the manifest it consumes needs to be public-safe.

## Extraction Strategy

Mine both accounts:

- `colorstheforce`
- `iamjedi888`

Focus on reusable categories:

1. 3D / XR / graphics
2. UEFN / Verse / Fortnite
3. charts / telemetry / dashboards
4. broadcast / media / player / TV systems
5. platform tooling / admin / automation
6. AI / LLM / agent / moderation systems

Ignore low-signal repos:

- abandoned empty forks
- generic test repos
- duplicate tutorial scaffolds unless they contain a pattern worth saving

## What To Reuse For TriptokForge

Good likely value categories:

- Three.js or A-Frame repos for room, arena, and immersive dashboards
- dashboard or D3/chart repos for Bloomberg/JARVIS telemetry walls
- Flask/admin/tool repos for moderation and operator consoles
- media-player or playlist repos for channels and TV-guide systems
- AI agent or moderation repos for `ColorsTheForce` and future house bots
- UEFN/Fortnite/Verse repos for generator output, runbooks, and content systems

## Low-Cost Delivery Model

1. Run the repo-vault builder with a GitHub token.
2. Generate `repo_vault_manifest.json`.
3. Commit that manifest to the vault repo.
4. Publish docs or static JSON through GitHub Pages if the data is public-safe.
5. In TriptokForge, link out to the vault or fetch only the small static JSON.

That keeps Oracle out of the indexing and storage work.

## Local Builder

This repo includes:

- `config/repo_vault_sources.example.json`
- `tools/build_repo_vault.py`

Example:

```bash
export GITHUB_TOKEN=your_token
python tools/build_repo_vault.py --config config/repo_vault_sources.example.json
```

On Windows PowerShell:

```powershell
$env:GITHUB_TOKEN="your_token"
python tools\build_repo_vault.py --config config\repo_vault_sources.example.json
```

## Why Use A Token

GitHub's official REST API rate limits are much better when authenticated. GitHub documents the REST API and rate-limit model in the official docs:

- [List repositories for a user](https://docs.github.com/en/rest/repos/repos#list-repositories-for-a-user)
- [Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)

## GitHub-Native Hosting Options

- GitHub Pages for static docs or manifest hosting
- GitHub Releases for larger downloadable assets
- GitHub Actions to rebuild the manifest on a schedule

Official references:

- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- [Release assets](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

## Recommendation

Do not shove this archive into Oracle.

The correct split is:

- GitHub for the knowledge vault
- TriptokForge for curated pointers and featured integrations
- Oracle only for lightweight app metadata
