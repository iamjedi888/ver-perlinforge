# Epic Approval Runbook

## Goal

When Epic approves the production domain, switch the site from pending OAuth state to a live Epic login flow on `https://triptokforge.org`.

## What the current website actually uses

The site already reads Epic OAuth from environment variables:

- `APP_BASE_URL`
- `EPIC_CLIENT_ID`
- `EPIC_CLIENT_SECRET`
- `EPIC_DEPLOYMENT_ID`
- `EPIC_REDIRECT_URI`

Relevant code:

- `routes/epic_auth_config.py`
- `routes/auth.py`

For the current Flask website login flow, this is the active credential set. The site does **not** currently need product-wide SDK identifiers beyond what is required to complete Epic Account Services login and token exchange.

## Values that are useful reference, but not currently consumed by the Flask login flow

- `PRODUCT_ID`
- `APPLICATION_ID`
- `SANDBOX_ID`

Keep those recorded in your private Epic portal notes, but do not treat them as part of the current website login checklist unless the site later expands into deeper EOS SDK or game-service integration.

The app accepts both callback routes:

- `https://triptokforge.org/auth/callback`
- `https://triptokforge.org/auth/epic/callback`

The important rule is that the value configured in Epic must exactly match `EPIC_REDIRECT_URI` on Oracle.

## Exact production target

- Public base URL: `https://triptokforge.org`
- Canonical callback URL: `https://triptokforge.org/auth/callback`
- Alternate accepted callback URL: `https://triptokforge.org/auth/epic/callback`
- Login entry: `https://triptokforge.org/auth/epic`
- Logout entry: `https://triptokforge.org/auth/logout`

## Approval-day checklist

1. Confirm the approved Epic application uses the production domain.
2. Confirm the redirect URI registered with Epic exactly matches the Oracle env value for `EPIC_REDIRECT_URI`.
3. Prefer the canonical callback:
   `https://triptokforge.org/auth/callback`
4. If Epic approval was already processed against:
   `https://triptokforge.org/auth/epic/callback`
   keep that value on Oracle until Epic changes it.
5. Confirm the approved deployment is the one you actually want to run on the public site.
6. Put the approved values on Oracle.
7. Restart `islandforge`.
8. Test the full login and logout flow.
9. Verify the member session lands on `/dashboard`.
10. Verify logout returns cleanly to `/home`.

## Oracle config pattern

The current Oracle server may be using either:

1. inline `Environment="..."` lines inside the `islandforge.service` unit
2. an `EnvironmentFile=/path/to/file`

Use one pattern only. Do not mix both casually.

### Placeholder-only variable set

Add only the real approved values on Oracle. Do not place them in WhitePages, tracked files, screenshots, or chat logs.

Variable names only:

```ini
APP_BASE_URL=https://triptokforge.org
EPIC_CLIENT_ID=YOUR_APPROVED_CLIENT_ID
EPIC_CLIENT_SECRET=YOUR_APPROVED_CLIENT_SECRET
EPIC_DEPLOYMENT_ID=YOUR_APPROVED_DEPLOYMENT_ID
EPIC_REDIRECT_URI=https://triptokforge.org/auth/callback
FLASK_SECRET_KEY=REPLACE_WITH_LONG_RANDOM_VALUE
ADMIN_PASSWORD=REPLACE_WITH_LONG_RANDOM_VALUE
```

### If you use an EnvironmentFile

```bash
sudo install -m 600 /dev/null /etc/islandforge.env
sudo nano /etc/islandforge.env
```

Then set the service to read it:

```ini
EnvironmentFile=/etc/islandforge.env
```

### If you keep inline systemd Environment lines

Keep only placeholder-style examples in docs and write the real values directly on Oracle:

```ini
Environment="APP_BASE_URL=https://triptokforge.org"
Environment="EPIC_CLIENT_ID=YOUR_APPROVED_CLIENT_ID"
Environment="EPIC_CLIENT_SECRET=YOUR_APPROVED_CLIENT_SECRET"
Environment="EPIC_DEPLOYMENT_ID=YOUR_APPROVED_DEPLOYMENT_ID"
Environment="EPIC_REDIRECT_URI=https://triptokforge.org/auth/callback"
```

### Restart after any change

```bash
sudo systemctl daemon-reload
sudo systemctl restart islandforge
sudo systemctl status islandforge --no-pager
curl http://127.0.0.1:5000/health
```

## Browser test

1. Open `/auth/epic`
2. Complete Epic login
3. Confirm the callback path used by Epic matches `EPIC_REDIRECT_URI`
4. Confirm the flow lands at `/dashboard`
5. Confirm session values are present:
   - display name
   - Epic account id
   - dashboard nav
6. Run logout and confirm it returns to `/home`

## Quick decision rule

- If `/auth/epic` redirects to Epic already, the site-side flow is wired.
- If public users still are not supposed to log in yet, the remaining gate is on the Epic approval / app-review / deployment side, not the Flask route itself.
- If you switch from `Dev` or `Stage` to `Live`, update the approved deployment value on Oracle before expecting production behavior.

## Epic mark handling

If you place Epic marks on the website after approval:

- use the official shield files from `files/photos/epicgames/epicgames-logos/`
- keep them on factual Epic-related surfaces only
- do not let Epic marks become the main TriptokForge brand
- re-check the current Epic brand portal before any public rollout

Reference: `templates/whitepages/EPIC_BRANDING.md`

## Failure modes

### Redirect mismatch

Symptoms:

- Epic login page rejects callback
- callback returns with no code
- token exchange fails

Fix:

- make the registered Epic redirect URI exactly match `EPIC_REDIRECT_URI`
- keep `APP_BASE_URL` aligned with the public domain

### Missing deployment ID

Symptoms:

- token exchange fails even with valid client ID and secret

Fix:

- verify `EPIC_DEPLOYMENT_ID` from the approved setup is present on Oracle

### Wrong production domain

Symptoms:

- approval exists but login still behaves like pending setup

Fix:

- confirm Epic approved `triptokforge.org`, not a different staging host
- confirm no stale values remain in systemd or shell env

## Compliance notes

- Only use the scopes and identity surfaces approved by Epic.
- Keep site-side features within Epic and Fortnite rules.
- Do not imply access to private cross-game player save data just because Epic login succeeded.

## Portal note

Treat the website login app as an Epic Account Services / Developer Portal item, not a Fortnite Creator Portal publishing item.

Reference: `templates/whitepages/EPIC_CONTACT_MATRIX.md`

## Approval-day command set

```bash
cd ~/ver-perlinforge/islandforge
git pull origin main
sudo systemctl daemon-reload
sudo systemctl restart islandforge
sudo systemctl status islandforge --no-pager
curl http://127.0.0.1:5000/health
```
