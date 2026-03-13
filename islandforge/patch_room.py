#!/usr/bin/env python3
"""
patch_room.py  — Phase 1: Card Wall Room
Run on VM: python3 ~/ver-perlinforge/islandforge/patch_room.py

Adds:
  - templates/room.html           (cyberpunk 3D card wall)
  - routes/room.py                (/room  /api/set_room_theme)
  - oracle_db.py additions        (get_member_room, set_room_theme, get_member_tickets)
  - server.py                     registers room_bp
"""
import os, subprocess, time, shutil

ROOT      = "/home/ubuntu/ver-perlinforge/islandforge"
ROUTES    = os.path.join(ROOT, "routes")
TEMPLATES = os.path.join(ROOT, "templates")

# ══════════════════════════════════════════════════════════════
# 1. Copy room.html from scripts dir (was pushed with git)
# ══════════════════════════════════════════════════════════════
# The template is committed alongside this patch script
src_html = os.path.join(ROOT, "room.html")
dst_html = os.path.join(TEMPLATES, "room.html")
if os.path.exists(src_html):
    shutil.copy2(src_html, dst_html)
    print("✓ templates/room.html — copied")
else:
    print("⚠ room.html not found next to patch script — skipping copy")

# ══════════════════════════════════════════════════════════════
# 2. routes/room.py
# ══════════════════════════════════════════════════════════════
open(os.path.join(ROUTES, "room.py"), "w").write('''"""
routes/room.py — /room  card wall + theme API
"""
import os
from flask import Blueprint, render_template, session, redirect, request, jsonify

room_bp = Blueprint("room", __name__)

try:
    from oracle_db import (
        get_all_members, get_recent_islands,
        get_member_room, set_room_theme, get_member_tickets,
    )
    ROOM_DB = True
except ImportError:
    ROOM_DB = False
    def get_member_room(epic_id): return {"theme": "", "tickets": 0}
    def set_room_theme(epic_id, theme): pass
    def get_member_tickets(epic_id): return 0

try:
    from oracle_db import get_member_islands
    HAS_ISLANDS = True
except ImportError:
    HAS_ISLANDS = False
    def get_member_islands(epic_id, limit=50): return []

@room_bp.route("/room")
def room():
    user = session.get("user")
    if not user:
        return redirect("/auth/epic")

    epic_id   = user.get("account_id", "")
    name      = user.get("display_name", "Player")
    skin_img  = user.get("skin_img", "")
    wins      = user.get("wins", 0)
    kd        = user.get("kd", 0.0)

    # Room data
    room_data  = get_member_room(epic_id) if ROOM_DB else {"theme": "", "tickets": 0}
    tickets    = get_member_tickets(epic_id) if ROOM_DB else 0
    room_theme = room_data.get("theme", "") if room_data else ""

    # Islands for this member
    islands = get_member_islands(epic_id, limit=50) if HAS_ISLANDS else []

    return render_template("room.html",
        name=name,
        skin_img=skin_img,
        wins=wins,
        kd=kd,
        tickets=tickets,
        room_theme=room_theme,
        islands=islands,
    )

@room_bp.route("/api/set_room_theme", methods=["POST"])
def api_set_room_theme():
    user = session.get("user")
    if not user:
        return jsonify({"ok": False, "error": "Not logged in"})
    data  = request.get_json(force=True)
    theme = data.get("theme", "")
    allowed = ["", "tokyo", "miami", "marble", "forest", "retro"]
    if theme not in allowed:
        return jsonify({"ok": False, "error": "Invalid theme"})
    if ROOM_DB:
        set_room_theme(user.get("account_id", ""), theme)
    return jsonify({"ok": True, "theme": theme})
''')
print("✓ routes/room.py")

# ══════════════════════════════════════════════════════════════
# 3. oracle_db.py additions
# ══════════════════════════════════════════════════════════════
oracle_path = os.path.join(ROOT, "oracle_db.py")
src = open(oracle_path).read()

