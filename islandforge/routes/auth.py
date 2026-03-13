"""
routes/auth.py — Epic Games OAuth2 authentication
  /auth/epic       Begin OAuth flow → redirects to Epic
  /auth/callback   Epic redirects back here with code
  /auth/logout     Clear session
"""

import os
import requests
from flask import Blueprint, redirect, request, session, url_for, render_template

auth_bp = Blueprint("auth", __name__)

EPIC_CLIENT_ID     = os.environ.get("EPIC_CLIENT_ID",     "xyza7891Qe7LilJtX5iFxwuLlazSBexH")
EPIC_CLIENT_SECRET = os.environ.get("EPIC_CLIENT_SECRET",  "")
EPIC_DEPLOYMENT_ID = os.environ.get("EPIC_DEPLOYMENT_ID",  "b4d6e13c2206494a88d6ea1783129dad")

EPIC_AUTH_URL      = "https://www.epicgames.com/id/authorize"
EPIC_TOKEN_URL     = "https://api.epicgames.dev/epic/oauth/v2/token"
EPIC_IDENTITY_URL  = "https://api.epicgames.dev/epic/id/v2/accounts"
REDIRECT_URI       = "https://triptokforge.org/auth/callback"

# ── NOTE ─────────────────────────────────────────────────────────
# Epic OAuth is PENDING brand review approval.
# When approved, swap EPIC_DEPLOYMENT_ID in systemd service to:
#   8c57f3550d41430f9cf2ff2be4695fbf
# ─────────────────────────────────────────────────────────────────


@auth_bp.route("/auth/epic")
def auth_epic():
    """Redirect user to Epic Games login."""
    params = {
        "client_id":     EPIC_CLIENT_ID,
        "response_type": "code",
        "scope":         "basic_profile",
        "redirect_uri":  REDIRECT_URI,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return redirect(f"{EPIC_AUTH_URL}?{query}")


@auth_bp.route("/auth/callback")
def auth_callback():
    """Handle Epic OAuth callback."""
    code  = request.args.get("code")
    error = request.args.get("error")

    if error or not code:
        return render_template("auth_error.html",
                               message="Epic login was cancelled or failed."), 400

    # Exchange code for token
    try:
        token_resp = requests.post(EPIC_TOKEN_URL, data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": REDIRECT_URI,
            "deployment_id": EPIC_DEPLOYMENT_ID,
        }, auth=(EPIC_CLIENT_ID, EPIC_CLIENT_SECRET), timeout=10)
        token_resp.raise_for_status()
        token_data = token_resp.json()
    except Exception as e:
        return render_template("auth_error.html", message=f"Token exchange failed: {e}"), 500

    access_token = token_data.get("access_token")
    account_id   = token_data.get("account_id")

    # Fetch display name
    display_name = account_id
    try:
        id_resp = requests.get(
            f"{EPIC_IDENTITY_URL}?accountId={account_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        id_resp.raise_for_status()
        accounts = id_resp.json()
        if accounts:
            display_name = accounts[0].get("displayName", account_id)
    except Exception:
        pass

    # Store in session
    session["epic_id"]      = account_id
    session["display_name"] = display_name
    session["access_token"] = access_token

    # Upsert member record
    from oracle_db import upsert_member
    upsert_member(epic_id=account_id, display_name=display_name)

    return redirect("/dashboard")


@auth_bp.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect("/home")
