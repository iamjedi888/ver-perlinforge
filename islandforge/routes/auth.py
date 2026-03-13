from flask import Blueprint, request, redirect, session
import os, requests as http_requests

auth_bp = Blueprint("auth", __name__)

EPIC_CLIENT_ID     = os.environ.get("EPIC_CLIENT_ID", "xyza7891Qe7LilJtX5iFxwuLlazSBexH")
EPIC_CLIENT_SECRET = os.environ.get("EPIC_CLIENT_SECRET", "PRh3NmCBzgKcGFPEwSJVdm/fxa2POqbJz85Kr82+IWY")
EPIC_DEPLOYMENT_ID = os.environ.get("EPIC_DEPLOYMENT_ID", "b4d6e13c2206494a88d6ea1783129dad")
REDIRECT_URI       = "https://triptokforge.org/auth/callback"

@auth_bp.route("/auth/epic")
def auth_epic():
    params = f"client_id={EPIC_CLIENT_ID}&response_type=code&scope=basic_profile&redirect_uri={REDIRECT_URI}"
    return redirect(f"https://www.epicgames.com/id/authorize?{params}")

@auth_bp.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return "Epic login failed.", 400
    try:
        tok = http_requests.post(
            "https://api.epicgames.dev/epic/oauth/v2/token",
            data={"grant_type":"authorization_code","code":code,"redirect_uri":REDIRECT_URI,"deployment_id":EPIC_DEPLOYMENT_ID},
            auth=(EPIC_CLIENT_ID, EPIC_CLIENT_SECRET), timeout=10)
        tok.raise_for_status()
        td = tok.json()
    except Exception as e:
        return f"Token exchange failed: {e}", 500
    session["epic_id"]      = td.get("account_id")
    session["display_name"] = td.get("account_id")
    session["access_token"] = td.get("access_token")
    from oracle_db import upsert_member
    upsert_member(epic_id=session["epic_id"], display_name=session["display_name"])
    return redirect("/dashboard")

@auth_bp.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect("/home")
