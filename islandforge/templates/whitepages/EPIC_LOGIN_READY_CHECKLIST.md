# Epic Login Ready Checklist

Staff-only checklist for deciding whether `triptokforge.org` is truly ready for public Epic login.

## The website login flow uses only these values

- `APP_BASE_URL`
- `EPIC_CLIENT_ID`
- `EPIC_CLIENT_SECRET`
- `EPIC_DEPLOYMENT_ID`
- `EPIC_REDIRECT_URI`

For the current Flask site, those are the only Epic-side values that matter to complete the web login flow.

## Not part of the current Flask login checklist

- `PRODUCT_ID`
- `APPLICATION_ID`
- `SANDBOX_ID`

Those may matter later for broader EOS SDK or game-service work, but they are not what makes the current website login succeed.

## Ready for production login when all of these are true

- The Epic app/client being used is the one approved for the public site.
- The deployment on Oracle matches the approved public environment.
- `EPIC_REDIRECT_URI` exactly matches the redirect URI registered with Epic.
- `APP_BASE_URL` matches the public domain.
- `/auth/epic` redirects to Epic successfully.
- Epic returns to the approved callback path successfully.
- The site lands on `/dashboard` after login.
- `/auth/logout` returns the user to `/home`.
- No placeholder values remain in the live Oracle config.
- No Epic secrets are present in WhitePages, Git, screenshots, or chat logs.

## Placeholder-only config examples

### EnvironmentFile pattern

```ini
APP_BASE_URL=https://triptokforge.org
EPIC_CLIENT_ID=YOUR_APPROVED_CLIENT_ID
EPIC_CLIENT_SECRET=YOUR_APPROVED_CLIENT_SECRET
EPIC_DEPLOYMENT_ID=YOUR_APPROVED_DEPLOYMENT_ID
EPIC_REDIRECT_URI=https://triptokforge.org/auth/callback
FLASK_SECRET_KEY=YOUR_LONG_RANDOM_FLASK_SECRET
ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD_HERE
```

### Inline systemd pattern

```ini
Environment="APP_BASE_URL=https://triptokforge.org"
Environment="EPIC_CLIENT_ID=YOUR_APPROVED_CLIENT_ID"
Environment="EPIC_CLIENT_SECRET=YOUR_APPROVED_CLIENT_SECRET"
Environment="EPIC_DEPLOYMENT_ID=YOUR_APPROVED_DEPLOYMENT_ID"
Environment="EPIC_REDIRECT_URI=https://triptokforge.org/auth/callback"
```

## Fast readiness test

1. Check the health route.
2. Open `/auth/epic`.
3. Complete login.
4. Confirm callback success.
5. Confirm `/dashboard`.
6. Confirm logout.

## Failure hints

- Redirect mismatch:
  Epic app config and Oracle callback do not exactly match.
- Login works only for org/test users:
  Epic-side approval or review is still the remaining gate.
- Token exchange fails:
  wrong client secret, wrong deployment, or stale live values.

## Operational rule

Do not build a website form for editing Epic secrets. Keep real values on Oracle only.
