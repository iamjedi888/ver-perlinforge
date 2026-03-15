# TriptokForge — Deploy Guide
## Oracle VM (Ubuntu 22.04, ARM Ampere)

**Server:** `ubuntu@129.80.222.152`  
**App dir:** `~/ver-perlinforge/islandforge/`  
**Domain:** `https://triptokforge.org`  
**Service:** `islandforge.service` (systemd + gunicorn, port 5000)

---

## Standard deploy (after pushing to GitHub)

```bash
ssh -i ~/ssh-key-2.key ubuntu@129.80.222.152

cd ~/ver-perlinforge
git pull origin main

pip install -r islandforge/requirements.txt --break-system-packages

sudo systemctl daemon-reload
sudo systemctl restart islandforge
sudo systemctl status islandforge
```

Check logs if it fails:
```bash
journalctl -u islandforge -n 50 --no-pager
```

---

## First-time setup (already done — reference only)

If the GitHub repository is private, configure a read-only deploy key on Oracle first and use the SSH remote instead of a public HTTPS clone.

```bash
# Clone
git clone git@github-triptokforge:iamjedi888/ver-perlinforge.git
cd ver-perlinforge/islandforge

# Install deps
pip install -r requirements.txt --break-system-packages

# Test manually
gunicorn -w 2 -b 0.0.0.0:5000 wsgi:application

# Install systemd service
sudo cp /etc/systemd/system/islandforge.service /etc/systemd/system/islandforge.service.bak
sudo nano /etc/systemd/system/islandforge.service
sudo systemctl enable islandforge
sudo systemctl start islandforge
```

---

## systemd service file

`/etc/systemd/system/islandforge.service`

```ini
[Unit]
Description=Island Forge
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ver-perlinforge/islandforge
ExecStart=/usr/local/bin/gunicorn -w 2 -b 0.0.0.0:5000 wsgi:application
Restart=always
RestartSec=5
EnvironmentFile=/etc/islandforge.env

[Install]
WantedBy=multi-user.target
```

> Keep secrets in a protected Oracle-only secret source such as OCI Vault or a root-only env file like `/etc/islandforge.env` with mode `600`, not inline in tracked files, screenshots, chat logs, or shell history.

Example variable names only:

```ini
APP_BASE_URL=https://triptokforge.org
EPIC_CLIENT_ID=YOUR_EPIC_CLIENT_ID_HERE
EPIC_CLIENT_SECRET=YOUR_EPIC_CLIENT_SECRET_HERE
EPIC_DEPLOYMENT_ID=YOUR_EPIC_DEPLOYMENT_ID_HERE
EPIC_REDIRECT_URI=https://triptokforge.org/auth/callback
FLASK_SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET
ADMIN_PASSWORD=REPLACE_WITH_A_LONG_RANDOM_PASSWORD
FORTNITE_API_KEY=OPTIONAL_FORTNITE_API_KEY
FORTNITE_DATA_ISLAND_CODE=OPTIONAL_PUBLISHED_ISLAND_CODE
```

Optional data surfaces:

- `FORTNITE_API_KEY` enables live Battle Royale stat lookups in the member hub.
- `FORTNITE_DATA_ISLAND_CODE` gives the site a published island code to anchor official Fortnite Data API views once your island is live.

### Epic approval hand-off

When Epic approves `triptokforge.org`, update the Oracle server with:

- `APP_BASE_URL=https://triptokforge.org`
- `EPIC_CLIENT_ID`
- `EPIC_CLIENT_SECRET`
- `EPIC_DEPLOYMENT_ID`
- `EPIC_REDIRECT_URI=https://triptokforge.org/auth/callback` if Epic requires the explicit override

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart islandforge
sudo systemctl status islandforge
```

---

## nginx config (reference)

`/etc/nginx/sites-available/triptokforge`

```nginx
server {
    listen 80;
    server_name triptokforge.org www.triptokforge.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name triptokforge.org www.triptokforge.org;

    ssl_certificate     /etc/letsencrypt/live/triptokforge.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/triptokforge.org/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

---

## Diagnosing 502 Bad Gateway

502 means nginx is up but gunicorn is not. Check in order:

```bash
# 1. Is gunicorn running?
sudo systemctl status islandforge

# 2. What crashed it?
journalctl -u islandforge -n 80 --no-pager

# 3. Try running manually to see the error directly
cd ~/ver-perlinforge/islandforge
gunicorn -w 1 -b 0.0.0.0:5000 wsgi:application

# 4. Common causes:
#    - Missing dependency   → pip install -r requirements.txt --break-system-packages
#    - Import error         → python3 -c "from server import app"
#    - Wrong gunicorn path  → which gunicorn
#    - Port conflict        → sudo lsof -i :5000
```

---

## Private repo note

If you switch the repository to private:

- keep Oracle on a read-only deploy key
- switch Oracle `origin` to the SSH remote
- continue deploying with `git pull origin main`

Reference: `templates/whitepages/GITHUB_PRIVATE_DEPLOY.md`

---

## SSL renewal

Cert expires 2026-06-09. Auto-renew via certbot:
```bash
sudo certbot renew --dry-run
```

---

## Repo structure

```
ver-perlinforge/
└── islandforge/
    ├── server.py              ← Flask app (all routes)
    ├── wsgi.py                ← gunicorn entry point
    ├── audio_to_heightmap.py  ← terrain generator
    ├── town_generator.py      ← town layout engine
    ├── index.html             ← Island Forge UI
    ├── requirements.txt
    ├── data/
    │   ├── announcements.json
    │   ├── jukebox.json
    │   ├── members.json
    │   └── spotlights.json
    ├── saved_audio/           ← uploaded audio (gitignored)
    └── outputs/               ← generated islands (gitignored)
```
