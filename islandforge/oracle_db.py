"""
oracle_db.py — TriptokForge Oracle Autonomous Database Layer
=============================================================
Handles all persistent storage via Oracle Autonomous DB (Always Free).
Falls back gracefully to JSON files if DB is not configured.

CONNECTION:
  Set environment variables:
    ORACLE_DSN      = your_db_name_high   (from wallet tnsnames.ora)
    ORACLE_USER     = ADMIN  (or a dedicated user)
    ORACLE_PASSWORD = YourSecurePassword123!
    ORACLE_WALLET   = /home/ubuntu/wallet  (path to unzipped wallet folder)

TABLES:
  DB1 (Transaction Processing) — members, sessions, audio metadata
    members        — Epic OAuth user profiles
    audio_tracks   — uploaded track metadata + weights
    jukebox        — community jukebox queue
    announcements  — admin announcements
    island_saves   — saved island metadata (no binary blobs)

  DB2 (JSON/APEX) — optional second DB for island data
    (not implemented yet — extend as needed)

OBJECT STORAGE (OCI):
  Audio files, heightmap PNGs, preview PNGs → OCI Object Storage
  Configure via:
    OCI_NAMESPACE   = your_tenancy_namespace
    OCI_BUCKET      = triptokforge
    OCI_REGION      = us-ashburn-1
    OCI_KEY_FILE    = /home/ubuntu/.oci/oci_api_key.pem
    OCI_FINGERPRINT = aa:bb:cc:...
    OCI_TENANCY     = ocid1.tenancy.oc1...
    OCI_USER        = ocid1.user.oc1...
"""

import os
import json
import time
import hashlib
import traceback
from datetime import datetime

# ── Oracle DB driver (optional) ──────────────────────────────────────────────
try:
    import oracledb
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False

# ── OCI Object Storage SDK (optional) ────────────────────────────────────────
try:
    import oci
    OCI_AVAILABLE = True
except ImportError:
    OCI_AVAILABLE = False

# ── Config from environment ───────────────────────────────────────────────────
ORACLE_DSN      = os.environ.get("ORACLE_DSN", "")
ORACLE_USER     = os.environ.get("ORACLE_USER", "ADMIN")
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "")
ORACLE_WALLET   = os.environ.get("ORACLE_WALLET", "")

OCI_NAMESPACE   = os.environ.get("OCI_NAMESPACE", "")
OCI_BUCKET      = os.environ.get("OCI_BUCKET", "triptokforge")
OCI_REGION      = os.environ.get("OCI_REGION", "us-ashburn-1")
OCI_CONFIG_FILE = os.environ.get("OCI_CONFIG_FILE", os.path.expanduser("~/.oci/config"))

