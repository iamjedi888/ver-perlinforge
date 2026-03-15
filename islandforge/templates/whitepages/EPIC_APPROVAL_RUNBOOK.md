# Epic Approval Runbook

## Goal

When Epic approves the production domain, switch the site from pending OAuth state to a live Epic login flow on `https://triptokforge.org`.

## Current code path

The site already reads Epic OAuth from environment variables:

- `APP_BASE_URL`
- `EPIC_CLIENT_ID`
- `EPIC_CLIENT_SECRET`
- `EPIC_DEPLOYMENT_ID`
- `EPIC_REDIRECT_URI`

Relevant code:

- `routes/epic_auth_config.py`
- `routes/auth.py`

## Exact production target

- Public base URL: `https://triptokforge.org`
- Callback URL: `https://triptokforge.org/auth/callback`
- Login entry: `https://triptokforge.org/auth/epic`
- Logout entry: `https://triptokforge.org/auth/logout`

## Approval-day checklist

1. Confirm the approved Epic application uses the production domain.
2. Confirm the redirect URI registered with Epic matches:
   `https://triptokforge.org/auth/callback`
3. Put the approved values on Oracle.
4. Restart `islandforge`.
5. Test the full login and logout flow.
6. Verify the member session lands on `/dashboard`.

## Oracle env pattern

Recommended:

```bash
sudo install -m 600 /dev/null /etc/islandforge.env
sudo nano /etc/islandforge.env
```

Add:

```ini
APP_BASE_URL=https://triptokforge.org
EPIC_CLIENT_ID=YOUR_APPROVED_CLIENT_ID
EPIC_CLIENT_SECRET=YOUR_APPROVED_CLIENT_SECRET
EPIC_DEPLOYMENT_ID=YOUR_APPROVED_DEPLOYMENT_ID
EPIC_REDIRECT_URI=https://triptokforge.org/auth/callback
FLASK_SECRET_KEY=REPLACE_WITH_LONG_RANDOM_VALUE
ADMIN_PASSWORD=REPLACE_WITH_LONG_RANDOM_VALUE
```

Then point systemd at that file:

```ini
EnvironmentFile=/etc/islandforge.env
```

Restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart islandforge
sudo systemctl status islandforge --no-pager
curl http://127.0.0.1:5000/health
```

## Browser test

1. Open `/auth/epic`
2. Complete Epic login
3. Confirm callback lands at `/dashboard`
4. Confirm session values are present:
   - display name
   - Epic account id
   - dashboard nav
5. Run logout and confirm it returns to `/home`

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

## Approval-day command set

```bash
cd ~/ver-perlinforge/islandforge
git pull origin main
sudo systemctl daemon-reload
sudo systemctl restart islandforge
sudo systemctl status islandforge --no-pager
curl http://127.0.0.1:5000/health
```
