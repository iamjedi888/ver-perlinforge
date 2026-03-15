from secrets import token_urlsafe
from urllib.parse import urlencode

import requests as http_requests
from flask import Blueprint, current_app, redirect, render_template, request, session

from routes.epic_auth_config import (
    epic_auth_ready,
    epic_missing_config,
    get_epic_auth_config,
)

auth_bp = Blueprint("auth", __name__)


def _render_auth_status(message: str, status_code: int = 503, title: str = "Epic Login Not Ready"):
    config = get_epic_auth_config()
    return (
        render_template(
            "auth_status.html",
            title=title,
            message=message,
            missing_vars=epic_missing_config(config),
            redirect_uri=config["redirect_uri"],
            base_url=config["base_url"],
        ),
        status_code,
    )


@auth_bp.route("/auth/epic")
def auth_epic():
    config = get_epic_auth_config()
    if not epic_auth_ready(config):
        return _render_auth_status(
            "Epic OAuth is still waiting on approved keys or deployment settings. "
            "Set the EPIC_* variables on the Oracle server and restart the service once Epic approves the domain."
        )

    state = token_urlsafe(24)
    session["epic_oauth_state"] = state
    params = urlencode(
        {
            "client_id": config["client_id"],
            "response_type": "code",
            "scope": "basic_profile",
            "redirect_uri": config["redirect_uri"],
            "state": state,
        }
    )
    return redirect(f"{config['auth_url']}?{params}")


@auth_bp.route("/auth/callback")
@auth_bp.route("/auth/epic/callback")
def auth_callback():
    config = get_epic_auth_config()
    if not epic_auth_ready(config):
        return _render_auth_status(
            "Epic OAuth callback was reached before the app was fully configured. "
            "Add the approved EPIC_* values on the server first."
        )

    state = request.args.get("state", "")
    expected_state = session.pop("epic_oauth_state", "")
    if not state or not expected_state or state != expected_state:
        return _render_auth_status(
            "Epic login state validation failed. Start the login flow again from the site.",
            status_code=400,
            title="Epic Login Failed",
        )

    code = request.args.get("code")
    if not code:
        return _render_auth_status(
            "Epic did not return an authorization code.",
            status_code=400,
            title="Epic Login Failed",
        )

    try:
        tok = http_requests.post(
            config["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config["redirect_uri"],
                "deployment_id": config["deployment_id"],
            },
            auth=(config["client_id"], config["client_secret"]),
            timeout=10,
        )
        tok.raise_for_status()
        token_data = tok.json()
    except http_requests.RequestException:
        current_app.logger.exception("Epic token exchange failed")
        return _render_auth_status(
            "Epic token exchange failed. Double-check the approved client ID, client secret, deployment ID, "
            "and redirect URI on the Oracle server.",
            status_code=502,
            title="Epic Login Failed",
        )

    epic_id = token_data.get("account_id") or token_data.get("sub")
    access_token = token_data.get("access_token", "")
    display_name = (
        token_data.get("display_name")
        or token_data.get("displayName")
        or epic_id
        or "Epic Player"
    )
    if not epic_id or not access_token:
        return _render_auth_status(
            "Epic returned an incomplete token response. Confirm the deployment is approved for this domain.",
            status_code=502,
            title="Epic Login Failed",
        )

    session["epic_id"] = epic_id
    session["epic_account_id"] = epic_id
    session["display_name"] = display_name
    session["access_token"] = access_token
    session["epic_access_token"] = access_token
    session["user"] = {
        "account_id": epic_id,
        "display_name": display_name,
        "skin_img": session.get("skin_img", ""),
        "skin_name": session.get("skin_name", "Default"),
    }

    from oracle_db import upsert_member

    upsert_member(epic_id=epic_id, display_name=display_name)
    return redirect("/dashboard")


@auth_bp.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect("/home")
