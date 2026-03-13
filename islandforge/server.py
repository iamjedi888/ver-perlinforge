"""
server.py — TriptokForge Platform v2.0
=======================================
Island Forge generator + full platform (homepage, Epic OAuth, member dashboard)

ENDPOINTS:
  GET  /              → homepage (redirect to /home)
  GET  /home          → platform homepage
  GET  /forge         → Island Forge UI
  GET  /dashboard     → member dashboard (login required)
  GET  /auth/epic     → start Epic OAuth
  GET  /auth/callback → Epic OAuth callback
  GET  /auth/logout   → logout
  GET  /privacy       → privacy policy
  POST /generate      → generate island
  POST /upload_audio  → upload audio
  GET  /audio/list    → list saved audio
  POST /audio/select  → select saved audio
  DELETE /audio/<fn>  → delete audio
  GET  /download/heightmap
  GET  /download/layout
  GET  /download/preview
  GET  /random_seed
  GET  /api/stats     → Fortnite stats by username
  GET  /api/cosmetics → Fortnite cosmetics list
  POST /api/set_skin  → save skin selection to session
"""

import io, base64, json, os, sys, traceback, secrets
import urllib.parse, urllib.request
from functools import wraps

import numpy as np
from flask import Flask, request, jsonify, send_file, session, redirect

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Oracle DB + OCI Object Storage (graceful fallback if not configured) ──────
try:
    from oracle_db import (
        upsert_member, update_member_skin, get_all_members,
        save_audio_track, get_audio_tracks, delete_audio_track,
        save_island, get_recent_islands,
        get_announcements, post_announcement,
        oci_upload, oci_upload_bytes, oci_delete,
        audio_object_name, preview_object_name,
        heightmap_object_name, layout_object_name,
        init_schema, status as db_status,
    )
    DB_MODULE = True
except ImportError:
    DB_MODULE = False
    def upsert_member(*a, **k): return True
    def update_member_skin(*a, **k): return True
    def get_all_members(): return []
    def save_audio_track(*a, **k): return True
    def get_audio_tracks(**k): return []
    def delete_audio_track(*a): return True
    def save_island(*a, **k): return True
    def get_recent_islands(limit=20): return []
    def get_announcements(): return []
    def post_announcement(*a, **k): return True
    def oci_upload(*a, **k): return ""
    def oci_upload_bytes(*a, **k): return ""
    def oci_delete(*a): return False
    def audio_object_name(fn): return f"audio/{fn}"
    def preview_object_name(seed): return f"previews/island_{seed}_preview.png"
    def heightmap_object_name(seed): return f"heightmaps/island_{seed}_heightmap.png"
    def layout_object_name(seed): return f"layouts/island_{seed}_layout.json"
    def init_schema(): pass
    def db_status(): return {"fallback_mode": True, "oracle_online": False}

from audio_to_heightmap import (
    analyse_audio, generate_terrain, generate_moisture,
    classify_biomes, find_plot_positions, build_layout,
    build_preview, paint_farm_biome, get_farm_cluster_info,
    BIOME_NAMES, BIOME_COLOURS,
    WORLD_SIZE_PRESETS, DEFAULT_WORLD_SIZE_CM,
)
try:
    from town_generator import generate_town, BIOME_TOWN
    TOWN_GEN_AVAILABLE = True
except ImportError:
    TOWN_GEN_AVAILABLE = False

app = Flask(__name__, static_folder=None)

# ── Config ──
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR  = os.path.join(BASE_DIR, "saved_audio")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPPORTED_EXTS = (".wav",".mp3",".flac",".ogg",".aac",".m4a",".aiff",".opus")

EPIC_CLIENT_ID     = os.environ.get("EPIC_CLIENT_ID", "")
EPIC_CLIENT_SECRET = os.environ.get("EPIC_CLIENT_SECRET", "")
EPIC_DEPLOYMENT_ID = os.environ.get("EPIC_DEPLOYMENT_ID", "")
app.secret_key     = os.environ.get("FLASK_SECRET_KEY", "triptokforge-dev-2026")

REDIRECT_URI       = "https://triptokforge.org/auth/callback"
EPIC_AUTH_URL      = "https://www.epicgames.com/id/authorize"
EPIC_TOKEN_URL     = "https://api.epicgames.dev/epic/oauth/v2/token"
EPIC_USERINFO_URL  = "https://api.epicgames.dev/epic/oauth/v2/userInfo"
FORTNITE_STATS_URL = "https://fortnite-api.com/v2/stats/br/v2"
FORTNITE_COSMETICS = "https://fortnite-api.com/v2/cosmetics/br"

# ── Server state ──
_state = {
    "heightmap_bytes": None, "layout": None, "preview_bytes": None,
    "audio_path": None, "audio_filename": None, "audio_weights": None,
}
DEFAULT_WEIGHTS = {
    "sub_bass":0.5,"bass":0.5,"midrange":0.5,
    "presence":0.5,"brilliance":0.5,"tempo_bpm":120.0,"duration_s":0.0,
}
_cosmetics_cache = None

# ── Auth helper ──
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/home")
        return f(*args, **kwargs)
    return decorated

def epic_get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except:
        return {}

# ═════════════════════════════════════════════════════════════
# PAGES
# ═════════════════════════════════════════════════════════════

@app.route("/")
def root():
    return redirect("/home")

