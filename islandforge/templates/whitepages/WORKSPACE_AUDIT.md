# TriptokForge Workspace Audit

Canonical live app:
- `Island Forge Repo/islandforge`

Useful docs retained:
- `README.md`
- `templates/whitepages/DEPLOY.md`
- `templates/whitepages/DEPLOY_WHEN_READY.md`
- `templates/whitepages/ORACLE_SETUP.md`
- `templates/whitepages/CHANNELS_DEPLOY_GUIDE.md`
- `templates/whitepages/ARENA_ROADMAP.md`
- `templates/whitepages/UEFN_IMPLEMENTATION_GUIDE.md`
- `templates/whitepages/ENHANCEMENT_ROADMAP.md`
- `templates/whitepages/COMPRESSION_INTEGRATION_GUIDE.md`

Absorbed into WhitePages HTML:
- old TV guide deploy notes
- old news deploy notes
- forge import guidance
- workspace cleanup guidance

Low-risk delete candidates inside the live repo:
- `patch_*.py`
- repo-root `patch_restore_full.py`
- repo-root `patch_room.py`
- `routes/forge.py.backup`
- `Island Forge 2/`
- `DEPLOY_TV.txt`
- `NEWS_DEPLOY.txt`
- `NEWS_DEPLOY_UPDATED.txt`
- `STRUCTURE.md`
- `text.txt`

Sibling workspace archive candidates not auto-removed:
- `PerlinPY/`
- root-level `Island Forge 2/`
- `files/`
- `PerlinPY2/`
- `ProjectPHaser/`
- root-level `templates/`
- `verse dump/`

Security note:
- historical scratch notes contained inline secret values
- keep secrets only in protected server env files, never in tracked notes
- rotate any secret that was ever pasted into tracked files or chat history