# ── Fallback JSON paths (used when Oracle is not configured) ──────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data")
AUDIO_DIR   = os.path.join(BASE_DIR, "saved_audio")
OUTPUT_DIR  = os.path.join(BASE_DIR, "outputs")
os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(AUDIO_DIR,  exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION POOL
# ═══════════════════════════════════════════════════════════════════════════════

_pool = None

def _get_pool():
    """Return connection pool, creating it on first call."""
    global _pool
    if _pool is not None:
        return _pool
    if not ORACLE_AVAILABLE:
        raise RuntimeError("oracledb not installed. Run: pip install oracledb --break-system-packages")
    if not ORACLE_DSN or not ORACLE_PASSWORD:
        raise RuntimeError("ORACLE_DSN and ORACLE_PASSWORD environment variables not set.")

    # Thin mode (no Oracle Client libs needed)
    if ORACLE_WALLET:
        _pool = oracledb.create_pool(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN,
            config_dir=ORACLE_WALLET,
            wallet_location=ORACLE_WALLET,
            wallet_password=ORACLE_PASSWORD,  # same as DB password by default
            min=1, max=4, increment=1,
        )
    else:
        _pool = oracledb.create_pool(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN,
            min=1, max=4, increment=1,
        )
    return _pool


def get_connection():
    """Get a connection from the pool."""
    return _get_pool().acquire()


def db_available():
    """Return True if Oracle is configured and reachable."""
    if not ORACLE_AVAILABLE or not ORACLE_DSN or not ORACLE_PASSWORD:
        return False
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA SETUP  (run once after provisioning DB)
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS members (
    epic_id      VARCHAR2(64)  PRIMARY KEY,
    display_name VARCHAR2(128) NOT NULL,
    avatar_url   VARCHAR2(512),
    skin_id      VARCHAR2(64),
    skin_name    VARCHAR2(128),
    skin_img     VARCHAR2(512),
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    last_seen    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audio_tracks (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filename     VARCHAR2(256) NOT NULL,
    original_name VARCHAR2(256),
    uploader_id  VARCHAR2(64),
    size_bytes   NUMBER,
    duration_s   NUMBER(10,3),
    sub_bass     NUMBER(6,4),
    bass         NUMBER(6,4),
    midrange     NUMBER(6,4),
    presence     NUMBER(6,4),
    brilliance   NUMBER(6,4),
    tempo_bpm    NUMBER(8,3),
    storage_url  VARCHAR2(512),
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jukebox (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id     NUMBER        REFERENCES audio_tracks(id) ON DELETE CASCADE,
    added_by     VARCHAR2(64),
    title        VARCHAR2(256),
    storage_url  VARCHAR2(512),
    votes        NUMBER        DEFAULT 0,
    played       NUMBER(1)     DEFAULT 0,
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS announcements (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        VARCHAR2(256) NOT NULL,
    body         VARCHAR2(4000),
    posted_by    VARCHAR2(128),
    pinned       NUMBER(1)     DEFAULT 0,
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS island_saves (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seed         NUMBER        NOT NULL,
    creator_id   VARCHAR2(64),
    world_size_cm NUMBER,
    water_level  NUMBER(6,4),
    plots_count  NUMBER,
    preview_url  VARCHAR2(512),
    heightmap_url VARCHAR2(512),
    layout_url   VARCHAR2(512),
    weights_json VARCHAR2(1024),
    biome_stats  VARCHAR2(2048),
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    epic_id      VARCHAR2(64),
    display_name VARCHAR2(128),
    skin_img     VARCHAR2(512),
    caption      VARCHAR2(1000),
    embed_url    VARCHAR2(1024) NOT NULL,
    likes        NUMBER        DEFAULT 0,
    approved     NUMBER(1)     DEFAULT 1,
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS channels (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         VARCHAR2(128) NOT NULL,
    category     VARCHAR2(64),
    embed_url    VARCHAR2(1024) NOT NULL,
    description  VARCHAR2(512),
    approved     NUMBER(1)     DEFAULT 0,
    suggested_by VARCHAR2(64),
    sort_order   NUMBER        DEFAULT 0,
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);
"""

def init_schema():
    """Create tables if they don't exist. Safe to call multiple times."""
    if not db_available():
        print("[oracle_db] DB not available — skipping schema init")
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        # Oracle doesn't support IF NOT EXISTS for tables — split and try each
        for stmt in SCHEMA_SQL.strip().split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                cur.execute(stmt)
            except Exception as e:
                if "ORA-00955" in str(e):  # name already used
                    pass
                else:
                    print(f"[oracle_db] schema warning: {e}")
        conn.commit()
        cur.close()
        conn.close()
        print("[oracle_db] Schema ready.")
        return True
    except Exception as e:
        print(f"[oracle_db] Schema init failed: {e}")
        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBER OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def upsert_member(epic_id, display_name, avatar_url="", skin_id="", skin_name="", skin_img=""):
    """Insert or update a member record."""
    if not db_available():
        return _json_upsert_member(epic_id, display_name, avatar_url, skin_id, skin_name, skin_img)
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            MERGE INTO members m
            USING (SELECT :epic_id AS epic_id FROM dual) src
            ON (m.epic_id = src.epic_id)
            WHEN MATCHED THEN UPDATE SET
                display_name = :display_name,
                avatar_url   = :avatar_url,
                last_seen    = CURRENT_TIMESTAMP
            WHEN NOT MATCHED THEN INSERT
                (epic_id, display_name, avatar_url, skin_id, skin_name, skin_img)
            VALUES
                (:epic_id, :display_name, :avatar_url, :skin_id, :skin_name, :skin_img)
        """, {
            "epic_id":      epic_id,
            "display_name": display_name,
            "avatar_url":   avatar_url,
            "skin_id":      skin_id,
            "skin_name":    skin_name,
            "skin_img":     skin_img,
        })
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] upsert_member error: {e}")
        return False


def update_member_skin(epic_id, skin_id, skin_name, skin_img):
    """Update skin selection for a member."""
    if not db_available():
        return _json_update_skin(epic_id, skin_id, skin_name, skin_img)
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            UPDATE members SET skin_id=:skin_id, skin_name=:skin_name, skin_img=:skin_img
            WHERE epic_id=:epic_id
        """, {"skin_id": skin_id, "skin_name": skin_name, "skin_img": skin_img, "epic_id": epic_id})
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] update_member_skin error: {e}")
        return False


def get_all_members():
    """Return list of all members for community page."""
    if not db_available():
        return _json_get_members()
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT epic_id, display_name, avatar_url, skin_img, skin_name, last_seen
            FROM members ORDER BY last_seen DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "epic_id":      r[0],
                "display_name": r[1],
                "avatar_url":   r[2] or "",
                "skin_img":     r[3] or "",
                "skin_name":    r[4] or "Default",
                "last_seen":    str(r[5]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[oracle_db] get_all_members error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO TRACK OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def save_audio_track(filename, weights, uploader_id="", size_bytes=0, storage_url="", original_name=""):
    """Save audio track metadata to DB."""
    if not db_available():
        return True  # local file system used as fallback
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO audio_tracks
                (filename, original_name, uploader_id, size_bytes, duration_s,
                 sub_bass, bass, midrange, presence, brilliance, tempo_bpm, storage_url)
            VALUES
                (:filename, :original_name, :uploader_id, :size_bytes, :duration_s,
                 :sub_bass, :bass, :midrange, :presence, :brilliance, :tempo_bpm, :storage_url)
        """, {
            "filename":      filename,
            "original_name": original_name or filename,
            "uploader_id":   uploader_id,
            "size_bytes":    size_bytes,
            "duration_s":    weights.get("duration_s", 0),
            "sub_bass":      weights.get("sub_bass", 0.5),
            "bass":          weights.get("bass", 0.5),
            "midrange":      weights.get("midrange", 0.5),
            "presence":      weights.get("presence", 0.5),
            "brilliance":    weights.get("brilliance", 0.5),
            "tempo_bpm":     weights.get("tempo_bpm", 120.0),
            "storage_url":   storage_url,
        })
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] save_audio_track error: {e}")
        return False


def get_audio_tracks(uploader_id=""):
    """Get audio track list. If uploader_id given, filter by uploader."""
    if not db_available():
        return _json_get_audio_tracks()
    try:
        conn = get_connection()
        cur  = conn.cursor()
        if uploader_id:
            cur.execute("""
                SELECT filename, size_bytes, storage_url, sub_bass, bass, midrange,
                       presence, brilliance, tempo_bpm, duration_s, created_at
                FROM audio_tracks WHERE uploader_id=:uid ORDER BY created_at DESC
            """, {"uid": uploader_id})
        else:
            cur.execute("""
                SELECT filename, size_bytes, storage_url, sub_bass, bass, midrange,
                       presence, brilliance, tempo_bpm, duration_s, created_at
                FROM audio_tracks ORDER BY created_at DESC
            """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "filename":    r[0],
                "size_kb":     round((r[1] or 0) / 1024, 1),
                "storage_url": r[2] or "",
                "weights": {
                    "sub_bass":   float(r[3] or 0.5),
                    "bass":       float(r[4] or 0.5),
                    "midrange":   float(r[5] or 0.5),
                    "presence":   float(r[6] or 0.5),
                    "brilliance": float(r[7] or 0.5),
                    "tempo_bpm":  float(r[8] or 120.0),
                    "duration_s": float(r[9] or 0),
                },
                "created_at": str(r[10]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[oracle_db] get_audio_tracks error: {e}")
        return []


def delete_audio_track(filename):
    """Delete audio track metadata from DB."""
    if not db_available():
        return True
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM audio_tracks WHERE filename=:fn", {"fn": filename})
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] delete_audio_track error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ANNOUNCEMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def get_announcements():
    """Return list of announcements, pinned first."""
    if not db_available():
        return _json_load("announcements.json", [])
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, title, body, posted_by, pinned, created_at
            FROM announcements ORDER BY pinned DESC, created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id":         r[0],
                "title":      r[1],
                "body":       r[2] or "",
                "posted_by":  r[3] or "Admin",
                "pinned":     bool(r[4]),
                "created_at": str(r[5]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[oracle_db] get_announcements error: {e}")
        return []


def post_announcement(title, body, posted_by="Admin", pinned=False):
    """Post a new announcement."""
    if not db_available():
        items = _json_load("announcements.json", [])
        items.insert(0, {
            "id": int(time.time()), "title": title, "body": body,
            "posted_by": posted_by, "pinned": pinned,
            "created_at": datetime.utcnow().isoformat(),
        })
        _json_save("announcements.json", items)
        return True
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO announcements (title, body, posted_by, pinned)
            VALUES (:title, :body, :posted_by, :pinned)
        """, {"title": title, "body": body, "posted_by": posted_by, "pinned": 1 if pinned else 0})
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] post_announcement error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ISLAND SAVES
# ═══════════════════════════════════════════════════════════════════════════════

def save_island(seed, creator_id="", world_size_cm=1100000, water_level=0.2,
                plots_count=0, preview_url="", heightmap_url="", layout_url="",
                weights=None, biome_stats=None):
    """Save island generation metadata to DB."""
    if not db_available():
        return True  # local files used as fallback
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO island_saves
                (seed, creator_id, world_size_cm, water_level, plots_count,
                 preview_url, heightmap_url, layout_url, weights_json, biome_stats)
            VALUES
                (:seed, :creator_id, :world_size_cm, :water_level, :plots_count,
                 :preview_url, :heightmap_url, :layout_url, :weights_json, :biome_stats)
        """, {
            "seed":          seed,
            "creator_id":    creator_id,
            "world_size_cm": world_size_cm,
            "water_level":   water_level,
            "plots_count":   plots_count,
            "preview_url":   preview_url,
            "heightmap_url": heightmap_url,
            "layout_url":    layout_url,
            "weights_json":  json.dumps(weights or {}),
            "biome_stats":   json.dumps(biome_stats or []),
        })
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] save_island error: {e}")
        return False


def get_recent_islands(limit=20):
    """Return list of recent island saves for gallery."""
    if not db_available():
        return []
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT seed, creator_id, world_size_cm, water_level, plots_count,
                   preview_url, biome_stats, created_at
            FROM island_saves
            ORDER BY created_at DESC
            FETCH FIRST :lim ROWS ONLY
        """, {"lim": limit})
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "seed":          r[0],
                "creator_id":    r[1] or "",
                "world_size_cm": r[2],
                "water_level":   float(r[3] or 0.2),
                "plots_count":   r[4],
                "preview_url":   r[5] or "",
                "biome_stats":   json.loads(r[6] or "[]"),
                "created_at":    str(r[7]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[oracle_db] get_recent_islands error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# OCI OBJECT STORAGE
# ═══════════════════════════════════════════════════════════════════════════════

def oci_client():
    """Return an OCI ObjectStorageClient or None if not configured."""
    if not OCI_AVAILABLE or not OCI_NAMESPACE:
        return None, None
    try:
        config = oci.config.from_file(OCI_CONFIG_FILE)
        client = oci.object_storage.ObjectStorageClient(config)
        return client, config["region"]
    except Exception as e:
        print(f"[oracle_db] OCI config error: {e}")
        return None, None


def oci_upload(local_path, object_name, content_type="application/octet-stream"):
    """
    Upload a file to OCI Object Storage.
    Returns the public URL or empty string on failure.
    """
    client, region = oci_client()
    if not client:
        return ""
    try:
        with open(local_path, "rb") as f:
            data = f.read()
        client.put_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET,
            object_name=object_name,
            put_object_body=data,
            content_type=content_type,
        )
        url = (
            f"https://objectstorage.{OCI_REGION}.oraclecloud.com"
            f"/n/{OCI_NAMESPACE}/b/{OCI_BUCKET}/o/{object_name}"
        )
        print(f"[oracle_db] Uploaded {object_name} → {url}")
        return url
    except Exception as e:
        print(f"[oracle_db] oci_upload error: {e}")
        return ""


def oci_upload_bytes(data_bytes, object_name, content_type="application/octet-stream"):
    """Upload bytes directly to OCI Object Storage."""
    client, region = oci_client()
    if not client:
        return ""
    try:
        client.put_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET,
            object_name=object_name,
            put_object_body=data_bytes,
            content_type=content_type,
        )
        url = (
            f"https://objectstorage.{OCI_REGION}.oraclecloud.com"
            f"/n/{OCI_NAMESPACE}/b/{OCI_BUCKET}/o/{object_name}"
        )
        return url
    except Exception as e:
        print(f"[oracle_db] oci_upload_bytes error: {e}")
        return ""


def oci_delete(object_name):
    """Delete an object from OCI Object Storage."""
    client, _ = oci_client()
    if not client:
        return False
    try:
        client.delete_object(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET,
            object_name=object_name,
        )
        return True
    except Exception as e:
        print(f"[oracle_db] oci_delete error: {e}")
        return False


def oci_presigned_url(object_name, expiry_seconds=3600):
    """
    Generate a pre-authenticated request URL for temporary access.
    Returns URL string or empty string on failure.
    """
    client, _ = oci_client()
    if not client:
        return ""
    try:
        from oci.object_storage.models import CreatePreauthenticatedRequestDetails
        from datetime import timedelta
        details = CreatePreauthenticatedRequestDetails(
            name=f"par-{object_name}",
            access_type="ObjectRead",
            time_expires=datetime.utcnow() + timedelta(seconds=expiry_seconds),
            object_name=object_name,
        )
        resp = client.create_preauthenticated_request(
            namespace_name=OCI_NAMESPACE,
            bucket_name=OCI_BUCKET,
            create_preauthenticated_request_details=details,
        )
        return f"https://objectstorage.{OCI_REGION}.oraclecloud.com{resp.data.access_uri}"
    except Exception as e:
        print(f"[oracle_db] presigned_url error: {e}")
        return ""


def audio_object_name(filename):
    """Standard OCI object name for an audio file."""
    return f"audio/{filename}"


def preview_object_name(seed):
    """Standard OCI object name for an island preview PNG."""
    return f"previews/island_{seed}_preview.png"


def heightmap_object_name(seed):
    """Standard OCI object name for a heightmap PNG."""
    return f"heightmaps/island_{seed}_heightmap.png"


def layout_object_name(seed):
    """Standard OCI object name for a layout JSON."""
    return f"layouts/island_{seed}_layout.json"


# ═══════════════════════════════════════════════════════════════════════════════
# JSON FALLBACK HELPERS  (used when Oracle not configured)
# ═══════════════════════════════════════════════════════════════════════════════

def _json_load(filename, default):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _json_save(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _json_upsert_member(epic_id, display_name, avatar_url, skin_id, skin_name, skin_img):
    members = {m["epic_id"]: m for m in _json_load("members.json", [])}
    existing = members.get(epic_id, {})
    members[epic_id] = {
        "epic_id":      epic_id,
        "display_name": display_name,
        "avatar_url":   avatar_url or existing.get("avatar_url", ""),
        "skin_id":      skin_id or existing.get("skin_id", ""),
        "skin_name":    skin_name or existing.get("skin_name", "Default"),
        "skin_img":     skin_img or existing.get("skin_img", ""),
        "last_seen":    datetime.utcnow().isoformat(),
        "created_at":   existing.get("created_at", datetime.utcnow().isoformat()),
    }
    _json_save("members.json", list(members.values()))
    return True


def _json_update_skin(epic_id, skin_id, skin_name, skin_img):
    members = {m["epic_id"]: m for m in _json_load("members.json", [])}
    if epic_id in members:
        members[epic_id].update({"skin_id": skin_id, "skin_name": skin_name, "skin_img": skin_img})
        _json_save("members.json", list(members.values()))
    return True


def _json_get_members():
    return _json_load("members.json", [])


def _json_get_audio_tracks():
    """Return audio track list from local filesystem."""
    SUPPORTED_EXTS = (".wav", ".mp3", ".flac", ".ogg", ".aac", ".m4a", ".aiff", ".opus")
    try:
        files = []
        for fn in sorted(os.listdir(AUDIO_DIR)):
            if os.path.splitext(fn)[1].lower() not in SUPPORTED_EXTS:
                continue
            path = os.path.join(AUDIO_DIR, fn)
            files.append({
                "filename":    fn,
                "size_kb":     round(os.path.getsize(path) / 1024, 1),
                "storage_url": f"/audio/stream/{fn}",
                "weights":     None,
            })
        return files
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS / HEALTH
# ═══════════════════════════════════════════════════════════════════════════════

def status():
    """Return dict with connection status for /health endpoint."""
    return {
        "oracle_driver":   ORACLE_AVAILABLE,
        "oracle_config":   bool(ORACLE_DSN and ORACLE_PASSWORD),
        "oracle_online":   db_available(),
        "oci_sdk":         OCI_AVAILABLE,
        "oci_config":      bool(OCI_NAMESPACE),
        "fallback_mode":   not db_available(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# POST OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_post(epic_id, display_name, skin_img, caption, embed_url):
    """Create a new community post."""
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO posts (epic_id, display_name, skin_img, caption, embed_url)
            VALUES (:epic_id, :display_name, :skin_img, :caption, :embed_url)
        """, {"epic_id": epic_id, "display_name": display_name,
              "skin_img": skin_img, "caption": caption, "embed_url": embed_url})
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] create_post error: {e}")
        return False

def get_posts(limit=50, approved_only=True):
    """Return recent posts."""
    if not db_available():
        return []
    try:
        conn = get_connection()
        cur  = conn.cursor()
        if approved_only:
            cur.execute("SELECT id, epic_id, display_name, skin_img, caption, embed_url, likes, created_at FROM posts WHERE approved=1 ORDER BY created_at DESC FETCH FIRST :n ROWS ONLY", {"n": limit})
        else:
            cur.execute("SELECT id, epic_id, display_name, skin_img, caption, embed_url, likes, created_at FROM posts ORDER BY created_at DESC FETCH FIRST :n ROWS ONLY", {"n": limit})
        cols = ["id","epic_id","display_name","skin_img","caption","embed_url","likes","created_at"]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        for r in rows:
            if hasattr(r.get("created_at"), "isoformat"):
                r["created_at"] = r["created_at"].isoformat()
        cur.close(); conn.close()
        return rows
    except Exception as e:
        print(f"[oracle_db] get_posts error: {e}")
        return []

def like_post(post_id):
    """Increment likes on a post."""
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("UPDATE posts SET likes = likes + 1 WHERE id = :id", {"id": post_id})
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] like_post error: {e}")
        return False

def delete_post(post_id):
    """Delete a post by id."""
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM posts WHERE id = :id", {"id": post_id})
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] delete_post error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CHANNEL OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def suggest_channel(name, category, embed_url, description, suggested_by):
    """Submit a channel suggestion (pending approval)."""
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO channels (name, category, embed_url, description, suggested_by, approved)
            VALUES (:name, :category, :embed_url, :description, :suggested_by, 0)
        """, {"name": name, "category": category, "embed_url": embed_url,
              "description": description, "suggested_by": suggested_by})
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] suggest_channel error: {e}")
        return False

def get_channels(approved_only=True):
    """Return channels list."""
    if not db_available():
        return []
    try:
        conn = get_connection()
        cur  = conn.cursor()
        if approved_only:
            cur.execute("SELECT id, name, category, embed_url, description, suggested_by, sort_order FROM channels WHERE approved=1 ORDER BY category, sort_order, id")
        else:
            cur.execute("SELECT id, name, category, embed_url, description, suggested_by, sort_order, approved FROM channels ORDER BY approved DESC, category, id")
        cols = ["id","name","category","embed_url","description","suggested_by","sort_order"] if approved_only else ["id","name","category","embed_url","description","suggested_by","sort_order","approved"]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    except Exception as e:
        print(f"[oracle_db] get_channels error: {e}")
        return []

def approve_channel(channel_id, approved=1):
    """Approve or reject a channel."""
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("UPDATE channels SET approved=:a WHERE id=:id", {"a": approved, "id": channel_id})
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] approve_channel error: {e}")
        return False

def delete_channel(channel_id):
    """Delete a channel."""
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM channels WHERE id=:id", {"id": channel_id})
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] delete_channel error: {e}")
        return False


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


