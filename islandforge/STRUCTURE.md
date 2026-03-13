# TriptokForge — Project Structure

```
islandforge/
│
├── server.py               ← Flask app init + Blueprint registration (lean)
├── wsgi.py                 ← Gunicorn entry point
├── oracle_db.py            ← Oracle DB + OCI Object Storage layer
├── channels_page.py        ← Channels page HTML builder (drop-in module)
├── requirements.txt
│
├── routes/                 ← One Blueprint file per section
│   ├── __init__.py
│   ├── platform.py         ← /  /home  /forge  /gallery  /feed  /community  /dashboard  /admin  /health
│   ├── channels.py         ← /channels  /api/suggest_channel
│   ├── auth.py             ← /auth/epic  /auth/callback  /auth/logout
│   ├── api.py              ← /api/members  /api/post  /api/like/<id>
│   └── whitepages.py       ← /whitepages  /whitepages/verse  /whitepages/api  /whitepages/deploy  /whitepages/tarkov
│
├── templates/              ← All HTML templates (Flask render_template)
│   ├── _base.html          ← Base layout with shared head/nav/footer
│   ├── home.html
│   ├── forge.html
│   ├── gallery.html
│   ├── feed.html
│   ├── community.html
│   ├── dashboard.html
│   ├── admin.html
│   ├── auth_error.html
│   ├── 404.html
│   └── whitepages/         ← Docs articles — one file per page
│       ├── index.html      ← /whitepages landing + TOC
│       ├── verse.html      ← /whitepages/verse
│       ├── api.html        ← /whitepages/api
│       ├── deploy.html     ← /whitepages/deploy
│       └── tarkov.html     ← /whitepages/tarkov
│
├── static/                 ← All static assets (served by Flask / nginx)
│   ├── favicon.svg
│   ├── og.png              ← 1200×630 social share image
│   ├── icon-192.png        ← PWA icon
│   ├── icon-512.png        ← PWA icon
│   └── apple-touch-icon.png
│
├── tools/                  ← Utility modules imported by routes
│   ├── audio_to_heightmap.py
│   ├── file_compressor.py
│   └── town_generator.py
│
└── scripts/                ← One-off scripts (run manually, never imported)
    ├── seed_channels.py
    ├── seed_feed.py
    └── setup_compression.sh
```

## Adding a new whitepages article

1. Create `templates/whitepages/<slug>.html`
2. Add route in `routes/whitepages.py`:
   ```python
   @whitepages_bp.route("/<slug>")
   def my_article():
       return render_template("whitepages/<slug>.html", **_ctx(active_page="<slug>"))
   ```
3. Add sidebar link — update the sidebar nav in your base whitepages template
4. `git add`, `git commit`, deploy

## Deploy flow

```bash
# Local
git add -A && git commit -m "your message" && git push origin master

# Oracle VM
cd ~/ver-perlinforge && git pull origin master
sudo systemctl restart islandforge
curl http://127.0.0.1:5000/health
```

## Environment variables (in systemd service file)

| Variable            | Description                        |
|---------------------|------------------------------------|
| EPIC_CLIENT_ID      | Epic OAuth app client ID           |
| EPIC_CLIENT_SECRET  | Epic OAuth app secret              |
| EPIC_DEPLOYMENT_ID  | Epic deployment ID (swap on approval) |
| FLASK_SECRET_KEY    | Flask session key                  |
| ADMIN_PASSWORD      | Admin panel password               |
| ORACLE_DSN          | Oracle DB DSN (tiktokdb_high)      |
| ORACLE_USER         | Oracle DB user                     |
| ORACLE_PASSWORD     | Oracle DB password                 |
| ORACLE_WALLET       | Path to Oracle wallet dir          |
| OCI_NAMESPACE       | OCI object storage namespace       |
| OCI_BUCKET          | OCI bucket name (triptokforge)     |
| OCI_REGION          | OCI region (us-ashburn-1)          |
| OCI_CONFIG_FILE     | Path to OCI config (~/.oci/config) |