@app.route("/home")
def homepage():
    user = session.get("user")
    try: _n_members = len(get_all_members())
    except: _n_members = 0
    try: _n_islands = len(get_recent_islands(limit=999))
    except: _n_islands = 0
    try: _n_audio = len(get_audio_tracks())
    except: _n_audio = 0
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TriptokForge — Esports Platform</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600&display=swap" rel="stylesheet">
<style>
:root{{--black:#020408;--deep:#060d18;--panel:#0a1628;--border:#1a3a5c;--accent:#00d4ff;--accent2:#ff6b00;--text:#c8dff0;--dim:#4a6a8a}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}html{{scroll-behavior:smooth}}
body{{background:var(--black);color:var(--text);font-family:'Rajdhani',sans-serif;font-size:18px;overflow-x:hidden}}
body::before{{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,212,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,0.03) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}}
body::after{{content:'';position:fixed;top:-100%;left:0;right:0;height:200%;background:linear-gradient(transparent 50%,rgba(0,212,255,0.015) 50%);background-size:100% 4px;pointer-events:none;z-index:0;animation:scan 8s linear infinite}}
@keyframes scan{{to{{transform:translateY(50%)}}}}
nav{{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;justify-content:space-between;padding:0 48px;height:64px;background:rgba(2,4,8,0.9);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}}
.nav-logo{{font-family:'Orbitron',monospace;font-size:16px;font-weight:900;color:var(--accent);letter-spacing:3px;text-decoration:none}}
.nav-logo span{{color:var(--accent2)}}
.nav-links{{display:flex;gap:32px;list-style:none;align-items:center}}
.nav-links a{{color:var(--dim);text-decoration:none;font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;transition:color 0.2s}}
.nav-links a:hover{{color:var(--accent)}}
.btn{{display:inline-flex;align-items:center;gap:10px;font-family:'Orbitron',monospace;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:14px 32px;text-decoration:none;transition:all 0.2s;clip-path:polygon(8px 0%,100% 0%,calc(100% - 8px) 100%,0% 100%);border:none;cursor:pointer}}
.btn-p{{background:var(--accent);color:var(--black)}}.btn-p:hover{{background:#fff;box-shadow:0 0 40px var(--accent);transform:translateY(-2px)}}
.btn-o{{background:transparent;color:var(--text);border:1px solid var(--border)}}.btn-o:hover{{border-color:var(--accent);color:var(--accent)}}
.hero{{position:relative;min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:120px 24px 80px;z-index:1}}
.hero-bg{{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 40%,rgba(0,212,255,0.08) 0%,transparent 70%),radial-gradient(ellipse 40% 40% at 20% 80%,rgba(255,107,0,0.06) 0%,transparent 60%);z-index:-1}}
.tag{{display:inline-block;font-size:11px;font-weight:600;letter-spacing:4px;text-transform:uppercase;color:var(--accent2);border:1px solid rgba(255,107,0,0.3);padding:6px 18px;margin-bottom:32px}}
h1{{font-family:'Orbitron',monospace;font-size:clamp(36px,7vw,88px);font-weight:900;line-height:1.0;margin-bottom:24px}}
.l1{{color:#fff;display:block}}.l2{{color:transparent;-webkit-text-stroke:1px var(--accent);display:block}}
.hero p{{max-width:540px;margin:0 auto 48px;font-size:18px;font-weight:300;line-height:1.7;color:var(--dim)}}
.hero-btns{{display:flex;gap:20px;justify-content:center;flex-wrap:wrap}}
.stats-bar{{position:relative;z-index:1;display:flex;justify-content:center;border-top:1px solid var(--border);border-bottom:1px solid var(--border);background:rgba(10,22,40,0.6)}}
.stat{{flex:1;max-width:220px;padding:28px 24px;text-align:center;border-right:1px solid var(--border)}}.stat:last-child{{border-right:none}}
.sn{{font-family:'Orbitron',monospace;font-size:26px;font-weight:900;color:var(--accent);display:block}}
.sl{{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:var(--dim);margin-top:4px;display:block}}
.sec{{position:relative;z-index:1;padding:100px 48px;max-width:1200px;margin:0 auto}}
.s-tag{{font-size:11px;font-weight:600;letter-spacing:4px;text-transform:uppercase;color:var(--accent);margin-bottom:16px}}
h2{{font-family:'Orbitron',monospace;font-size:clamp(22px,3.5vw,40px);font-weight:900;color:#fff;margin-bottom:16px;line-height:1.1}}
.s-sub{{color:var(--dim);font-size:17px;max-width:500px;line-height:1.7;margin-bottom:56px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:2px;background:var(--border);border:1px solid var(--border)}}
.card{{background:var(--panel);padding:40px 32px;position:relative;overflow:hidden;transition:background 0.3s}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--accent),transparent);opacity:0;transition:opacity 0.3s}}
.card:hover{{background:#0d1f38}}.card:hover::before{{opacity:1}}
.ci{{font-size:28px;margin-bottom:20px;display:block}}
.ct{{font-family:'Orbitron',monospace;font-size:13px;font-weight:700;letter-spacing:1px;color:#fff;margin-bottom:12px}}
.card p{{font-size:15px;color:var(--dim);line-height:1.6}}
.forge-block{{position:relative;z-index:1;margin:0 48px 100px;border:1px solid var(--border);background:var(--panel);display:grid;grid-template-columns:1fr 1fr;min-height:320px;overflow:hidden}}
.forge-block::before{{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 60% 100% at 0% 50%,rgba(0,212,255,0.06) 0%,transparent 70%);pointer-events:none}}
.fc{{padding:56px;display:flex;flex-direction:column;justify-content:center;position:relative;z-index:1}}
.fl{{font-size:10px;letter-spacing:4px;text-transform:uppercase;color:var(--accent2);margin-bottom:16px}}
.fc h2{{margin-bottom:16px}}.fc p{{color:var(--dim);font-size:16px;line-height:1.7;margin-bottom:32px}}
.fv{{position:relative;overflow:hidden;background:var(--deep);display:flex;align-items:center;justify-content:center}}
.fg{{position:absolute;inset:0;background-image:linear-gradient(rgba(0,212,255,0.06) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,0.06) 1px,transparent 1px);background-size:32px 32px;animation:gm 4s linear infinite}}
@keyframes gm{{to{{background-position:32px 32px}}}}
.fh{{position:relative;z-index:1;font-family:'Orbitron',monospace;font-size:72px;font-weight:900;color:transparent;-webkit-text-stroke:1px rgba(0,212,255,0.3);animation:pulse 3s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{-webkit-text-stroke-color:rgba(0,212,255,0.3)}}50%{{-webkit-text-stroke-color:rgba(0,212,255,0.8);text-shadow:0 0 60px rgba(0,212,255,0.3)}}}}
footer{{position:relative;z-index:1;border-top:1px solid var(--border);padding:40px 48px;display:flex;align-items:center;justify-content:space-between;background:var(--deep)}}
.fl2{{font-family:'Orbitron',monospace;font-size:13px;font-weight:900;color:var(--dim);letter-spacing:3px}}
.fl2 span{{color:var(--accent2)}}
.flinks{{display:flex;gap:32px;list-style:none}}
.flinks a{{color:var(--dim);text-decoration:none;font-size:13px;transition:color 0.2s}}.flinks a:hover{{color:var(--accent)}}
.fcopy{{font-size:12px;color:var(--dim);opacity:0.5}}
@media(max-width:768px){{nav{{padding:0 20px}}.nav-links{{display:none}}.sec{{padding:60px 20px}}.forge-block{{grid-template-columns:1fr;margin:0 20px 60px}}.fv{{min-height:180px}}.fc{{padding:36px 28px}}footer{{flex-direction:column;gap:20px;text-align:center}}.stats-bar{{flex-wrap:wrap}}.stat{{min-width:50%;border-bottom:1px solid var(--border)}}}}
</style></head><body>
<nav>
  <a href="/home" class="nav-logo">Triptok<span>Forge</span></a>
  <ul class="nav-links">
    <li><a href="#features">Features</a></li>
    <li><a href="/forge">Island Forge</a></li>
    <li><a href="/privacy">Privacy</a></li>
    {'<li><a href="/dashboard" class="btn btn-p" style="padding:8px 20px">Dashboard →</a></li>' if user else '<li><a href="/auth/epic" class="btn btn-p" style="padding:8px 20px">⚡ Connect Epic</a></li>'}
  </ul>
</nav>
<section class="hero">
  <div class="hero-bg"></div>
  <div>
    <div class="tag">⚡ Esports Platform — Members Only</div>
    <h1><span class="l1">FORGE YOUR</span><span class="l2">LEGACY</span></h1>
    <p>Connect your Epic Games account. Build your member profile. Access tools built for serious Fortnite players and creators.</p>
    <div class="hero-btns">
      {'<a href="/dashboard" class="btn btn-p">Go to Dashboard →</a>' if user else '<a href="/auth/epic" class="btn btn-p">⚡ Connect Epic Account</a>'}
      <a href="#features" class="btn btn-o">Explore Platform →</a>
    </div>
  </div>
</section>
<div class="stats-bar">
  <div class="stat"><span class="sn">{{_n_members if _n_members else 'FREE'}}</span><span class="sl">{{'Members' if _n_members else 'Always'}}</span></div>
  <div class="stat"><span class="sn">{{_n_islands if _n_islands else 'UEFN'}}</span><span class="sl">{{'Islands' if _n_islands else 'Island Tools'}}</span></div>
  <div class="stat"><span class="sn">{{_n_audio if _n_audio else 'EPIC'}}</span><span class="sl">{{'Tracks' if _n_audio else 'OAuth Login'}}</span></div>
  <div class="stat"><span class="sn">PRO</span><span class="sl">Member Cards</span></div>
</div>
<section class="sec" id="features">
  <div class="s-tag">// Platform Features</div>
  <h2>Everything You Need</h2>
  <p class="s-sub">Built for Fortnite creators and competitive players. Login once with Epic, unlock everything.</p>
  <div class="grid">
    <div class="card"><span class="ci">🎮</span><div class="ct">Epic Account Login</div><p>Secure OAuth2 authentication directly through Epic Games. Your real account, your real identity.</p></div>
    <div class="card"><span class="ci">🃏</span><div class="ct">3D Member Card</div><p>Holographic player ID card with your stats, chosen skin, and rank. Shareable and always live.</p></div>
    <div class="card"><span class="ci">📊</span><div class="ct">Live Stats</div><p>K/D ratio, win rate, season performance pulled live from Fortnite and displayed on your profile.</p></div>
    <div class="card"><span class="ci">🏝️</span><div class="ct">Island Forge</div><p>Generate UEFN-ready island heightmaps from audio files. Export directly to Fortnite Creative.</p></div>
    <div class="card"><span class="ci">🎨</span><div class="ct">Skin Avatar</div><p>Browse the full Fortnite cosmetics library and pick any skin as your profile avatar.</p></div>
    <div class="card"><span class="ci">🏆</span><div class="ct">Members Only</div><p>All tools and features gated behind Epic account verification. Real players only.</p></div>
  </div>
</section>
<div class="forge-block" id="forge">
  <div class="fc">
    <div class="fl">// Tool — Island Forge</div>
    <h2>Generate Islands<br>From Sound</h2>
    <p>Upload any audio file. Island Forge analyzes frequency bands and generates a unique UEFN-ready heightmap — mountains from bass, rivers from rhythm, biomes from tone.</p>
    <a href="/forge" class="btn btn-p">Open Island Forge →</a>
  </div>
  <div class="fv"><div class="fg"></div><div class="fh">IF</div></div>
</div>
<footer>
  <div class="fl2">Triptok<span>Forge</span></div>
  <ul class="flinks"><li><a href="#features">Features</a></li><li><a href="/forge">Island Forge</a></li><li><a href="/privacy">Privacy</a></li></ul>
  <div class="fcopy">© 2026 EuphoriÆ Studios</div>
</footer>
</body></html>"""

# ─────────────────────────────────────────────────────────────
# EPIC OAUTH
# ─────────────────────────────────────────────────────────────

@app.route("/auth/epic")
def auth_epic():
    state = secrets.token_hex(16)
    session["oauth_state"] = state
    params = urllib.parse.urlencode({
        "client_id": EPIC_CLIENT_ID, "redirect_uri": REDIRECT_URI,
        "response_type": "code", "scope": "basic_profile", "state": state,
    })
    return redirect(f"{EPIC_AUTH_URL}?{params}")

@app.route("/auth/callback")
def auth_callback():
    if request.args.get("error"):
        return redirect("/home?error=epic_denied")
    code  = request.args.get("code", "")
    state = request.args.get("state", "")
    if state != session.get("oauth_state"):
        return redirect("/home?error=state_mismatch")
    try:
        import base64 as b64
        creds = b64.b64encode(f"{EPIC_CLIENT_ID}:{EPIC_CLIENT_SECRET}".encode()).decode()
        data  = urllib.parse.urlencode({"grant_type":"authorization_code","code":code,"redirect_uri":REDIRECT_URI}).encode()
        req   = urllib.request.Request(EPIC_TOKEN_URL, data=data, headers={"Authorization":f"Basic {creds}","Content-Type":"application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=10) as r:
            token_data = json.loads(r.read().decode())
    except Exception as e:
        print(f"[auth] Token exchange failed: {e}")
        return redirect("/home?error=token_failed")
    access_token = token_data.get("access_token", "")
    if not access_token:
        return redirect("/home?error=no_token")
    userinfo     = epic_get(EPIC_USERINFO_URL, access_token)
    display_name = userinfo.get("preferred_username", userinfo.get("name", "Player"))
    session["user"] = {
        "account_id":   userinfo.get("sub",""),
        "display_name": display_name,
        "avatar_url":   userinfo.get("picture",""),
        "access_token": access_token,
        "skin": None, "skin_name": "Default", "skin_img": "",
    }
    # Persist member to Oracle DB
    upsert_member(
        epic_id=userinfo.get("sub",""),
        display_name=display_name,
        avatar_url=userinfo.get("picture",""),
    )
    return redirect("/dashboard")

@app.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect("/home")

# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    user      = session["user"]
    name      = user["display_name"]
    skin_img  = user.get("skin_img","")
    skin_name = user.get("skin_name","Default")
    card_img  = skin_img if skin_img else user.get("avatar_url","")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — TriptokForge</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600&display=swap" rel="stylesheet">
<style>
:root{{--black:#020408;--deep:#060d18;--panel:#0a1628;--border:#1a3a5c;--accent:#00d4ff;--accent2:#ff6b00;--text:#c8dff0;--dim:#4a6a8a}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--black);color:var(--text);font-family:'Rajdhani',sans-serif;min-height:100vh;overflow-x:hidden}}
body::before{{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,212,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,0.03) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}}
nav{{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;justify-content:space-between;padding:0 48px;height:64px;background:rgba(2,4,8,0.9);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}}
.nav-logo{{font-family:'Orbitron',monospace;font-size:16px;font-weight:900;color:var(--accent);letter-spacing:3px;text-decoration:none}}
.nav-logo span{{color:var(--accent2)}}
.nav-r{{display:flex;gap:24px;align-items:center}}
.nav-r a{{color:var(--dim);text-decoration:none;font-size:13px;letter-spacing:2px;text-transform:uppercase;transition:color 0.2s}}
.nav-r a:hover{{color:var(--accent)}}.logout{{color:var(--accent2)!important}}
.dash{{position:relative;z-index:1;max-width:1300px;margin:0 auto;padding:100px 48px 80px}}
.dash-grid{{display:grid;grid-template-columns:360px 1fr;gap:32px;align-items:start}}
.card-wrap{{perspective:1200px}}
.holo-card{{width:340px;height:520px;border-radius:16px;background:linear-gradient(135deg,#0a1628 0%,#0d2040 50%,#0a1628 100%);border:1px solid var(--border);position:relative;overflow:hidden;transform-style:preserve-3d;transition:transform 0.1s ease;cursor:pointer;box-shadow:0 0 40px rgba(0,212,255,0.1),inset 0 0 60px rgba(0,212,255,0.03)}}
.holo-card::before{{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(0,212,255,0.15) 0%,transparent 30%,rgba(255,107,0,0.08) 60%,transparent 80%,rgba(0,212,255,0.1) 100%);z-index:2;pointer-events:none;animation:holo 4s ease-in-out infinite}}
@keyframes holo{{0%,100%{{opacity:0.6}}50%{{opacity:1}}}}
.holo-card::after{{content:'';position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,212,255,0.03) 2px,rgba(0,212,255,0.03) 4px);z-index:3;pointer-events:none}}
.ch{{position:relative;z-index:4;padding:20px 24px 0;display:flex;justify-content:space-between;align-items:center}}
.ch-s{{font-family:'Orbitron',monospace;font-size:9px;letter-spacing:3px;color:var(--accent);text-transform:uppercase}}
.ch-id{{font-family:'Orbitron',monospace;font-size:9px;color:var(--dim);letter-spacing:1px}}
.cskin{{position:relative;z-index:4;height:280px;display:flex;align-items:center;justify-content:center;overflow:hidden}}
.cskin img{{max-height:280px;max-width:100%;object-fit:contain;filter:drop-shadow(0 0 20px rgba(0,212,255,0.4));animation:float 3s ease-in-out infinite}}
.no-skin{{font-family:'Orbitron',monospace;font-size:48px;font-weight:900;color:transparent;-webkit-text-stroke:1px rgba(0,212,255,0.2)}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
.cinfo{{position:relative;z-index:4;padding:0 24px 20px}}
.cname{{font-family:'Orbitron',monospace;font-size:18px;font-weight:900;color:#fff;letter-spacing:1px;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.csname{{font-size:12px;color:var(--accent);letter-spacing:2px;text-transform:uppercase;margin-bottom:16px}}
.cstats{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}}
.csv{{background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.1);padding:8px;text-align:center}}
.csv-v{{font-family:'Orbitron',monospace;font-size:14px;font-weight:700;color:var(--accent);display:block}}
.csv-l{{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--dim)}}
.cglow{{position:absolute;bottom:-40px;left:50%;transform:translateX(-50%);width:200px;height:80px;background:radial-gradient(ellipse,rgba(0,212,255,0.2) 0%,transparent 70%);z-index:1;animation:glow 3s ease-in-out infinite}}
@keyframes glow{{0%,100%{{opacity:0.5}}50%{{opacity:1}}}}
.rp{{display:flex;flex-direction:column;gap:24px}}
.pb{{background:var(--panel);border:1px solid var(--border);padding:32px}}
.pt{{font-family:'Orbitron',monospace;font-size:12px;font-weight:700;letter-spacing:2px;color:var(--accent);text-transform:uppercase;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border)}}
.welcome{{font-family:'Orbitron',monospace;font-size:clamp(16px,2.5vw,26px);font-weight:900;color:#fff;margin-bottom:8px}}
.welcome span{{color:var(--accent)}}
.wsub{{color:var(--dim);font-size:15px;line-height:1.6;margin-bottom:24px}}
.tgrid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.tbtn{{display:flex;align-items:center;gap:12px;background:rgba(0,212,255,0.05);border:1px solid var(--border);padding:16px 20px;text-decoration:none;color:var(--text);transition:all 0.2s;font-size:15px;font-weight:600}}
.tbtn:hover{{border-color:var(--accent);background:rgba(0,212,255,0.08);color:var(--accent)}}
.sgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.sbox{{background:rgba(0,212,255,0.04);border:1px solid var(--border);padding:20px;text-align:center}}
.sv{{font-family:'Orbitron',monospace;font-size:22px;font-weight:900;color:var(--accent);display:block}}
.sl{{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin-top:4px;display:block}}
.skin-search{{width:100%;background:rgba(0,212,255,0.05);border:1px solid var(--border);color:var(--text);font-family:'Rajdhani',sans-serif;font-size:15px;padding:12px 16px;margin-bottom:16px;outline:none}}
.skin-search:focus{{border-color:var(--accent)}}
.skin-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:8px;max-height:280px;overflow-y:auto}}
.si{{background:rgba(0,212,255,0.04);border:1px solid var(--border);padding:8px;cursor:pointer;transition:all 0.2s;text-align:center}}
.si:hover,.si.active{{border-color:var(--accent);background:rgba(0,212,255,0.1)}}
.si img{{width:100%;aspect-ratio:1;object-fit:cover}}
.si-n{{font-size:9px;color:var(--dim);margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.loading{{color:var(--dim);font-size:14px;letter-spacing:2px;text-align:center;padding:20px}}
@media(max-width:900px){{.dash-grid{{grid-template-columns:1fr}}.holo-card{{width:100%}}.cskin{{height:220px}}.tgrid{{grid-template-columns:1fr}}nav{{padding:0 20px}}}}
</style></head><body>
<nav>
  <a href="/home" class="nav-logo">Triptok<span>Forge</span></a>
  <div class="nav-r"><a href="/forge">Island Forge</a><a href="/auth/logout" class="logout">Logout</a></div>
</nav>
<div class="dash">
  <div class="dash-grid">
    <div class="card-wrap">
      <div class="holo-card" id="holoCard">
        <div class="ch"><span class="ch-s">EuphoriÆ Studios</span><span class="ch-id">MEMBER</span></div>
        <div class="cskin" id="cardSkin">
          {('<img src="'+card_img+'" id="skinImg">') if card_img else '<div class="no-skin">FN</div>'}
        </div>
        <div class="cinfo">
          <div class="cname">{name}</div>
          <div class="csname" id="cardSkinName">{skin_name}</div>
          <div class="cstats">
            <div class="csv"><span class="csv-v" id="cWins">—</span><span class="csv-l">Wins</span></div>
            <div class="csv"><span class="csv-v" id="cKD">—</span><span class="csv-l">K/D</span></div>
            <div class="csv"><span class="csv-v" id="cMatches">—</span><span class="csv-l">Matches</span></div>
          </div>
        </div>
        <div class="cglow"></div>
      </div>
    </div>
    <div class="rp">
      <div class="pb">
        <div class="welcome">Welcome, <span>{name}</span></div>
        <div class="wsub">Your TriptokForge member dashboard. Access all platform tools and manage your profile.</div>
        <div class="tgrid">
          <a href="/forge" class="tbtn">🏝️ Island Forge</a>
          <a href="#skins" class="tbtn">🎨 Change Skin</a>
          <a href="#stats" class="tbtn" onclick="loadStats()">📊 Refresh Stats</a>
          <a href="/auth/logout" class="tbtn">🚪 Logout</a>
        </div>
      </div>
      <div class="pb" id="stats">
        <div class="pt">// Fortnite Stats</div>
        <div class="sgrid">
          <div class="sbox"><span class="sv" id="s-wins">—</span><span class="sl">Total Wins</span></div>
          <div class="sbox"><span class="sv" id="s-kd">—</span><span class="sl">K/D Ratio</span></div>
          <div class="sbox"><span class="sv" id="s-matches">—</span><span class="sl">Matches</span></div>
          <div class="sbox"><span class="sv" id="s-kills">—</span><span class="sl">Total Kills</span></div>
          <div class="sbox"><span class="sv" id="s-winpct">—</span><span class="sl">Win Rate</span></div>
          <div class="sbox"><span class="sv" id="s-score">—</span><span class="sl">Score/Match</span></div>
        </div>
        <div id="statsMsg" style="color:var(--dim);font-size:13px;margin-top:12px;letter-spacing:1px"></div>
      </div>
      <div class="pb" id="skins">
        <div class="pt">// Choose Your Skin</div>
        <input class="skin-search" type="text" placeholder="Search skins..." id="skinSearch" oninput="filterSkins()">
        <div class="skin-grid" id="skinGrid"><div class="loading">Loading cosmetics...</div></div>
      </div>
    </div>
  </div>
</div>
<script>
const card=document.getElementById('holoCard');
card.addEventListener('mousemove',e=>{{
  const r=card.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;
  card.style.transform=`rotateY(${{x*18}}deg) rotateX(${{-y*14}}deg) scale(1.02)`;
}});
card.addEventListener('mouseleave',()=>{{card.style.transform='rotateY(0) rotateX(0) scale(1)';}});
async function loadStats(){{
  const name=encodeURIComponent('{name}');
  document.getElementById('statsMsg').textContent='Loading stats...';
  try{{
    const r=await fetch(`/api/stats?name=${{name}}`),d=await r.json();
    if(d.ok){{
      const s=d.stats;
      document.getElementById('s-wins').textContent=s.wins||'0';
      document.getElementById('s-kd').textContent=s.kd||'0.0';
      document.getElementById('s-matches').textContent=s.matches||'0';
      document.getElementById('s-kills').textContent=s.kills||'0';
      document.getElementById('s-winpct').textContent=s.winPct||'0%';
      document.getElementById('s-score').textContent=s.score||'0';
      document.getElementById('cWins').textContent=s.wins||'0';
      document.getElementById('cKD').textContent=s.kd||'0.0';
      document.getElementById('cMatches').textContent=s.matches||'0';
      document.getElementById('statsMsg').textContent='';
    }}else{{document.getElementById('statsMsg').textContent='Stats not found — make sure your Fortnite account is public.';}}
  }}catch(e){{document.getElementById('statsMsg').textContent='Could not load stats.';}}
}}
let allSkins=[];
async function loadSkins(){{
  try{{
    const r=await fetch('/api/cosmetics'),d=await r.json();
    if(d.ok){{allSkins=d.skins;renderSkins(allSkins);}}
  }}catch(e){{document.getElementById('skinGrid').innerHTML='<div class="loading">Could not load cosmetics.</div>';}}
}}
function renderSkins(skins){{
  const g=document.getElementById('skinGrid');
  if(!skins.length){{g.innerHTML='<div class="loading">No results.</div>';return;}}
  const esc=n=>n.replace(/['"]/g,'');g.innerHTML=skins.slice(0,120).map(s=>'<div class="si" onclick="selectSkin(\'' +s.id+ '\',\'' +esc(s.name)+ '\',\'' +s.img+ '\')" title="' +s.name+ '"><img src="' +s.img+ '" loading="lazy"><div class="si-n">' +s.name+ '</div></div>').join('');
}}
function filterSkins(){{const q=document.getElementById('skinSearch').value.toLowerCase();renderSkins(q?allSkins.filter(s=>s.name.toLowerCase().includes(q)):allSkins);}}
async function selectSkin(id,name,img){{
  document.querySelectorAll('.si').forEach(el=>el.classList.remove('active'));
  event.currentTarget.classList.add('active');
  document.getElementById('cardSkin').innerHTML=`<img src="${{img}}" style="max-height:280px;max-width:100%;object-fit:contain;filter:drop-shadow(0 0 20px rgba(0,212,255,0.4));animation:float 3s ease-in-out infinite">`;
  document.getElementById('cardSkinName').textContent=name;
  await fetch('/api/set_skin',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id,name,img}})}});
}}
loadStats();loadSkins();
</script>
</body></html>"""

# ─────────────────────────────────────────────────────────────
# PRIVACY
# ─────────────────────────────────────────────────────────────

@app.route("/privacy")
def privacy():
    return """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Privacy — TriptokForge</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@300;400;600&display=swap" rel="stylesheet">
<style>:root{--black:#020408;--deep:#060d18;--panel:#0a1628;--border:#1a3a5c;--accent:#00d4ff;--accent2:#ff6b00;--text:#c8dff0;--dim:#4a6a8a}*{margin:0;padding:0;box-sizing:border-box}body{background:var(--black);color:var(--text);font-family:'Rajdhani',sans-serif;font-size:17px;line-height:1.7}nav{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;justify-content:space-between;padding:0 48px;height:64px;background:rgba(2,4,8,0.9);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}.logo{font-family:'Orbitron',monospace;font-size:16px;font-weight:900;color:var(--accent);letter-spacing:3px;text-decoration:none}.logo span{color:var(--accent2)}nav a.back{color:var(--dim);text-decoration:none;font-size:13px;letter-spacing:2px;text-transform:uppercase}.container{position:relative;z-index:1;max-width:760px;margin:0 auto;padding:100px 24px 80px}h1{font-family:'Orbitron',monospace;font-size:32px;font-weight:900;color:#fff;margin-bottom:8px}.upd{font-size:13px;color:var(--dim);margin-bottom:40px;padding-bottom:24px;border-bottom:1px solid var(--border)}h2{font-family:'Orbitron',monospace;font-size:13px;font-weight:700;color:var(--accent);letter-spacing:1px;margin:32px 0 12px;text-transform:uppercase}p{color:var(--dim);margin-bottom:12px}ul{color:var(--dim);padding-left:24px;margin-bottom:12px}li{margin-bottom:6px}a{color:var(--accent)}.box{margin-top:40px;padding:28px;border:1px solid var(--border);background:var(--panel)}footer{border-top:1px solid var(--border);padding:28px 48px;text-align:center;background:var(--deep)}footer a{color:var(--dim);text-decoration:none;font-size:14px}</style>
</head><body>
<nav><a href="/home" class="logo">Triptok<span>Forge</span></a><a href="/home" class="back">← Home</a></nav>
<div class="container">
<h1>Privacy Policy</h1><p class="upd">Last updated: March 2026 — EuphoriÆ Studios</p>
<p>TriptokForge is operated by EuphoriÆ Studios. This policy explains how we collect, use, and protect your information.</p>
<h2>Information We Collect</h2><ul><li>Your Epic Games account ID and display name</li><li>Your Epic Games profile avatar</li><li>Public Fortnite statistics</li><li>Your selected cosmetic skin preference</li></ul>
<h2>How We Use Your Information</h2><ul><li>Authenticate your identity via Epic Games OAuth2</li><li>Display your member profile card</li><li>Show your public Fortnite statistics</li><li>Maintain your session while logged in</li></ul>
<h2>Third Party Services</h2><ul><li>Epic Games OAuth — account authentication</li><li>Fortnite-API.com — public player statistics</li><li>Oracle Cloud Infrastructure — server hosting</li></ul>
<h2>Your Rights</h2><ul><li>Access the personal data we hold about you</li><li>Request deletion of your account and data</li><li>Disconnect your Epic Games account at any time</li></ul>
<div class="box"><h2>Contact</h2><p>For privacy questions: <a href="https://github.com/iamjedi888">github.com/iamjedi888</a></p></div>
</div>
<footer><a href="/home">← Back to TriptokForge</a></footer>
</body></html>"""

# ─────────────────────────────────────────────────────────────
# FORGE (Island Forge UI)
# ─────────────────────────────────────────────────────────────

@app.route("/forge")
def forge():
    path = os.path.join(BASE_DIR, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html"}

# ─────────────────────────────────────────────────────────────
# API — STATS
# ─────────────────────────────────────────────────────────────



@app.route("/api/members")
def api_members():
    try:
        members = get_all_members()
        return jsonify({"ok": True, "count": len(members), "members": members})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/stats")
@login_required
def api_stats():
    name = request.args.get("name","")
    if not name:
        return jsonify({"ok":False,"error":"No name"})
    try:
        url = f"{FORTNITE_STATS_URL}?name={urllib.parse.quote(name)}"
        req = urllib.request.Request(url,headers={"User-Agent":"TriptokForge/1.0"})
        with urllib.request.urlopen(req,timeout=8) as r:
            data=json.loads(r.read().decode())
        if data.get("status")!=200:
            return jsonify({"ok":False,"error":"Player not found"})
        ov=data.get("data",{}).get("stats",{}).get("all",{}).get("overall",{})
        wins=ov.get("wins",0); kills=ov.get("kills",0); matches=ov.get("matches",0)
        kd=ov.get("kd",0.0); score=ov.get("scorePerMatch",0)
        win_pct=f"{round(wins/matches*100,1)}%" if matches else "0%"
        return jsonify({"ok":True,"stats":{"wins":wins,"kills":kills,"matches":matches,"kd":round(kd,2),"winPct":win_pct,"score":round(score,1)}})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})

# ─────────────────────────────────────────────────────────────
# API — COSMETICS
# ─────────────────────────────────────────────────────────────

@app.route("/api/cosmetics")
@login_required
def api_cosmetics():
    global _cosmetics_cache
    if _cosmetics_cache:
        return jsonify({"ok":True,"skins":_cosmetics_cache})
    try:
        req=urllib.request.Request(FORTNITE_COSMETICS,headers={"User-Agent":"TriptokForge/1.0"})
        with urllib.request.urlopen(req,timeout=15) as r:
            data=json.loads(r.read().decode())
        skins=[]
        for item in data.get("data",[]):
            if item.get("type",{}).get("value")!="outfit": continue
            imgs=item.get("images",{}); img=imgs.get("smallIcon") or imgs.get("icon") or ""
            if not img: continue
            skins.append({"id":item.get("id",""),"name":item.get("name",""),"img":img})
        _cosmetics_cache=skins
        return jsonify({"ok":True,"skins":skins})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})

# ─────────────────────────────────────────────────────────────
# API — SET SKIN
# ─────────────────────────────────────────────────────────────

@app.route("/api/set_skin",methods=["POST"])
@login_required
def api_set_skin():
    data=request.get_json(force=True)
    session["user"]["skin"]=data.get("id")
    session["user"]["skin_name"]=data.get("name","")
    session["user"]["skin_img"]=data.get("img","")
    session.modified=True
    update_member_skin(
        epic_id=session["user"].get("account_id",""),
        skin_id=data.get("id",""),
        skin_name=data.get("name",""),
        skin_img=data.get("img",""),
    )
    return jsonify({"ok":True})

# ─────────────────────────────────────────────────────────────
# GENERATE
# ─────────────────────────────────────────────────────────────

@app.route("/generate", methods=["POST"])
@app.route("/generate", methods=["POST"])
def generate():
    try:
        data           = request.get_json(force=True)
        seed           = int(data.get("seed", 42))
        size           = int(data.get("size", 2017))
        n_plots        = int(data.get("plots", 32))
        spacing        = int(data.get("spacing", 40))
        weights        = data.get("weights", DEFAULT_WEIGHTS)
        water_level    = float(data.get("water_level", 0.20))
        world_wrap     = bool(data.get("world_wrap", True))
        cluster_angle  = float(data.get("cluster_angle", 135.0))
        cluster_spread = float(data.get("cluster_spread", 1.0))

        # Resolve world size — preset name or raw cm
        ws_raw = data.get("world_size", "double_br")
        if isinstance(ws_raw, str) and ws_raw in WORLD_SIZE_PRESETS:
            world_size_cm = WORLD_SIZE_PRESETS[ws_raw]
        else:
            world_size_cm = int(data.get("world_size_cm", DEFAULT_WORLD_SIZE_CM))

        water_level    = max(0.0, min(0.48, water_level))
        cluster_spread = max(0.5, min(2.0, cluster_spread))
        if size not in (505, 1009, 2017, 4033): size = 1009
        for k, v in DEFAULT_WEIGHTS.items(): weights.setdefault(k, v)

        # ── Generate terrain ──
        height, road_mask = generate_terrain(size, seed, weights, water_level)
        moisture = generate_moisture(size, seed)
        biome    = classify_biomes(height, moisture, water_level)

        # ── Town generator ──
        town_data   = None
        street_mask = None
        town_mask   = None
        farm_mask   = None
        if TOWN_GEN_AVAILABLE:
            from audio_to_heightmap import build_island_mask
            island_mask = build_island_mask(size, seed,
                                            weights.get("presence", 0.5),
                                            weights.get("tempo_bpm", 120.0))
            if BIOME_TOWN not in BIOME_NAMES:
                BIOME_NAMES[BIOME_TOWN]   = "Town"
                BIOME_COLOURS[BIOME_TOWN] = (158, 148, 132)
            height, biome, plots, town_data, street_mask, town_mask, farm_mask = generate_town(
                height, biome, island_mask, size, seed, weights,
                n_plots=n_plots,
                cluster_angle_deg=cluster_angle,
                cluster_spread=cluster_spread * 0.22,
            )
        else:
            plots = find_plot_positions(height, biome, n_plots, size,
                                        min_spacing=spacing,
                                        cluster_angle_deg=cluster_angle,
                                        cluster_spread=cluster_spread)
            biome = paint_farm_biome(biome, plots, size)

        # ── Layout JSON ──
        layout = build_layout(height, biome, plots, size, seed, weights,
                              water_level, world_wrap, world_size_cm)
        if town_data:
            layout["town_data"]   = town_data
            layout["town_center"] = {
                "pixel":      town_data["center_pixel"],
                "world_x_cm": town_data["center_world_x"],
                "world_z_cm": town_data["center_world_z"],
            }

        # ── Save heightmap ──
        from PIL import Image
        hm_16  = (height * 65535).astype(np.uint16)
        hm_img = Image.fromarray(hm_16)
        hm_img.save(os.path.join(OUTPUT_DIR, f"island_{seed}_heightmap.png"))
        hm_buf = io.BytesIO(); hm_img.save(hm_buf, format="PNG")
        _state["heightmap_bytes"] = hm_buf.getvalue()

        # ── Save layout ──
        with open(os.path.join(OUTPUT_DIR, f"island_{seed}_layout.json"), "w") as jf:
            json.dump(layout, jf, indent=2)
        _state["layout"] = layout

        # ── Build preview (downsample for large maps) ──
        prev_size = min(size, 1009)
        if prev_size < size:
            factor = size // prev_size
            h_dn  = height[::factor, ::factor][:prev_size, :prev_size]
            b_dn  = biome[::factor, ::factor][:prev_size, :prev_size]
            rm_dn = road_mask[::factor, ::factor][:prev_size, :prev_size] if road_mask is not None else None
            p_dn  = [(r // factor, c // factor) for r, c in plots]
        else:
            h_dn, b_dn, p_dn, rm_dn = height, biome, plots, road_mask

        prev_rgb = build_preview(h_dn, b_dn, p_dn, prev_size, rm_dn)

        # Town overlay on preview
        if TOWN_GEN_AVAILABLE and town_data and street_mask is not None:
            from town_generator import (build_street_grid, classify_blocks,
                                        place_lots_in_block, render_town_overlay)
            tc     = town_data["center_pixel"]
            scale  = prev_size / size
            tc_s   = (int(tc[0]*scale), int(tc[1]*scale))
            f      = max(1, size // prev_size)
            s_dn   = street_mask[::f, ::f][:prev_size, :prev_size]
            tm_dn  = town_mask[::f, ::f][:prev_size, :prev_size]
            fm_dn  = farm_mask[::f, ::f][:prev_size, :prev_size]
            st, bl = build_street_grid(tc_s[0], tc_s[1], prev_size)
            bl     = classify_blocks(bl, tc_s[0], tc_s[1])
            lots   = []
            for b in bl: lots.extend(place_lots_in_block(b, prev_size, b.get("type", "residential")))
            p_s    = [(int(r*scale), int(c*scale)) for r, c in plots]
            prev_rgb = render_town_overlay(prev_rgb, s_dn, tm_dn, fm_dn, p_s, bl, lots, prev_size)

        prev_img = Image.fromarray(prev_rgb, mode="RGB")
        prev_img.save(os.path.join(OUTPUT_DIR, f"island_{seed}_preview.png"))
        prev_buf = io.BytesIO(); prev_img.save(prev_buf, format="PNG")
        _state["preview_bytes"] = prev_buf.getvalue()
        prev_b64 = base64.b64encode(_state["preview_bytes"]).decode("utf-8")

        # ── Upload to OCI Object Storage ──
        preview_url = ""
        heightmap_url = ""
        layout_url = ""
        try:
            preview_url   = oci_upload_bytes(_state["preview_bytes"],   preview_object_name(seed))
            heightmap_url = oci_upload_bytes(_state["heightmap_bytes"], heightmap_object_name(seed))
            layout_url    = oci_upload_bytes(json.dumps(layout, indent=2).encode(), layout_object_name(seed))
        except Exception as oci_err:
            print(f"[oci] island upload failed (non-fatal): {oci_err}")

        # ── Save island to Oracle DB ──
        creator_id = session.get("user", {}).get("accountId", "anonymous")
        try:
            save_island(
                seed=seed, creator_id=creator_id, world_size_cm=world_size_cm,
                preview_url=preview_url, heightmap_url=heightmap_url,
                layout_url=layout_url, weights=weights,
                biome_stats={b["name"]: b["pct"] for b in biome_stats if "name" in b},
            )
        except Exception as db_err:
            print(f"[db] save_island failed (non-fatal): {db_err}")

        # ── Biome stats ──
        total = size * size
        biome_stats = [
            {
                "name":   BIOME_NAMES.get(b, "?"),
                "pct":    round(float(np.sum(biome == b)) / total * 100, 1),
                "colour": "rgb({},{},{})".format(*BIOME_COLOURS.get(b, (100,100,100))),
            }
            for b in sorted(BIOME_NAMES.keys()) if np.any(biome == b)
        ]

        return jsonify({
            "ok":              True,
            "preview_b64":     prev_b64,
            "plots_found":     len(plots),
            "biome_stats":     biome_stats,
            "verse_constants": layout["verse_constants"],
            "town_center":     layout.get("town_center"),
            "meta":            layout["meta"],
            "world_wrap":      world_wrap,
            "water_level":     water_level,
            "world_size_cm":   world_size_cm,
            "saved_to":        OUTPUT_DIR,
            "preview_url":     preview_url,
            "heightmap_url":   heightmap_url,
            "layout_url":      layout_url,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# AUDIO ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    try:
        if "file" not in request.files:
            return jsonify({"ok":False,"error":"No file"}),400
        f=request.files["file"]; ext=os.path.splitext(f.filename)[1].lower()
        if ext not in SUPPORTED_EXTS:
            return jsonify({"ok":False,"error":f"Unsupported: {', '.join(SUPPORTED_EXTS)}"}),400
        safe=os.path.basename(f.filename); save_path=os.path.join(AUDIO_DIR,safe)
        stem,sfx=os.path.splitext(safe); c=1
        while os.path.exists(save_path):
            save_path=os.path.join(AUDIO_DIR,f"{stem}_{c}{sfx}"); c+=1
        f.save(save_path)
        weights=analyse_audio(save_path)
        fn = os.path.basename(save_path)
        _state["audio_path"]=save_path; _state["audio_filename"]=fn; _state["audio_weights"]=weights
        # ── Upload to OCI Object Storage ──
        storage_url = ""
        try:
            storage_url = oci_upload(save_path, audio_object_name(fn))
        except Exception as oci_err:
            print(f"[oci] audio upload failed (non-fatal): {oci_err}")
        # ── Save metadata to Oracle DB ──
        uploader_id = session.get("user", {}).get("accountId", "anonymous")
        try:
            save_audio_track(fn, weights, uploader_id=uploader_id, storage_url=storage_url)
        except Exception as db_err:
            print(f"[db] save_audio_track failed (non-fatal): {db_err}")
        return jsonify({"ok":True,"filename":fn,"weights":weights,"storage_url":storage_url})
    except Exception as e:
        traceback.print_exc(); return jsonify({"ok":False,"error":str(e)}),500

@app.route("/audio/list")
def audio_list():
    try:
        files=[{"filename":fn,"size_kb":round(os.path.getsize(os.path.join(AUDIO_DIR,fn))/1024,1),"active":_state["audio_filename"]==fn}
               for fn in sorted(os.listdir(AUDIO_DIR)) if os.path.splitext(fn)[1].lower() in SUPPORTED_EXTS]
        return jsonify({"ok":True,"files":files})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}),500

@app.route("/audio/select", methods=["POST"])
def audio_select():
    try:
        data=request.get_json(force=True); path=os.path.join(AUDIO_DIR,os.path.basename(data.get("filename","")))
        if not os.path.exists(path): return jsonify({"ok":False,"error":"Not found"}),404
        weights=analyse_audio(path)
        _state["audio_path"]=path; _state["audio_filename"]=os.path.basename(path); _state["audio_weights"]=weights
        return jsonify({"ok":True,"filename":os.path.basename(path),"weights":weights})
    except Exception as e:
        traceback.print_exc(); return jsonify({"ok":False,"error":str(e)}),500

@app.route("/audio/<filename>", methods=["DELETE"])
def audio_delete(filename):
    try:
        path=os.path.join(AUDIO_DIR,os.path.basename(filename))
        if not os.path.exists(path): return jsonify({"ok":False,"error":"Not found"}),404
        os.remove(path)
        # ── Delete from OCI ──
        try:
            oci_delete(audio_object_name(filename))
        except Exception as oci_err:
            print(f"[oci] delete failed (non-fatal): {oci_err}")
        # ── Delete from DB ──
        try:
            delete_audio_track(filename)
        except Exception as db_err:
            print(f"[db] delete_audio_track failed (non-fatal): {db_err}")
        if _state["audio_filename"]==filename:
            _state["audio_path"]=_state["audio_filename"]=_state["audio_weights"]=None
        return jsonify({"ok":True})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}),500

@app.route("/audio/stream/<filename>")
def audio_stream(filename):
    """Stream audio file to browser player with range request support."""
    path = os.path.join(AUDIO_DIR, os.path.basename(filename))
    if not os.path.exists(path):
        return "Not found", 404
    ext  = os.path.splitext(filename)[1].lower()
    mime = {
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
        ".flac":"audio/flac", ".aac": "audio/aac", ".m4a": "audio/mp4",
        ".aiff":"audio/aiff",".opus":"audio/opus",
    }.get(ext, "audio/mpeg")
    return send_file(path, mimetype=mime, conditional=True)

@app.route("/download/heightmap")
def download_heightmap():
    if not _state["heightmap_bytes"]: return "No heightmap yet",404
    return send_file(io.BytesIO(_state["heightmap_bytes"]),mimetype="image/png",as_attachment=True,download_name="island_heightmap.png")

@app.route("/download/layout")
def download_layout():
    if not _state["layout"]: return "No layout yet",404
    return send_file(io.BytesIO(json.dumps(_state["layout"],indent=2).encode()),mimetype="application/json",as_attachment=True,download_name="island_layout.json")

@app.route("/download/preview")
def download_preview():
    if not _state["preview_bytes"]: return "No preview yet",404
    return send_file(io.BytesIO(_state["preview_bytes"]),mimetype="image/png",as_attachment=True,download_name="island_preview.png")

@app.route("/random_seed")
def random_seed():
    import random; return jsonify({"seed":random.randint(1,99999)})

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────



@app.route("/sitemap.xml")
def sitemap_xml():
    pages=["/home","/forge","/gallery","/feed","/jukebox","/community","/dev","/privacy"]
    urls="".join(f"<url><loc>https://triptokforge.org{p}</loc></url>" for p in pages)
    xml=f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return xml, 200, {"Content-Type": "application/xml"}

@app.route("/health")
def health():
    stats = {}
    try:
        stats["members"] = len(get_all_members())
        stats["islands"]  = len(get_recent_islands(limit=999))
        stats["audio"]    = len(get_audio_tracks())
    except:
        pass
    return jsonify({"ok": True, "service": "triptokforge", "version": "3.0", **db_status(), **stats})

# ─────────────────────────────────────────────────────────────
# PLATFORM PAGES — Gallery, Feed, Jukebox, Community, Dev, Admin
# All share the same nav shell; content is minimal but functional.
# ─────────────────────────────────────────────────────────────

_NAV = """
<nav style="position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;
     justify-content:space-between;padding:0 40px;height:60px;
     background:rgba(2,4,8,.95);backdrop-filter:blur(12px);
     border-bottom:1px solid #1a3a5c;font-family:'Rajdhani',sans-serif">
  <a href="/home" style="font-family:'Orbitron',monospace;font-size:15px;font-weight:900;
     color:#00d4ff;letter-spacing:3px;text-decoration:none">
     Triptok<span style="color:#ff6b00">Forge</span></a>
  <div style="display:flex;gap:28px;align-items:center">
    <a href="/forge"     style="color:#4a6a8a;text-decoration:none;font-size:13px;letter-spacing:1px">FORGE</a>
    <a href="/gallery"   style="color:#4a6a8a;text-decoration:none;font-size:13px;letter-spacing:1px">GALLERY</a>
    <a href="/feed"      style="color:#4a6a8a;text-decoration:none;font-size:13px;letter-spacing:1px">FEED</a>
    <a href="/community" style="color:#4a6a8a;text-decoration:none;font-size:13px;letter-spacing:1px">COMMUNITY</a>
    <a href="/dev"       style="color:#4a6a8a;text-decoration:none;font-size:13px;letter-spacing:1px">DEV</a>
    {login_link}
  </div>
</nav>
"""

def _shell(title, content, active="", user=None):
    login_link = (f'<a href="/dashboard" style="color:#00d4ff;text-decoration:none;font-size:13px">DASHBOARD</a>'
                  if user else
                  f'<a href="/auth/epic" style="background:#00d4ff;color:#020408;padding:6px 16px;font-size:12px;font-weight:700;letter-spacing:1px;text-decoration:none">⚡ LOGIN</a>')
    nav = _NAV.format(login_link=login_link)
    _pinned_banner = ""
    try:
        _anns = get_announcements()
        _pinned = [a for a in _anns if a.get("pinned")]
        if _pinned:
            _p = _pinned[0]
            _pinned_banner = (
                '<div style="background:rgba(255,107,0,0.08);border-bottom:1px solid rgba(255,107,0,0.3);'
                'padding:10px 40px;font-size:13px;color:#ff9944;font-family:Rajdhani,sans-serif;'
                'display:flex;align-items:center;gap:12px;position:relative;z-index:99;margin-top:60px">'
                '<span style="font-family:Orbitron,monospace;font-size:9px;letter-spacing:2px;color:#ff6b00">PINNED</span>'
                '<strong>' + _p.get("title","") + '</strong>'
                '<span style="color:#aa6622">' + _p.get("body","")[:120] + '</span>'
                '</div>'
            )
    except:
        pass
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — TriptokForge</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600&display=swap" rel="stylesheet">
<style>
:root{{--black:#020408;--deep:#060d18;--panel:#0a1628;--border:#1a3a5c;--accent:#00d4ff;--accent2:#ff6b00;--text:#c8dff0;--dim:#4a6a8a}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--black);color:var(--text);font-family:'Rajdhani',sans-serif;min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,212,255,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,.03) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}}
.page{{position:relative;z-index:1;max-width:1200px;margin:0 auto;padding:88px 40px 120px}}
h1{{font-family:'Orbitron',monospace;font-size:clamp(22px,3vw,36px);font-weight:900;color:#fff;margin-bottom:8px}}
.sub{{color:var(--dim);font-size:16px;margin-bottom:40px;line-height:1.6}}
.tag{{font-size:11px;letter-spacing:4px;text-transform:uppercase;color:var(--accent);margin-bottom:14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}}
.card{{background:var(--panel);border:1px solid var(--border);padding:28px;transition:border-color .2s}}
.card:hover{{border-color:var(--accent)}}
.card h3{{font-family:'Orbitron',monospace;font-size:13px;font-weight:700;color:#fff;margin-bottom:10px;letter-spacing:1px}}
.card p{{color:var(--dim);font-size:14px;line-height:1.6}}
.btn{{display:inline-flex;align-items:center;gap:8px;font-family:'Orbitron',monospace;font-size:11px;font-weight:700;
      letter-spacing:2px;text-transform:uppercase;padding:11px 24px;text-decoration:none;transition:all .2s;border:none;cursor:pointer}}
.btn-p{{background:var(--accent);color:var(--black)}}.btn-p:hover{{background:#fff}}
.btn-o{{background:transparent;color:var(--text);border:1px solid var(--border)}}.btn-o:hover{{border-color:var(--accent);color:var(--accent)}}
.coming{{display:inline-block;padding:4px 12px;background:rgba(255,107,0,.1);border:1px solid rgba(255,107,0,.3);
         color:var(--accent2);font-family:'Orbitron',monospace;font-size:9px;letter-spacing:2px;margin-bottom:20px}}

/* ── Persistent Player ── */
#tf-player{{
  position:fixed;bottom:0;left:0;right:0;z-index:999;
  background:rgba(6,13,24,0.97);
  border-top:1px solid var(--border);
  backdrop-filter:blur(20px);
  display:flex;align-items:center;gap:0;
  height:64px;
  transform:translateY(100%);
  transition:transform 0.35s cubic-bezier(0.4,0,0.2,1);
}}
#tf-player.visible{{transform:translateY(0)}}
#tf-player.expanded{{height:auto;flex-direction:column;padding-bottom:0}}

/* left — track info */
.tfp-info{{
  display:flex;align-items:center;gap:14px;
  padding:0 20px;min-width:220px;flex:1;
  border-right:1px solid var(--border);height:64px;
}}
.tfp-icon{{
  width:36px;height:36px;background:var(--panel);border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  font-size:14px;position:relative;overflow:hidden;
}}
.tfp-icon::after{{
  content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(0,212,255,0.2),transparent);
}}
.tfp-bars{{display:flex;align-items:flex-end;gap:2px;height:18px}}
.tfp-bars span{{width:3px;background:var(--accent);border-radius:1px;animation:tfbar 0.8s ease-in-out infinite alternate}}
.tfp-bars span:nth-child(2){{animation-delay:0.15s;height:60%}}
.tfp-bars span:nth-child(3){{animation-delay:0.3s;height:90%}}
.tfp-bars span:nth-child(4){{animation-delay:0.1s;height:40%}}
.tfp-bars span:nth-child(5){{animation-delay:0.25s;height:75%}}
@keyframes tfbar{{from{{transform:scaleY(0.3)}}to{{transform:scaleY(1)}}}}
.tfp-bars.paused span{{animation-play-state:paused}}
.tfp-name{{font-family:'Orbitron',monospace;font-size:10px;font-weight:700;color:#fff;letter-spacing:1px;
           white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px}}
.tfp-meta{{font-size:11px;color:var(--dim);letter-spacing:1px;margin-top:2px}}

/* center — controls */
.tfp-controls{{
  display:flex;align-items:center;gap:8px;
  padding:0 24px;height:64px;
}}
.tfp-btn{{
  width:32px;height:32px;border:1px solid var(--border);background:transparent;
  color:var(--text);cursor:pointer;display:flex;align-items:center;justify-content:center;
  font-size:13px;transition:all 0.2s;flex-shrink:0;
}}
.tfp-btn:hover{{border-color:var(--accent);color:var(--accent)}}
.tfp-btn.play{{
  width:40px;height:40px;background:var(--accent);color:var(--black);
  border-color:var(--accent);font-size:15px;
}}
.tfp-btn.play:hover{{background:#fff;border-color:#fff}}

/* progress bar */
.tfp-progress-wrap{{
  flex:1;display:flex;align-items:center;gap:10px;
  padding:0 16px;height:64px;min-width:0;
}}
.tfp-time{{font-family:'Orbitron',monospace;font-size:9px;color:var(--dim);flex-shrink:0;letter-spacing:1px}}
.tfp-bar{{flex:1;height:3px;background:var(--border);cursor:pointer;position:relative}}
.tfp-bar-fill{{height:100%;background:var(--accent);width:0%;transition:width 0.25s linear;pointer-events:none}}
.tfp-bar:hover .tfp-bar-fill{{background:#fff}}

/* right — volume + track picker toggle */
.tfp-right{{
  display:flex;align-items:center;gap:10px;
  padding:0 16px;height:64px;border-left:1px solid var(--border);
}}
.tfp-vol{{width:72px;height:3px;background:var(--border);cursor:pointer;position:relative}}
.tfp-vol-fill{{height:100%;background:var(--accent);width:80%;pointer-events:none}}
.tfp-toggle{{
  font-family:'Orbitron',monospace;font-size:9px;letter-spacing:1px;color:var(--dim);
  background:transparent;border:1px solid var(--border);padding:5px 10px;cursor:pointer;
  transition:all 0.2s;white-space:nowrap;
}}
.tfp-toggle:hover{{border-color:var(--accent);color:var(--accent)}}
.tfp-close{{
  width:28px;height:28px;background:transparent;border:none;color:var(--dim);
  cursor:pointer;font-size:16px;padding:0;transition:color 0.2s;
}}
.tfp-close:hover{{color:#fff}}

/* track list drawer */
.tfp-drawer{{
  width:100%;border-top:1px solid var(--border);
  background:rgba(6,13,24,0.99);
  max-height:0;overflow:hidden;
  transition:max-height 0.3s ease;
}}
.tfp-drawer.open{{max-height:240px;overflow-y:auto}}
.tfp-track{{
  display:flex;align-items:center;gap:14px;
  padding:10px 20px;cursor:pointer;
  border-bottom:1px solid rgba(26,58,92,0.4);
  transition:background 0.15s;
}}
.tfp-track:hover{{background:rgba(0,212,255,0.05)}}
.tfp-track.active{{background:rgba(0,212,255,0.08);border-left:2px solid var(--accent)}}
.tfp-track-name{{font-family:'Orbitron',monospace;font-size:10px;color:#fff;letter-spacing:0.5px;
                 flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tfp-track-size{{font-size:11px;color:var(--dim)}}
.tfp-empty{{padding:20px;text-align:center;color:var(--dim);font-size:13px;font-family:'Orbitron',monospace;letter-spacing:1px}}
</style></head><body>
{nav}
{_pinned_banner}
<div class="page">{content}</div>

<!-- ═══════════════════════════════════════════════════ -->
<!-- PERSISTENT GLOBAL PLAYER                           -->
<!-- ═══════════════════════════════════════════════════ -->
<div id="tf-player">
  <!-- Info -->
  <div class="tfp-info">
    <div class="tfp-icon">
      <div class="tfp-bars" id="tfp-bars">
        <span style="height:50%"></span><span></span><span></span><span></span><span></span>
      </div>
    </div>
    <div>
      <div class="tfp-name" id="tfp-name">NO TRACK</div>
      <div class="tfp-meta" id="tfp-meta">SELECT A TRACK</div>
    </div>
  </div>

  <!-- Controls -->
  <div class="tfp-controls">
    <button class="tfp-btn" id="tfp-prev" title="Previous">&#9664;&#9664;</button>
    <button class="tfp-btn play" id="tfp-play" title="Play/Pause">&#9654;</button>
    <button class="tfp-btn" id="tfp-next" title="Next">&#9654;&#9654;</button>
  </div>

  <!-- Progress -->
  <div class="tfp-progress-wrap">
    <span class="tfp-time" id="tfp-cur">0:00</span>
    <div class="tfp-bar" id="tfp-bar"><div class="tfp-bar-fill" id="tfp-fill"></div></div>
    <span class="tfp-time" id="tfp-dur">0:00</span>
  </div>

  <!-- Right -->
  <div class="tfp-right">
    <div class="tfp-vol" id="tfp-vol" title="Volume"><div class="tfp-vol-fill" id="tfp-vfill"></div></div>
    <button class="tfp-toggle" id="tfp-toggle">&#9835; TRACKS</button>
    <button class="tfp-close" id="tfp-close" title="Close">&#215;</button>
  </div>

  <!-- Track drawer -->
  <div class="tfp-drawer" id="tfp-drawer">
    <div class="tfp-empty" id="tfp-empty">Loading tracks...</div>
  </div>
</div>

<audio id="tfp-audio" preload="none"></audio>

<script>
(function(){{
  const audio   = document.getElementById('tfp-audio');
  const player  = document.getElementById('tf-player');
  const bars    = document.getElementById('tfp-bars');
  const nameEl  = document.getElementById('tfp-name');
  const metaEl  = document.getElementById('tfp-meta');
  const playBtn = document.getElementById('tfp-play');
  const prevBtn = document.getElementById('tfp-prev');
  const nextBtn = document.getElementById('tfp-next');
  const fill    = document.getElementById('tfp-fill');
  const curEl   = document.getElementById('tfp-cur');
  const durEl   = document.getElementById('tfp-dur');
  const bar     = document.getElementById('tfp-bar');
  const volBar  = document.getElementById('tfp-vol');
  const vfill   = document.getElementById('tfp-vfill');
  const toggle  = document.getElementById('tfp-toggle');
  const drawer  = document.getElementById('tfp-drawer');
  const closeBtn= document.getElementById('tfp-close');
  const emptyEl = document.getElementById('tfp-empty');

  let tracks = [];
  let current = -1;
  let drawerOpen = false;
  let vol = 0.8;

  // ── Restore state from sessionStorage ──
  try {{
    const saved = JSON.parse(sessionStorage.getItem('tfp') || '{{}}');
    if (saved.vol !== undefined) vol = saved.vol;
    audio.volume = vol;
    vfill.style.width = (vol * 100) + '%';
  }} catch(e) {{}}

  function fmt(s) {{
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s/60), ss = Math.floor(s%60);
    return m + ':' + String(ss).padStart(2,'0');
  }}

  function saveState() {{
    try {{
      sessionStorage.setItem('tfp', JSON.stringify({{
        current, vol, filename: tracks[current]?.filename || '', time: audio.currentTime
      }}));
    }} catch(e) {{}}
  }}

  // ── Load tracks from server ──
  async function loadTracks() {{
    try {{
      const r = await fetch('/audio/list');
      const d = await r.json();
      tracks = d.files || [];
      renderDrawer();
      // Restore last playing track
      try {{
        const saved = JSON.parse(sessionStorage.getItem('tfp') || '{{}}');
        if (saved.filename) {{
          const idx = tracks.findIndex(t => t.filename === saved.filename);
          if (idx >= 0) {{
            current = idx;
            setTrack(idx, false);
            if (saved.time) audio.currentTime = saved.time;
            player.classList.add('visible');
          }}
        }}
      }} catch(e) {{}}
      if (tracks.length > 0 && current < 0) {{
        player.classList.add('visible');
      }}
    }} catch(e) {{
      emptyEl.textContent = 'Could not load tracks.';
    }}
  }}

  function renderDrawer() {{
    if (!tracks.length) {{
      emptyEl.textContent = 'No tracks uploaded yet. Visit Island Forge to upload audio.';
      emptyEl.style.display = 'block';
      return;
    }}
    emptyEl.style.display = 'none';
    // Remove old track rows
    drawer.querySelectorAll('.tfp-track').forEach(el => el.remove());
    tracks.forEach((t, i) => {{
      const row = document.createElement('div');
      row.className = 'tfp-track' + (i === current ? ' active' : '');
      row.innerHTML = `<div class="tfp-track-name">${{t.filename}}</div><div class="tfp-track-size">${{t.size_kb}} KB</div>`;
      row.addEventListener('click', () => {{ setTrack(i, true); }});
      drawer.appendChild(row);
    }});
  }}

  function setTrack(idx, autoplay) {{
    current = idx;
    const t = tracks[idx];
    if (!t) return;
    const src = '/audio/stream/' + encodeURIComponent(t.filename);
    audio.src = src;
    const label = t.filename.replace(/\.[^.]+$/, '').replace(/_/g,' ').toUpperCase();
    nameEl.textContent = label.length > 22 ? label.slice(0,22) + '…' : label;
    metaEl.textContent = t.size_kb + ' KB  ·  TRIPTOKFORGE';
    fill.style.width = '0%';
    curEl.textContent = '0:00';
    durEl.textContent = '0:00';
    renderDrawer();
    player.classList.add('visible');
    if (autoplay) {{ audio.play(); }}
    saveState();
  }}

  // ── Play/Pause ──
  playBtn.addEventListener('click', () => {{
    if (!audio.src) {{
      if (tracks.length > 0) setTrack(0, true);
      return;
    }}
    if (audio.paused) audio.play(); else audio.pause();
  }});

  audio.addEventListener('play', () => {{
    playBtn.innerHTML = '&#9646;&#9646;';
    bars.classList.remove('paused');
  }});
  audio.addEventListener('pause', () => {{
    playBtn.innerHTML = '&#9654;';
    bars.classList.add('paused');
  }});
  audio.addEventListener('ended', () => {{
    if (current < tracks.length - 1) setTrack(current + 1, true);
    else {{ playBtn.innerHTML = '&#9654;'; bars.classList.add('paused'); }}
  }});

  // ── Progress ──
  audio.addEventListener('timeupdate', () => {{
    if (!audio.duration) return;
    const pct = (audio.currentTime / audio.duration) * 100;
    fill.style.width = pct + '%';
    curEl.textContent = fmt(audio.currentTime);
    durEl.textContent = fmt(audio.duration);
    saveState();
  }});

  bar.addEventListener('click', e => {{
    if (!audio.duration) return;
    const rect = bar.getBoundingClientRect();
    audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
  }});

  // ── Prev / Next ──
  prevBtn.addEventListener('click', () => {{
    if (audio.currentTime > 3) {{ audio.currentTime = 0; return; }}
    if (current > 0) setTrack(current - 1, !audio.paused);
  }});
  nextBtn.addEventListener('click', () => {{
    if (current < tracks.length - 1) setTrack(current + 1, !audio.paused);
  }});

  // ── Volume ──
  volBar.addEventListener('click', e => {{
    const rect = volBar.getBoundingClientRect();
    vol = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    audio.volume = vol;
    vfill.style.width = (vol * 100) + '%';
    saveState();
  }});

  // ── Drawer toggle ──
  toggle.addEventListener('click', () => {{
    drawerOpen = !drawerOpen;
    drawer.classList.toggle('open', drawerOpen);
    player.classList.toggle('expanded', drawerOpen);
    toggle.textContent = drawerOpen ? '✕ CLOSE' : '♫ TRACKS';
  }});

  // ── Close player ──
  closeBtn.addEventListener('click', () => {{
    audio.pause();
    player.classList.remove('visible');
    saveState();
  }});

  // ── Init ──
  loadTracks();
  // Refresh track list every 30s in case new uploads happen
  setInterval(loadTracks, 30000);
}})();
</script>
</body></html>"""


@app.route("/gallery")
def gallery():
    # Try Oracle DB first, fall back to disk
    islands = []
    try:
        rows = get_recent_islands(limit=24)
        for r in rows:
            seed = str(r.get("seed", ""))
            preview_url = r.get("preview_url", "")
            layout_url  = r.get("layout_url", "")
            creator     = r.get("creator_id", "anonymous")
            world_size  = r.get("world_size_cm", 0)
            preview_src = preview_url if preview_url else f"/outputs/island_{seed}_preview.png"
            layout_href = layout_url  if layout_url  else (f"/outputs/island_{seed}_layout.json" if os.path.exists(os.path.join(OUTPUT_DIR, f"island_{seed}_layout.json")) else "")
            islands.append({"seed": seed, "preview_src": preview_src,
                            "layout_href": layout_href, "creator": creator, "world_size": world_size})
    except Exception as e:
        print(f"[gallery] DB query failed, using disk: {e}")

    if not islands:
        if os.path.exists(OUTPUT_DIR):
            for fn in sorted(os.listdir(OUTPUT_DIR)):
                if fn.endswith("_preview.png"):
                    seed = fn.replace("_preview.png","").replace("island_","")
                    has_layout = os.path.exists(os.path.join(OUTPUT_DIR, f"island_{seed}_layout.json"))
                    islands.append({
                        "seed": seed,
                        "preview_src": f"/outputs/{fn}",
                        "layout_href": f"/outputs/island_{seed}_layout.json" if has_layout else "",
                        "creator": "", "world_size": 0,
                    })

    cards = ""
    if islands:
        for isl in islands:
            size_label    = f"{isl['world_size']:,} cm" if isl.get("world_size") else ""
            creator_label = isl.get("creator","")[:16] if isl.get("creator","") not in ("anonymous","local","","") else ""
            meta = " · ".join(filter(None, [size_label, creator_label]))
            cards += f"""
            <div class="card">
              <img src="{isl['preview_src']}" style="width:100%;aspect-ratio:1;object-fit:cover;margin-bottom:14px;image-rendering:pixelated"
                   onerror="this.style.background='var(--panel)';this.style.minHeight='120px';this.removeAttribute('src')">
              <h3>SEED #{isl['seed']}</h3>
              {f'<p style="color:var(--dim);font-size:12px;margin-bottom:10px">{meta}</p>' if meta else ''}
              <div style="display:flex;gap:8px;flex-wrap:wrap">
                <a href="{isl['preview_src']}" download class="btn btn-o" style="font-size:9px;padding:7px 14px">&#11015; Preview</a>
                {f'<a href="{isl['layout_href']}" download class="btn btn-o" style="font-size:9px;padding:7px 14px">&#11015; Layout</a>' if isl.get("layout_href") else ''}
              </div>
            </div>"""
    else:
        cards = '<div class="sub">No islands generated yet. <a href="/forge" style="color:var(--accent)">Open Island Forge →</a></div>'

    content = f"""
    <div class="tag">// Island Gallery</div>
    <h1>Generated Islands</h1>
    <p class="sub">All islands generated by the community. Download heightmaps and layout JSON for UEFN import.</p>
    <div class="grid">{cards}</div>"""
    return _shell("Gallery", content, user=session.get("user"))


@app.route("/outputs/<filename>")
def serve_output(filename):
    """Serve generated output files (previews, heightmaps, layouts)."""
    path = os.path.join(OUTPUT_DIR, os.path.basename(filename))
    if not os.path.exists(path):
        return "Not found", 404
    return send_file(path)


@app.route("/feed")
def feed():
    # ── Latest islands from DB ──
    island_cards = ""
    try:
        recent = get_recent_islands(limit=6)
        for r in recent:
            seed        = str(r.get("seed",""))
            preview_src = r.get("preview_url","") or f"/outputs/island_{seed}_preview.png"
            layout_href = r.get("layout_url","") or f"/outputs/island_{seed}_layout.json"
            creator     = r.get("creator_id","anonymous")[:16]
            world_size  = f"{r.get('world_size_cm',0):,} cm" if r.get("world_size_cm") else ""
            island_cards += f'''
            <div class="card" style="display:flex;gap:14px;align-items:flex-start;padding:16px 20px">
              <img src="{preview_src}" style="width:64px;height:64px;object-fit:cover;image-rendering:pixelated;flex-shrink:0;border:1px solid var(--border)"
                   onerror="this.style.display='none'">
              <div style="flex:1;min-width:0">
                <div style="font-family:'Orbitron',monospace;font-size:11px;color:#fff;margin-bottom:4px">SEED #{seed}</div>
                <div style="font-size:12px;color:var(--dim)">{world_size}{" · " + creator if creator not in ("anonymous","") else ""}</div>
                <div style="display:flex;gap:8px;margin-top:8px">
                  <a href="{preview_src}" download class="btn btn-o" style="font-size:9px;padding:5px 10px">&#11015; PNG</a>
                  <a href="{layout_href}" download class="btn btn-o" style="font-size:9px;padding:5px 10px">&#11015; JSON</a>
                </div>
              </div>
            </div>'''
    except Exception as e:
        island_cards = f'<p class="sub">Could not load islands: {e}</p>'

    if not island_cards:
        island_cards = '<p class="sub">No islands yet. <a href="/forge" style="color:var(--accent)">Be the first →</a></p>'

    # ── Latest announcements from DB ──
    ann_html = ""
    try:
        anns = get_announcements()
        for a in anns[:4]:
            ann_html += f'''
            <div class="card">
              <h3>{a.get("title","")}</h3>
              <p style="margin-top:8px">{a.get("body","")}</p>
              <p style="color:var(--dim);font-size:11px;margin-top:10px;font-family:monospace">{a.get("posted_by","")}</p>
            </div>'''
    except:
        pass

    if not ann_html:
        ann_html = '<div class="card"><h3>NO ANNOUNCEMENTS</h3><p>Check back soon.</p></div>'

    content = f"""
    <div class="tag">// Community Feed</div>
    <h1>Latest Activity</h1>
    <p class="sub">Recent islands from the community and platform announcements.</p>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:40px">
      <div>
        <div style="font-family:'Orbitron',monospace;font-size:11px;letter-spacing:2px;color:var(--accent);margin-bottom:12px">// RECENT ISLANDS</div>
        <div style="display:flex;flex-direction:column;gap:2px;background:var(--border);border:1px solid var(--border)">{island_cards}</div>
        <div style="margin-top:12px"><a href="/gallery" class="btn btn-o" style="font-size:10px">View All Islands →</a></div>
      </div>
      <div>
        <div style="font-family:'Orbitron',monospace;font-size:11px;letter-spacing:2px;color:var(--accent);margin-bottom:12px">// ANNOUNCEMENTS</div>
        <div class="grid" style="grid-template-columns:1fr">{ann_html}</div>
      </div>
    </div>

    <div class="grid">
      <div class="card"><h3>FNCS RESULTS</h3><p>Fortnite Champion Series standings and VODs. <span style="color:var(--accent2);font-size:11px">COMING SOON</span></p></div>
      <div class="card"><h3>MAP UPDATES</h3><p>Season patch notes and POI breakdowns. <span style="color:var(--accent2);font-size:11px">COMING SOON</span></p></div>
    </div>"""
    return _shell("Feed", content, user=session.get("user"))


@app.route("/jukebox")
def jukebox():
    tracks = []
    try:
        db_tracks = get_audio_tracks()
        for t in db_tracks:
            fn = t.get("filename","")
            tracks.append({
                "title": fn,
                "artist": t.get("uploader_id","Member")[:16],
                "url": f"/audio/stream/{fn}",
                "bpm": round(t.get("tempo_bpm", 0)) if t.get("tempo_bpm") else 0,
            })
    except Exception as e:
        print(f"[jukebox] DB error, using disk: {e}")
        if os.path.exists(AUDIO_DIR):
            for fn in sorted(os.listdir(AUDIO_DIR)):
                if os.path.splitext(fn)[1].lower() in SUPPORTED_EXTS:
                    tracks.append({"title": fn, "artist": "Upload", "url": f"/audio/stream/{fn}", "bpm": 0})

    track_html = ""
    for i, t in enumerate(tracks):
        label = t["title"].replace("_"," ").rsplit(".",1)[0].upper()
        bpm_badge = f'<span style="font-family:Orbitron,monospace;font-size:9px;color:var(--accent);letter-spacing:1px">{t["bpm"]} BPM</span>' if t.get("bpm") else ""
        track_html += (
            f'<div class="card" style="display:flex;align-items:center;gap:16px;padding:14px 20px;cursor:pointer" ' +
            f'onclick="jkPlay({i})" id="jkrow-{i}">' +
            '<div style="width:34px;height:34px;background:rgba(0,212,255,.06);border:1px solid var(--border);' +
            'display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;color:var(--accent)">&#9654;</div>' +
            '<div style="flex:1;min-width:0">' +
            f'<div style="font-family:Orbitron,monospace;font-size:11px;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</div>' +
            f'<div style="font-size:11px;color:var(--dim);margin-top:3px;display:flex;gap:10px;align-items:center"><span>{t.get("artist","")}</span>{bpm_badge}</div>' +
            '</div></div>'
        )

    if not track_html:
        track_html = '<p class="sub">No tracks yet. <a href="/forge" style="color:var(--accent)">Upload audio in Island Forge</a></p>'

    import json as _json
    import json as _json
    track_urls_js   = _json.dumps([t["url"] for t in tracks])
    track_titles_js = _json.dumps([t["title"].replace("'","") for t in tracks])

    track_list_html = f'<div class="grid" style="grid-template-columns:1fr">{track_html}</div>'

    content = f"""
    <div class="tag">// Jukebox</div>
    <h1>Community Jukebox</h1>
    <p class="sub">{len(tracks)} tracks &middot; Click any track to play</p>
    <div id="jk-now" style="display:none;margin-bottom:20px;padding:12px 20px;background:var(--panel);
         border:1px solid var(--accent);font-family:'Orbitron',monospace;font-size:11px;color:var(--accent);
         align-items:center;gap:12px">
      &#9654; <span id="jk-title" style="flex:1">&#8212;</span>
      <button onclick="document.getElementById('jk-a').pause();document.getElementById('jk-now').style.display='none'"
              style="background:none;border:none;color:var(--dim);cursor:pointer;font-size:16px">&#9646;</button>
    </div>
    <audio id="jk-a"></audio>
    {track_list_html}
    <script>
    const jkU={track_urls_js};
    const jkT={track_titles_js};
    let jkC=-1;
    function jkPlay(i){{
      jkC=i;
      const a=document.getElementById("jk-a");
      a.src=jkU[i]; a.play();
      document.getElementById("jk-title").textContent=jkT[i];
      document.getElementById("jk-now").style.display="flex";
      document.querySelectorAll("[id^=jkrow-]").forEach((el,j)=>{{
        el.style.borderColor = j===i ? "var(--accent)" : "";
      }});
    }}
    </script>"""
    return _shell("Jukebox", content, user=session.get("user"))

@app.route("/community")
def community():
    members = []
    announcements = []
    try:
        members = get_all_members()
    except Exception as e:
        print(f"[community] members DB error: {e}")
    try:
        announcements = get_announcements()
    except Exception as e:
        print(f"[community] announcements DB error: {e}")

    ann_html = ""
    for a in (announcements or [])[:5]:
        pinned = a.get("pinned", False)
        ann_html += (
            '<div class="card" style="margin-bottom:12px' +
            (';border-color:var(--accent2)' if pinned else '') + '">' +
            ('<span style="font-size:9px;color:var(--accent2);letter-spacing:2px;font-family:Orbitron,monospace">PINNED</span><br>' if pinned else '') +
            '<h3>' + a.get("title","Announcement") + '</h3>' +
            '<p style="margin-bottom:8px;margin-top:6px">' + a.get("body","") + '</p>' +
            '<span style="font-size:11px;color:var(--dim)">' + a.get("posted_by","") + '</span>' +
            '</div>'
        )

    mem_html = ""
    for m in (members or [])[:24]:
        skin_img = m.get("skin_img","")
        name = m.get("display_name", m.get("name","Member"))
        avatar = m.get("avatar_url","")
        img_src = skin_img or avatar or ""
        initials = name[:2].upper() if name else "??"
        img_tag = ('<img src="' + img_src + '" style="width:100%;height:100%;object-fit:cover" onerror="this.style.display=\'none\'">') if img_src else ''
        mem_html += (
            '<div class="card" style="display:flex;align-items:center;gap:12px;padding:14px 16px">' +
            '<div style="width:44px;height:44px;border-radius:4px;background:rgba(0,212,255,.06);' +
            'border:1px solid var(--border);display:flex;align-items:center;justify-content:center;' +
            'font-size:11px;flex-shrink:0;overflow:hidden;font-family:Orbitron,monospace;color:var(--accent)">' +
            img_tag + (initials if not img_src else '') + '</div>' +
            '<div style="flex:1;min-width:0">' +
            '<div style="font-family:Orbitron,monospace;font-size:11px;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + name + '</div>' +
            '<div style="font-size:11px;color:var(--dim);margin-top:2px">' + (m.get("skin_name","") or "Member") + '</div>' +
            '</div></div>'
        )

    if not mem_html:
        mem_html = '<p style="color:var(--dim);font-size:14px">No members yet. <a href="/auth/epic" style="color:var(--accent)">Connect your Epic account</a>.</p>'

    n_mem = len(members)
    n_ann = len(announcements)
    content = (
        '<div class="tag">// Community</div>' +
        '<h1>TriptokForge Community</h1>' +
        f'<p class="sub">{n_mem} members · {n_ann} announcements</p>' +
        '<div style="display:grid;grid-template-columns:1fr 320px;gap:32px;align-items:start">' +
        '<div>' +
        '<div style="font-family:Orbitron,monospace;font-size:10px;letter-spacing:2px;color:var(--dim);margin-bottom:14px">// ANNOUNCEMENTS</div>' +
        (ann_html or '<p style="color:var(--dim);font-size:14px">No announcements yet.</p>') +
        '</div>' +
        f'<div><div style="font-family:Orbitron,monospace;font-size:10px;letter-spacing:2px;color:var(--dim);margin-bottom:14px">// MEMBERS ({n_mem})</div>' +
        '<div style="display:flex;flex-direction:column;gap:4px">' + mem_html + '</div></div>' +
        '</div>'
    )
    return _shell("Community", content, user=session.get("user"))


@app.route("/dev")
def dev():
    content = """
    <div class="tag">// Developer Library</div>
    <h1>Verse & UEFN Resources</h1>
    <p class="sub">Reference docs, patterns, and code snippets for building on TriptokForge and UEFN.</p>
    <div class="grid">
      <div class="card">
        <h3>ISLAND FORGE API</h3>
        <p style="margin-bottom:14px">POST /generate — returns heightmap, layout JSON, and biome stats. Accepts seed, size, world_size, and audio weights.</p>
        <code style="display:block;background:var(--black);padding:12px;font-size:11px;color:var(--accent);border:1px solid var(--border);font-family:monospace;white-space:pre-wrap">POST /generate
{
  "seed": 42,
  "size": 2017,
  "world_size": "double_br",
  "plots": 32,
  "weights": { ... }
}</code>
      </div>
      <div class="card">
        <h3>VERSE PATTERNS</h3>
        <p style="margin-bottom:14px">Battle-tested Verse code patterns from the TriptokForge RPG system.</p>
        <code style="display:block;background:var(--black);padding:12px;font-size:11px;color:var(--accent);border:1px solid var(--border);font-family:monospace;white-space:pre-wrap"># AgentEntersEvent
OnEnter(Agent:agent):void=
  if(P:=player[Agent]):
    HandlePlayer(P)

# weak_map per-player state
var Flags:weak_map(player,logic)=map{}</code>
      </div>
      <div class="card">
        <h3>WORLD SIZE PRESETS</h3>
        <p style="margin-bottom:14px">Reference for world_size values and their UEFN requirements.</p>
        <code style="display:block;background:var(--black);padding:12px;font-size:11px;color:var(--accent);border:1px solid var(--border);font-family:monospace;white-space:pre-wrap">uefn_small   →    50,000 cm
uefn_max     →   100,000 cm
br_chapter2  →   550,000 cm
double_br    → 1,100,000 cm ←default
skyrim       → 3,700,000 cm
gta5         → 8,100,000 cm</code>
      </div>
      <div class="card">
        <h3>UEFN HEIGHTMAP IMPORT</h3>
        <p>16-bit PNG, R16 format. Import via Landscape Mode → Import from File. Coordinate origin is map center. World cm values in layout.json match UEFN world origin.</p>
      </div>
      <div class="card">
        <h3>GITHUB</h3>
        <p style="margin-bottom:16px">Source code, Verse files, and issue tracker.</p>
        <a href="https://github.com/iamjedi888/ver-perlinforge" target="_blank" class="btn btn-o">View on GitHub →</a>
      </div>
      <div class="card">
        <h3>BOOT ORDER</h3>
        <p style="margin-bottom:14px">Required device init sequence for the RPG system.</p>
        <code style="display:block;background:var(--black);padding:12px;font-size:11px;color:var(--accent);border:1px solid var(--border);font-family:monospace;white-space:pre-wrap">1. plot_registry
2. zone_manager
3. world_generator   (Sleep 1.0)
4. farm_populator    (Sleep 0.5)
5. npc_director      (Sleep 1.5)
6. biome_manager
7. world_wrap_manager</code>
      </div>
    </div>"""
    return _shell("Dev Library", content, user=session.get("user"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "triptokadmin2026")

    # Auth check
    if request.method == "POST" and request.form.get("action") == "login":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
        else:
            return _shell("Admin", '<div style="color:#ff4444;font-family:var(--mono)">Wrong password.</div><br><a href="/admin" style="color:var(--accent)">Try again</a>', user=session.get("user"))

    if not session.get("admin"):
        return _shell("Admin", """
        <div class="tag">// Admin</div>
        <h1>Admin Login</h1>
        <form method="POST" style="max-width:340px">
          <input type="hidden" name="action" value="login">
          <input type="password" name="password" placeholder="Admin password"
                 style="width:100%;background:var(--panel);border:1px solid var(--border);
                        color:var(--text);font-family:monospace;font-size:14px;
                        padding:12px 16px;margin-bottom:12px;outline:none">
          <button type="submit" class="btn btn-p" style="width:100%">LOGIN</button>
        </form>""", user=session.get("user"))

    # Handle admin POST actions
    msg = ""
    if request.method == "POST":
        action = request.form.get("action")
        if action == "announcement":
            title = request.form.get("title","")
            body  = request.form.get("body","")
            date  = request.form.get("date","")
            posted_by = session.get("user",{}).get("display_name","admin")
            # Save to Oracle DB
            try:
                post_announcement(title=title, body=body, posted_by=posted_by)
                msg = "Announcement posted to DB."
            except Exception as db_err:
                print(f"[admin] DB post failed: {db_err}")
                # Fallback to JSON
                ann_path = os.path.join(BASE_DIR, "data", "announcements.json")
                anns = []
                if os.path.exists(ann_path):
                    with open(ann_path) as f: anns = json.load(f)
                anns.append({"title": title, "body": body, "date": date})
                os.makedirs(os.path.join(BASE_DIR,"data"), exist_ok=True)
                with open(ann_path,"w") as f: json.dump(anns, f, indent=2)
                msg = "Announcement posted (local fallback)."
        elif action == "delete_announcement":
            ann_id = request.form.get("ann_id","")
            try:
                from oracle_db import _get_pool
                pool = _get_pool()
                with pool.acquire() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM announcements WHERE id = :id", {"id": int(ann_id)})
                    conn.commit()
                msg = "Announcement deleted."
            except Exception as e:
                msg = f"Delete failed: {e}"
        elif action == "logout_admin":
            session.pop("admin", None)
            return redirect("/admin")

    # Count stats — prefer DB counts
    try:
        n_islands = len(get_recent_islands(limit=999))
    except:
        n_islands = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith("_layout.json")]) if os.path.exists(OUTPUT_DIR) else 0
    try:
        n_audio = len(get_audio_tracks())
    except:
        n_audio = len([f for f in os.listdir(AUDIO_DIR) if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS]) if os.path.exists(AUDIO_DIR) else 0
    try:
        n_members = len(get_all_members())
    except:
        n_members = 0
    try:
        announcements = get_announcements()
        n_announcements = len(announcements)
    except:
        n_announcements = 0
        announcements = []

    ann_rows = ""
    for a in (announcements or [])[:5]:
        ann_rows += f'''<div style="padding:10px 0;border-bottom:1px solid var(--border);font-size:13px">
            <strong style="color:#fff">{a.get("title","")}</strong>
            <span style="color:var(--dim);margin-left:8px;font-size:11px">{a.get("posted_by","")}</span>
            <p style="color:var(--dim);margin-top:4px">{a.get("body","")[:120]}</p>
            </div>'''

    content = f"""
    <div class="tag">// Admin Panel</div>
    <h1>TriptokForge Admin</h1>
    {f'<div style="color:var(--accent);margin-bottom:20px;font-family:monospace">{msg}</div>' if msg else ''}
    <div class="grid" style="margin-bottom:32px">
      <div class="card"><h3>ISLANDS</h3><div style="font-family:'Orbitron',monospace;font-size:36px;color:var(--accent)">{n_islands}</div></div>
      <div class="card"><h3>AUDIO FILES</h3><div style="font-family:'Orbitron',monospace;font-size:36px;color:var(--accent)">{n_audio}</div></div>
      <div class="card"><h3>MEMBERS</h3><div style="font-family:'Orbitron',monospace;font-size:36px;color:var(--accent)">{n_members}</div></div>
      <div class="card"><h3>ANNOUNCEMENTS</h3><div style="font-family:'Orbitron',monospace;font-size:36px;color:var(--accent)">{n_announcements}</div></div>
    </div>
    {f'<div class="card" style="margin-bottom:24px;max-width:560px"><h3 style="margin-bottom:12px">RECENT ANNOUNCEMENTS</h3>{ann_rows}</div>' if ann_rows else ''}
    <div class="card" style="margin-bottom:20px;max-width:560px">
      <h3 style="margin-bottom:16px">POST ANNOUNCEMENT</h3>
      <form method="POST">
        <input type="hidden" name="action" value="announcement">
        <input type="text" name="title" placeholder="Title" required
               style="width:100%;background:var(--black);border:1px solid var(--border);color:var(--text);
                      font-family:monospace;font-size:13px;padding:10px 14px;margin-bottom:10px;outline:none">
        <textarea name="body" placeholder="Body" rows="3" required
                  style="width:100%;background:var(--black);border:1px solid var(--border);color:var(--text);
                         font-family:monospace;font-size:13px;padding:10px 14px;margin-bottom:10px;outline:none;resize:vertical"></textarea>
        <input type="text" name="date" placeholder="Date (e.g. March 2026)"
               style="width:100%;background:var(--black);border:1px solid var(--border);color:var(--text);
                      font-family:monospace;font-size:13px;padding:10px 14px;margin-bottom:10px;outline:none">
        <button type="submit" class="btn btn-p">Post</button>
      </form>
    </div>
    <form method="POST">
      <input type="hidden" name="action" value="logout_admin">
      <button type="submit" class="btn btn-o">Logout Admin</button>
    </form>"""
    return _shell("Admin", content, user=session.get("user"))




@app.errorhandler(404)
def not_found(e):
    path = os.path.join(BASE_DIR, "404.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), 404
    return "<h1>404</h1>", 404

@app.errorhandler(500)
def server_error(e):
    return _shell("Error", '<div class="tag">// Error 500</div><h1>Something Broke</h1><p class="sub">An internal error occurred.</p><a href="/home" class="btn btn-o">Back Home</a>'), 500

# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

# Init Oracle schema on startup (safe no-op if DB not configured)
try:
    init_schema()
except Exception as _e:
    print(f"[startup] DB schema init skipped: {_e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"""
  ╔══════════════════════════════════════╗
  ║   TriptokForge Platform v3.0         ║
  ║   https://triptokforge.org           ║
  ╚══════════════════════════════════════╝
  Island Forge + Epic OAuth + Oracle DB
""")
    app.run(host="0.0.0.0", port=port, debug=False)