# ── PRESETS ──────────────────────────────────────────────────

def get_presets(limit: int = 100) -> list:
    """Return all public island presets."""
    if not db_available():
        return []
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, epic_id, display_name, name, config, created_at
                   FROM island_presets
                   WHERE is_public = 1
                   ORDER BY created_at DESC
                   FETCH FIRST :1 ROWS ONLY""",
                [limit]
            )
            rows = []
            for row in cur.fetchall():
                try:
                    cfg = json.loads(row[4]) if row[4] else {}
                except Exception:
                    cfg = {}
                rows.append({
                    "id":           row[0],
                    "epic_id":      row[1],
                    "display_name": row[2],
                    "name":         row[3],
                    "config":       cfg,
                    "created_at":   str(row[5]) if row[5] else "",
                })
            return rows
    except Exception as e:
        _log(f"get_presets error: {e}")
        return []

def get_preset_by_id(preset_id: int) -> dict:
    """Return a single preset by ID."""
    if not db_available():
        return None
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, epic_id, display_name, name, config, created_at
                   FROM island_presets WHERE id = :1""",
                [preset_id]
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                cfg = json.loads(row[4]) if row[4] else {}
            except Exception:
                cfg = {}
            return {
                "id":           row[0],
                "epic_id":      row[1],
                "display_name": row[2],
                "name":         row[3],
                "config":       cfg,
                "created_at":   str(row[5]) if row[5] else "",
            }
    except Exception as e:
        _log(f"get_preset_by_id error: {e}")
        return None

