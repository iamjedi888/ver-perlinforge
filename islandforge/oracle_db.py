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
CREATE TABLE members (
    epic_id      VARCHAR2(64)  PRIMARY KEY,
    display_name VARCHAR2(128) NOT NULL,
    avatar_url   VARCHAR2(512),
    skin_id      VARCHAR2(64),
    skin_name    VARCHAR2(128),
    skin_img     VARCHAR2(512),
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    last_seen    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audio_tracks (
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

CREATE TABLE jukebox (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id     NUMBER        REFERENCES audio_tracks(id) ON DELETE CASCADE,
    added_by     VARCHAR2(64),
    title        VARCHAR2(256),
    storage_url  VARCHAR2(512),
    votes        NUMBER        DEFAULT 0,
    played       NUMBER(1)     DEFAULT 0,
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE announcements (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        VARCHAR2(256) NOT NULL,
    body         VARCHAR2(4000),
    posted_by    VARCHAR2(128),
    pinned       NUMBER(1)     DEFAULT 0,
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE island_saves (
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

CREATE TABLE posts (
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

CREATE TABLE channels (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         VARCHAR2(128) NOT NULL,
    category     VARCHAR2(64),
    embed_url    VARCHAR2(1024) NOT NULL,
    description  VARCHAR2(512),
    source_urls_json CLOB,
    search_terms_json CLOB,
    provider_hint VARCHAR2(32),
    rotation_mode VARCHAR2(32) DEFAULT 'single',
    autoplay     NUMBER(1)     DEFAULT 1,
    transition_title VARCHAR2(128),
    transition_copy VARCHAR2(512),
    transition_seconds NUMBER(6,2) DEFAULT 0.9,
    approved     NUMBER(1)     DEFAULT 0,
    suggested_by VARCHAR2(64),
    sort_order   NUMBER        DEFAULT 0,
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE site_broadcasts (
    id               NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title            VARCHAR2(128) NOT NULL,
    body             VARCHAR2(1024),
    variant          VARCHAR2(24)  DEFAULT 'info',
    display_mode     VARCHAR2(24)  DEFAULT 'banner',
    dismiss_mode     VARCHAR2(24)  DEFAULT 'manual',
    duration_seconds NUMBER(6,2)   DEFAULT 8,
    cta_label        VARCHAR2(64),
    cta_href         VARCHAR2(512),
    closable         NUMBER(1)     DEFAULT 1,
    active           NUMBER(1)     DEFAULT 1,
    created_by       VARCHAR2(64),
    priority         NUMBER        DEFAULT 0,
    created_at       TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wp_tracks (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        VARCHAR2(256) NOT NULL,
    artist       VARCHAR2(128),
    source_type  VARCHAR2(32)  DEFAULT 'soundcloud',
    embed_url    VARCHAR2(1024) NOT NULL,
    sort_order   NUMBER        DEFAULT 0,
    active       NUMBER(1)     DEFAULT 1,
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


CHANNEL_SCHEMA_COLUMNS = {
    "SOURCE_URLS_JSON": "CLOB",
    "SEARCH_TERMS_JSON": "CLOB",
    "PROVIDER_HINT": "VARCHAR2(32)",
    "ROTATION_MODE": "VARCHAR2(32) DEFAULT 'single'",
    "AUTOPLAY": "NUMBER(1) DEFAULT 1",
    "TRANSITION_TITLE": "VARCHAR2(128)",
    "TRANSITION_COPY": "VARCHAR2(512)",
    "TRANSITION_SECONDS": "NUMBER(6,2) DEFAULT 0.9",
}

_channel_schema_checked = False


def _column_exists(cur, table_name, column_name):
    cur.execute(
        """
        SELECT COUNT(*)
          FROM user_tab_columns
         WHERE table_name = :table_name
           AND column_name = :column_name
        """,
        {
            "table_name": table_name.upper(),
            "column_name": column_name.upper(),
        },
    )
    row = cur.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def _to_json_text_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(item or "").strip() for item in value]
    else:
        raw = str(value or "").strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                items = [str(item or "").strip() for item in parsed]
            else:
                items = [part.strip() for part in raw.splitlines()]
        except Exception:
            items = [part.strip() for part in raw.splitlines()]
    unique = []
    seen = set()
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _json_dump_list(value):
    return json.dumps(_to_json_text_list(value))


def _channel_row_to_dict(columns, row):
    record = dict(zip(columns, row))
    source_urls = _to_json_text_list(record.get("source_urls_json"))
    search_terms = _to_json_text_list(record.get("search_terms_json"))
    if not source_urls and record.get("embed_url"):
        source_urls = _to_json_text_list(record.get("embed_url"))
    record["source_urls"] = source_urls
    record["search_terms"] = search_terms
    record["source_urls_text"] = "\n".join(source_urls)
    record["search_terms_text"] = "\n".join(search_terms)
    record["provider_hint"] = record.get("provider_hint") or ""
    record["rotation_mode"] = record.get("rotation_mode") or ("queue" if len(source_urls) > 1 else "single")
    record["autoplay"] = int(record.get("autoplay") or 0)
    record["transition_title"] = record.get("transition_title") or ""
    record["transition_copy"] = record.get("transition_copy") or ""
    record["transition_seconds"] = float(record.get("transition_seconds") or 0.9)
    return record


def ensure_channel_schema():
    global _channel_schema_checked
    if _channel_schema_checked or not db_available():
        return False

    try:
        conn = get_connection()
        cur = conn.cursor()

        for column_name, definition in CHANNEL_SCHEMA_COLUMNS.items():
            if _column_exists(cur, "CHANNELS", column_name):
                continue
            cur.execute(f"ALTER TABLE channels ADD ({column_name} {definition})")

        cur.execute(
            """
            SELECT id, embed_url
              FROM channels
             WHERE source_urls_json IS NULL
                OR autoplay IS NULL
                OR rotation_mode IS NULL
            """
        )
        rows = cur.fetchall()
        for channel_id, embed_url in rows:
            source_urls = _to_json_text_list(embed_url)
            cur.execute(
                """
                UPDATE channels
                   SET source_urls_json = COALESCE(source_urls_json, :source_urls_json),
                       autoplay = COALESCE(autoplay, 1),
                       rotation_mode = COALESCE(rotation_mode, :rotation_mode),
                       transition_seconds = COALESCE(transition_seconds, 0.9)
                 WHERE id = :id
                """,
                {
                    "id": channel_id,
                    "source_urls_json": json.dumps(source_urls),
                    "rotation_mode": "queue" if len(source_urls) > 1 else "single",
                },
            )

        conn.commit()
        cur.close()
        conn.close()
        _channel_schema_checked = True
        return True
    except Exception as e:
        print(f"[oracle_db] ensure_channel_schema error: {e}")
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
        ensure_channel_schema()
        source_urls = _to_json_text_list(embed_url)
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO channels (
                name, category, embed_url, description, suggested_by, approved,
                source_urls_json, rotation_mode, autoplay, transition_seconds
            )
            VALUES (
                :name, :category, :embed_url, :description, :suggested_by, 0,
                :source_urls_json, :rotation_mode, 1, 0.9
            )
        """, {
            "name": name,
            "category": category,
            "embed_url": embed_url,
            "description": description,
            "suggested_by": suggested_by,
            "source_urls_json": json.dumps(source_urls),
            "rotation_mode": "queue" if len(source_urls) > 1 else "single",
        })
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] suggest_channel error: {e}")
        return False

def _next_channel_sort_order(cur, category):
    cur.execute(
        "SELECT NVL(MAX(sort_order), -1) + 1 FROM channels WHERE category = :category",
        {"category": category},
    )
    row = cur.fetchone()
    return int(row[0] or 0) if row else 0

def create_channel(
    name,
    category,
    embed_url,
    description="",
    suggested_by="admin",
    approved=1,
    sort_order=None,
    source_urls_json=None,
    search_terms_json=None,
    provider_hint="",
    rotation_mode="single",
    autoplay=1,
    transition_title="",
    transition_copy="",
    transition_seconds=0.9,
):
    """Create a channel entry."""
    if not db_available():
        return False
    try:
        ensure_channel_schema()
        conn = get_connection()
        cur = conn.cursor()
        if sort_order is None:
            sort_order = _next_channel_sort_order(cur, category)
        source_urls = _to_json_text_list(source_urls_json or embed_url)
        search_terms = _to_json_text_list(search_terms_json)
        rotation_mode = rotation_mode or ("queue" if len(source_urls) > 1 else "single")
        cur.execute(
            """
            INSERT INTO channels (
                name, category, embed_url, description, suggested_by, approved, sort_order,
                source_urls_json, search_terms_json, provider_hint, rotation_mode, autoplay,
                transition_title, transition_copy, transition_seconds
            )
            VALUES (
                :name, :category, :embed_url, :description, :suggested_by, :approved, :sort_order,
                :source_urls_json, :search_terms_json, :provider_hint, :rotation_mode, :autoplay,
                :transition_title, :transition_copy, :transition_seconds
            )
            """,
            {
                "name": name,
                "category": category,
                "embed_url": embed_url,
                "description": description,
                "suggested_by": suggested_by,
                "approved": approved,
                "sort_order": sort_order,
                "source_urls_json": json.dumps(source_urls),
                "search_terms_json": json.dumps(search_terms),
                "provider_hint": (provider_hint or "")[:32],
                "rotation_mode": (rotation_mode or "single")[:32],
                "autoplay": 1 if autoplay else 0,
                "transition_title": (transition_title or "")[:128],
                "transition_copy": (transition_copy or "")[:512],
                "transition_seconds": float(transition_seconds or 0.9),
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close(); conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] create_channel error: {e}")
        return False

def update_channel(
    channel_id,
    name,
    category,
    embed_url,
    description="",
    sort_order=None,
    approved=None,
    source_urls_json=None,
    search_terms_json=None,
    provider_hint="",
    rotation_mode="single",
    autoplay=1,
    transition_title="",
    transition_copy="",
    transition_seconds=0.9,
):
    """Update an existing channel entry."""
    if not db_available():
        return False
    try:
        ensure_channel_schema()
        conn = get_connection()
        cur = conn.cursor()
        if sort_order is None:
            cur.execute("SELECT sort_order FROM channels WHERE id = :id", {"id": channel_id})
            row = cur.fetchone()
            sort_order = int(row[0] or 0) if row else 0
        source_urls = _to_json_text_list(source_urls_json or embed_url)
        search_terms = _to_json_text_list(search_terms_json)
        rotation_mode = rotation_mode or ("queue" if len(source_urls) > 1 else "single")
        if approved is None:
            cur.execute(
                """
                UPDATE channels
                   SET name = :name,
                       category = :category,
                       embed_url = :embed_url,
                       description = :description,
                       sort_order = :sort_order,
                       source_urls_json = :source_urls_json,
                       search_terms_json = :search_terms_json,
                       provider_hint = :provider_hint,
                       rotation_mode = :rotation_mode,
                       autoplay = :autoplay,
                       transition_title = :transition_title,
                       transition_copy = :transition_copy,
                       transition_seconds = :transition_seconds
                 WHERE id = :id
                """,
                {
                    "id": channel_id,
                    "name": name,
                    "category": category,
                    "embed_url": embed_url,
                    "description": description,
                    "sort_order": sort_order,
                    "source_urls_json": json.dumps(source_urls),
                    "search_terms_json": json.dumps(search_terms),
                    "provider_hint": (provider_hint or "")[:32],
                    "rotation_mode": (rotation_mode or "single")[:32],
                    "autoplay": 1 if autoplay else 0,
                    "transition_title": (transition_title or "")[:128],
                    "transition_copy": (transition_copy or "")[:512],
                    "transition_seconds": float(transition_seconds or 0.9),
                },
            )
        else:
            cur.execute(
                """
                UPDATE channels
                   SET name = :name,
                       category = :category,
                       embed_url = :embed_url,
                       description = :description,
                       sort_order = :sort_order,
                       approved = :approved,
                       source_urls_json = :source_urls_json,
                       search_terms_json = :search_terms_json,
                       provider_hint = :provider_hint,
                       rotation_mode = :rotation_mode,
                       autoplay = :autoplay,
                       transition_title = :transition_title,
                       transition_copy = :transition_copy,
                       transition_seconds = :transition_seconds
                 WHERE id = :id
                """,
                {
                    "id": channel_id,
                    "name": name,
                    "category": category,
                    "embed_url": embed_url,
                    "description": description,
                    "sort_order": sort_order,
                    "approved": approved,
                    "source_urls_json": json.dumps(source_urls),
                    "search_terms_json": json.dumps(search_terms),
                    "provider_hint": (provider_hint or "")[:32],
                    "rotation_mode": (rotation_mode or "single")[:32],
                    "autoplay": 1 if autoplay else 0,
                    "transition_title": (transition_title or "")[:128],
                    "transition_copy": (transition_copy or "")[:512],
                    "transition_seconds": float(transition_seconds or 0.9),
                },
            )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close(); conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] update_channel error: {e}")
        return False

def get_channel(channel_id):
    """Return a single channel by id."""
    if not db_available():
        return None
    try:
        ensure_channel_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, category, embed_url, description, suggested_by, sort_order, approved,
                   source_urls_json, search_terms_json, provider_hint, rotation_mode, autoplay,
                   transition_title, transition_copy, transition_seconds
              FROM channels
             WHERE id = :id
            """,
            {"id": channel_id},
        )
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return None
        cols = [
            "id", "name", "category", "embed_url", "description", "suggested_by", "sort_order", "approved",
            "source_urls_json", "search_terms_json", "provider_hint", "rotation_mode", "autoplay",
            "transition_title", "transition_copy", "transition_seconds",
        ]
        return _channel_row_to_dict(cols, row)
    except Exception as e:
        print(f"[oracle_db] get_channel error: {e}")
        return None

def get_channels(approved_only=True):
    """Return channels list."""
    if not db_available():
        return []
    try:
        ensure_channel_schema()
        conn = get_connection()
        cur  = conn.cursor()
        if approved_only:
            cur.execute(
                """
                SELECT id, name, category, embed_url, description, suggested_by, sort_order,
                       source_urls_json, search_terms_json, provider_hint, rotation_mode, autoplay,
                       transition_title, transition_copy, transition_seconds
                  FROM channels
                 WHERE approved=1
                 ORDER BY category, sort_order, id
                """
            )
        else:
            cur.execute(
                """
                SELECT id, name, category, embed_url, description, suggested_by, sort_order, approved,
                       source_urls_json, search_terms_json, provider_hint, rotation_mode, autoplay,
                       transition_title, transition_copy, transition_seconds
                  FROM channels
                 ORDER BY approved DESC, category, id
                """
            )
        cols = (
            ["id","name","category","embed_url","description","suggested_by","sort_order",
             "source_urls_json","search_terms_json","provider_hint","rotation_mode","autoplay",
             "transition_title","transition_copy","transition_seconds"]
            if approved_only else
            ["id","name","category","embed_url","description","suggested_by","sort_order","approved",
             "source_urls_json","search_terms_json","provider_hint","rotation_mode","autoplay",
             "transition_title","transition_copy","transition_seconds"]
        )
        rows = [_channel_row_to_dict(cols, row) for row in cur.fetchall()]
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


def create_site_broadcast(
    title,
    body="",
    variant="info",
    display_mode="banner",
    dismiss_mode="manual",
    duration_seconds=8,
    cta_label="",
    cta_href="",
    closable=1,
    active=1,
    created_by="admin",
    priority=0,
):
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO site_broadcasts (
                title, body, variant, display_mode, dismiss_mode, duration_seconds,
                cta_label, cta_href, closable, active, created_by, priority
            )
            VALUES (
                :title, :body, :variant, :display_mode, :dismiss_mode, :duration_seconds,
                :cta_label, :cta_href, :closable, :active, :created_by, :priority
            )
            """,
            {
                "title": title,
                "body": body,
                "variant": variant,
                "display_mode": display_mode,
                "dismiss_mode": dismiss_mode,
                "duration_seconds": float(duration_seconds or 8),
                "cta_label": cta_label,
                "cta_href": cta_href,
                "closable": 1 if closable else 0,
                "active": 1 if active else 0,
                "created_by": created_by,
                "priority": int(priority or 0),
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close(); conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] create_site_broadcast error: {e}")
        return False


def update_site_broadcast(
    broadcast_id,
    title,
    body="",
    variant="info",
    display_mode="banner",
    dismiss_mode="manual",
    duration_seconds=8,
    cta_label="",
    cta_href="",
    closable=1,
    active=1,
    priority=0,
):
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE site_broadcasts
               SET title = :title,
                   body = :body,
                   variant = :variant,
                   display_mode = :display_mode,
                   dismiss_mode = :dismiss_mode,
                   duration_seconds = :duration_seconds,
                   cta_label = :cta_label,
                   cta_href = :cta_href,
                   closable = :closable,
                   active = :active,
                   priority = :priority
             WHERE id = :id
            """,
            {
                "id": broadcast_id,
                "title": title,
                "body": body,
                "variant": variant,
                "display_mode": display_mode,
                "dismiss_mode": dismiss_mode,
                "duration_seconds": float(duration_seconds or 8),
                "cta_label": cta_label,
                "cta_href": cta_href,
                "closable": 1 if closable else 0,
                "active": 1 if active else 0,
                "priority": int(priority or 0),
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close(); conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] update_site_broadcast error: {e}")
        return False


def get_site_broadcast(broadcast_id):
    if not db_available():
        return None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, body, variant, display_mode, dismiss_mode, duration_seconds,
                   cta_label, cta_href, closable, active, created_by, priority, created_at
              FROM site_broadcasts
             WHERE id = :id
            """,
            {"id": broadcast_id},
        )
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return None
        cols = [
            "id", "title", "body", "variant", "display_mode", "dismiss_mode", "duration_seconds",
            "cta_label", "cta_href", "closable", "active", "created_by", "priority", "created_at",
        ]
        return dict(zip(cols, row))
    except Exception as e:
        print(f"[oracle_db] get_site_broadcast error: {e}")
        return None


def get_site_broadcasts(active_only=False, limit=50):
    if not db_available():
        return []
    try:
        conn = get_connection()
        cur = conn.cursor()
        if active_only:
            cur.execute(
                """
                SELECT id, title, body, variant, display_mode, dismiss_mode, duration_seconds,
                       cta_label, cta_href, closable, active, created_by, priority, created_at
                  FROM site_broadcasts
                 WHERE active = 1
                 ORDER BY priority DESC, created_at DESC
                 FETCH FIRST :limit ROWS ONLY
                """,
                {"limit": limit},
            )
        else:
            cur.execute(
                """
                SELECT id, title, body, variant, display_mode, dismiss_mode, duration_seconds,
                       cta_label, cta_href, closable, active, created_by, priority, created_at
                  FROM site_broadcasts
                 ORDER BY active DESC, priority DESC, created_at DESC
                 FETCH FIRST :limit ROWS ONLY
                """,
                {"limit": limit},
            )
        cols = [
            "id", "title", "body", "variant", "display_mode", "dismiss_mode", "duration_seconds",
            "cta_label", "cta_href", "closable", "active", "created_by", "priority", "created_at",
        ]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    except Exception as e:
        print(f"[oracle_db] get_site_broadcasts error: {e}")
        return []


def set_site_broadcast_active(broadcast_id, active):
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE site_broadcasts SET active = :active WHERE id = :id",
            {"id": broadcast_id, "active": 1 if active else 0},
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close(); conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] set_site_broadcast_active error: {e}")
        return False


def delete_site_broadcast(broadcast_id):
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM site_broadcasts WHERE id = :id", {"id": broadcast_id})
        conn.commit()
        ok = cur.rowcount > 0
        cur.close(); conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] delete_site_broadcast error: {e}")
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


# ═══════════════════════════════════════════════════════════════════════════════
# WHITEPAGES PLAYER TRACKS
# ═══════════════════════════════════════════════════════════════════════════════

_WP_TRACKS_JSON = os.path.join(os.path.dirname(__file__), "data", "wp_tracks.json")

def _wp_json_load():
    try:
        os.makedirs(os.path.dirname(_WP_TRACKS_JSON), exist_ok=True)
        if os.path.exists(_WP_TRACKS_JSON):
            with open(_WP_TRACKS_JSON) as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _wp_json_save(tracks):
    try:
        os.makedirs(os.path.dirname(_WP_TRACKS_JSON), exist_ok=True)
        with open(_WP_TRACKS_JSON, "w") as f:
            json.dump(tracks, f, indent=2)
        return True
    except Exception:
        return False

def get_wp_tracks():
    """Return all active whitepages player tracks ordered by sort_order."""
    if not db_available():
        return _wp_json_load()
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, title, artist, source_type, embed_url, sort_order
            FROM wp_tracks WHERE active=1
            ORDER BY sort_order, id
        """)
        rows = [dict(zip(["id","title","artist","source_type","embed_url","sort_order"], r))
                for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    except Exception as e:
        print(f"[oracle_db] get_wp_tracks error: {e}")
        return _wp_json_load()

def add_wp_track(title, artist, source_type, embed_url):
    """Add a track to the whitepages player."""
    track = {"title": title, "artist": artist,
             "source_type": source_type, "embed_url": embed_url}
    if not db_available():
        tracks = _wp_json_load()
        track["id"] = (max((t.get("id",0) for t in tracks), default=0) + 1)
        track["sort_order"] = len(tracks)
        tracks.append(track)
        _wp_json_save(tracks)
        return track["id"]
    try:
        conn = get_connection()
        cur  = conn.cursor()
        new_id = cur.var(int)
        cur.execute("""
            INSERT INTO wp_tracks (title, artist, source_type, embed_url, sort_order)
            VALUES (:title, :artist, :source_type, :embed_url,
                    (SELECT NVL(MAX(sort_order),0)+1 FROM wp_tracks))
            RETURNING id INTO :new_id
        """, {"title": title, "artist": artist, "source_type": source_type,
              "embed_url": embed_url, "new_id": new_id})
        conn.commit()
        cur.close(); conn.close()
        return int(new_id.getvalue()[0])
    except Exception as e:
        print(f"[oracle_db] add_wp_track error: {e}")
        return None

def delete_wp_track(track_id):
    """Remove a track from the whitepages player."""
    if not db_available():
        tracks = _wp_json_load()
        tracks = [t for t in tracks if t.get("id") != track_id]
        return _wp_json_save(tracks)
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM wp_tracks WHERE id=:id", {"id": track_id})
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] delete_wp_track error: {e}")
        return False