additions = '''

# ── ROOM / TICKETS ───────────────────────────────────────────

def get_member_room(epic_id: str) -> dict:
    """Return room settings (theme, tickets) for a member."""
    if not db_available():
        return {"theme": "", "tickets": 0}
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT room_theme, tickets FROM members WHERE epic_id = :1",
                [epic_id]
            )
            row = cur.fetchone()
            if row:
                return {"theme": row[0] or "", "tickets": row[1] or 0}
            return {"theme": "", "tickets": 0}
    except Exception as e:
        _log(f"get_member_room error: {e}")
        return {"theme": "", "tickets": 0}

def set_room_theme(epic_id: str, theme: str) -> bool:
    """Persist chosen room theme for a member."""
    if not db_available():
        return False
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE members SET room_theme = :1 WHERE epic_id = :2",
                [theme, epic_id]
            )
            conn.commit()
        return True
    except Exception as e:
        _log(f"set_room_theme error: {e}")
        return False

def get_member_tickets(epic_id: str) -> int:
    """Return current ticket balance for a member."""
    if not db_available():
        return 0
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tickets FROM members WHERE epic_id = :1", [epic_id])
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0
    except Exception as e:
        _log(f"get_member_tickets error: {e}")
        return 0

def get_member_islands(epic_id: str, limit: int = 50) -> list:
    """Return islands saved by a specific member."""
    if not db_available():
        return []
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT seed, name, dominant_biome, preview_url, stickers
                   FROM island_saves
                   WHERE epic_id = :1
                   ORDER BY created_at DESC
                   FETCH FIRST :2 ROWS ONLY""",
                [epic_id, limit]
            )
            cols = [c[0].lower() for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        _log(f"get_member_islands error: {e}")
        return []

def award_tickets(epic_id: str, amount: int) -> bool:
    """Award tickets to a member (for wins, uploads, etc.)."""
    if not db_available():
        return False
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE members SET tickets = COALESCE(tickets, 0) + :1 WHERE epic_id = :2",
                [amount, epic_id]
            )
            conn.commit()
        return True
    except Exception as e:
        _log(f"award_tickets error: {e}")
        return False
'''

if "get_member_room" not in src:
    src = src.rstrip() + "\n" + additions
    open(oracle_path, "w").write(src)
    print("✓ oracle_db.py — room/ticket functions added")
else:
    print("→ oracle_db.py — room functions already present")

# ══════════════════════════════════════════════════════════════
# 4. Schema migration — add room_theme + tickets columns
# ══════════════════════════════════════════════════════════════
migrate_sql = '''
-- Run once to add room columns
-- Paste into Oracle DB console or run via python

ALTER TABLE members ADD (room_theme VARCHAR2(32) DEFAULT '');
ALTER TABLE members ADD (tickets NUMBER DEFAULT 0);
'''
with open(os.path.join(ROOT, "scripts", "migrate_room.sql"), "w") as f:
    f.write(migrate_sql)
print("✓ scripts/migrate_room.sql — run this in Oracle console once")

# ══════════════════════════════════════════════════════════════
# 5. Register room_bp in server.py
# ══════════════════════════════════════════════════════════════
server_path = os.path.join(ROOT, "server.py")
src = open(server_path).read()
if "room_bp" not in src:
    src = src.replace(
        "from routes.forge      import forge_bp",
        "from routes.forge      import forge_bp\nfrom routes.room       import room_bp"
    )
    src = src.replace(
        "app.register_blueprint(forge_bp)",
        "app.register_blueprint(forge_bp)\napp.register_blueprint(room_bp)"
    )
    open(server_path, "w").write(src)
    print("✓ server.py — room_bp registered")
else:
    print("→ server.py — room_bp already registered")

# ══════════════════════════════════════════════════════════════
# 6. Restart
# ══════════════════════════════════════════════════════════════
print("\n▸ Restarting...")
subprocess.run(["sudo", "systemctl", "restart", "islandforge"], check=True)
time.sleep(5)

for path in ["/room", "/health"]:
    r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}",
                        f"http://127.0.0.1:5000{path}"], capture_output=True, text=True)
    print(f"  {path:20s} → {r.stdout}")

print("""
✅ Phase 1 — Card Wall Room live!

Next steps:
  1. Run migrate_room.sql in Oracle console to add room_theme + tickets columns
     ALTER TABLE members ADD (room_theme VARCHAR2(32) DEFAULT '');
     ALTER TABLE members ADD (tickets NUMBER DEFAULT 0);

  2. Visit triptokforge.org/room when logged in with Epic
  3. Try the room theme switcher (bottom-right)
  4. Forge an island to populate your wall
""")