def save_preset(epic_id: str, display_name: str, name: str,
                config: dict, is_public: bool = True):
    """Save an island preset. Returns new ID."""
    if not db_available():
        return None
    try:
        with _conn() as conn:
            cur = conn.cursor()
            new_id = cur.var(__import__("oracledb").NUMBER)
            cur.execute(
                """INSERT INTO island_presets
                   (epic_id, display_name, name, config, is_public, created_at)
                   VALUES (:1, :2, :3, :4, :5, CURRENT_TIMESTAMP)
                   RETURNING id INTO :6""",
                [epic_id, display_name, name, json.dumps(config),
                 1 if is_public else 0, new_id]
            )
            conn.commit()
            return int(new_id.getvalue()[0])
    except Exception as e:
        _log(f"save_preset error: {e}")
        return None

def delete_preset(preset_id: int, epic_id: str) -> bool:
    """Delete a preset — only owner can delete."""
    if not db_available():
        return False
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM island_presets WHERE id = :1 AND epic_id = :2",
                [preset_id, epic_id]
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        _log(f"delete_preset error: {e}")
        return False

def save_island_to_gallery(epic_id: str, display_name: str, name: str,
                            seed, dominant_biome: str, preview_b64: str,
                            config: dict, verse_data: dict,
                            stickers: list, is_public: bool = True):
    """Save a generated island to the gallery + room wall."""
    if not db_available():
        return None
    try:
        # Upload preview to OCI if available, else store truncated b64
        preview_url = ""
        if preview_b64:
            try:
                import base64, oci.object_storage, os as _os
                client = _oci_client()
                img_bytes = base64.b64decode(preview_b64)
                obj_name  = f"previews/{epic_id or 'anon'}_{seed}_{int(__import__('time').time())}.png"
                ns        = _os.environ.get("OCI_NAMESPACE","")
                bucket    = _os.environ.get("OCI_BUCKET","triptokforge")
                client.put_object(ns, bucket, obj_name,
                                  img_bytes,
                                  content_type="image/png")
                region = _os.environ.get("OCI_REGION","us-ashburn-1")
                preview_url = f"https://objectstorage.{region}.oraclecloud.com/n/{ns}/b/{bucket}/o/{obj_name}"
            except Exception as oci_e:
                _log(f"OCI preview upload skipped: {oci_e}")

        with _conn() as conn:
            cur = conn.cursor()
            new_id = cur.var(__import__("oracledb").NUMBER)
            cur.execute(
                """INSERT INTO island_saves
                   (epic_id, display_name, seed, name, dominant_biome,
                    preview_url, config, verse_data, stickers, is_public, created_at)
                   VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,CURRENT_TIMESTAMP)
                   RETURNING id INTO :11""",
                [epic_id, display_name, seed, name, dominant_biome,
                 preview_url,
                 json.dumps(config),
                 json.dumps(verse_data),
                 json.dumps(stickers),
                 1 if is_public else 0,
                 new_id]
            )
            conn.commit()
            return int(new_id.getvalue()[0])
    except Exception as e:
        _log(f"save_island_to_gallery error: {e}")
        return None
