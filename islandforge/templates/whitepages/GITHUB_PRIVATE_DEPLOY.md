# GitHub Private Deploy Runbook

## Goal

Keep the TriptokForge repository private on GitHub while still allowing the Oracle VM to deploy from `main`.

## Recommended model

Use:

- one private GitHub repository
- one read-only deploy key on the Oracle VM
- one SSH remote on Oracle for pulls

Do not use:

- a personal access token pasted into shell history
- a shared machine user account
- a public repository for convenience

## Why this model

It keeps the code private from everyone except the GitHub accounts you explicitly grant access to, while the Oracle server only gets read access to that single repository.

## GitHub side

1. Open the repository on GitHub.
2. Go to `Settings` -> `General`.
3. Change repository visibility to `Private`.
4. Go to `Settings` -> `Deploy keys`.
5. Add a new deploy key.
6. Paste the Oracle VM public key.
7. Leave write access off unless you explicitly need server-side pushes.

## Oracle side

Generate a deploy key on Oracle:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/triptokforge_deploy -C "oracle-triptokforge-deploy"
cat ~/.ssh/triptokforge_deploy.pub
```

Copy the public key into the GitHub deploy key form.

Lock down permissions:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/triptokforge_deploy
chmod 644 ~/.ssh/triptokforge_deploy.pub
```

Add GitHub to known hosts:

```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
chmod 644 ~/.ssh/known_hosts
```

Point the Oracle clone at the SSH remote:

```bash
cd ~/ver-perlinforge
git remote set-url origin git@github.com:iamjedi888/ver-perlinforge.git
GIT_SSH_COMMAND='ssh -i ~/.ssh/triptokforge_deploy' git fetch origin
```

To avoid retyping the SSH command, use `~/.ssh/config`:

```sshconfig
Host github-triptokforge
  HostName github.com
  User git
  IdentityFile ~/.ssh/triptokforge_deploy
  IdentitiesOnly yes
```

Then set:

```bash
cd ~/ver-perlinforge
git remote set-url origin git@github-triptokforge:iamjedi888/ver-perlinforge.git
git fetch origin
```

## Deploy flow after privatizing

```bash
cd ~/ver-perlinforge/islandforge
git pull origin main
sudo systemctl daemon-reload
sudo systemctl restart islandforge
sudo systemctl status islandforge --no-pager
curl http://127.0.0.1:5000/health
```

## Security notes

- Keep the deploy key read-only.
- Do not reuse your personal SSH key.
- Do not store GitHub credentials in tracked files.
- If the Oracle VM is ever replaced, revoke the old deploy key immediately.
- If you later split repos, give each repo its own deploy key.

## Suggested repo split later

- `ver-perlinforge` -> live site and deployment code
- `triptokforge-bot-config` -> bot prompts, persona packs, moderation rules
- `triptokforge-ops` -> internal scripts, migration notes, operational tooling

That keeps sensitive operational logic separate without changing the public site architecture.
