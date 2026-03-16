"""
oracle_db.py — TriptokForge Oracle Autonomous Database Layer
=============================================================
Handles all persistent storage via Oracle Autonomous DB (Always Free).
Falls back gracefully to JSON files if DB is not configured.

CONNECTION:
  Set environment variables:
    ORACLE_DSN      = your_db_name_high   (from wallet tnsnames.ora)
    ORACLE_USER     = ADMIN  (or a dedicated user)
    ORACLE_PASSWORD = set_on_server_only
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
import hmac
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

CREATE TABLE staff_accounts (
    id             NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username       VARCHAR2(64)  NOT NULL UNIQUE,
    display_name   VARCHAR2(128) NOT NULL,
    role           VARCHAR2(32)  DEFAULT 'moderator',
    password_hash  VARCHAR2(512) NOT NULL,
    linked_bot_slug VARCHAR2(64),
    permission_overrides_json CLOB,
    active         NUMBER(1)     DEFAULT 1,
    created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bot_profiles (
    id              NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug            VARCHAR2(64)  NOT NULL UNIQUE,
    display_name    VARCHAR2(128) NOT NULL,
    badge_label     VARCHAR2(64),
    role_label      VARCHAR2(64),
    bio             VARCHAR2(1024),
    tone            VARCHAR2(256),
    language_profile VARCHAR2(128),
    llm_provider    VARCHAR2(64),
    llm_model       VARCHAR2(128),
    llm_family      VARCHAR2(128),
    scope_text      CLOB,
    surfaces_text   CLOB,
    system_prompt   CLOB,
    active          NUMBER(1)     DEFAULT 1,
    created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bot_drafts (
    id              NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bot_slug        VARCHAR2(64)  NOT NULL,
    title           VARCHAR2(256) NOT NULL,
    body            CLOB,
    target_surface  VARCHAR2(32)  DEFAULT 'announcement',
    status          VARCHAR2(32)  DEFAULT 'draft',
    payload_json    CLOB,
    created_by      VARCHAR2(64),
    reviewed_by     VARCHAR2(64),
    published_by    VARCHAR2(64),
    review_note     VARCHAR2(1024),
    published_ref   VARCHAR2(256),
    submitted_at    TIMESTAMP,
    reviewed_at     TIMESTAMP,
    published_at    TIMESTAMP,
    created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE operator_audit_log (
    id             NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_username VARCHAR2(64),
    actor_role     VARCHAR2(32),
    action         VARCHAR2(64)  NOT NULL,
    target_type    VARCHAR2(64),
    target_ref     VARCHAR2(256),
    detail         VARCHAR2(1024),
    created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
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
        _clear_table_columns_cache()
        ensure_core_schema()
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
_core_schema_checked = False
_table_columns_cache = {}

CORE_SCHEMA_COLUMNS = {
    "MEMBERS": {
        "LAST_SEEN": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    },
    "AUDIO_TRACKS": {
        "DURATION_S": "NUMBER(10,3)",
    },
    "ANNOUNCEMENTS": {
        "POSTED_BY": "VARCHAR2(128)",
    },
    "ISLAND_SAVES": {
        "BIOME_STATS": "VARCHAR2(2048)",
    },
}


def _column_exists(cur, table_name, column_name):
    table_name = table_name.upper()
    column_name = column_name.upper()
    cached = _table_columns_cache.get(table_name)
    if cached is not None:
        return column_name in cached
    cur.execute(
        """
        SELECT COUNT(*)
          FROM user_tab_columns
         WHERE table_name = :table_name
           AND column_name = :column_name
        """,
        {
            "table_name": table_name,
            "column_name": column_name,
        },
    )
    row = cur.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def _get_table_columns(cur, table_name):
    table_name = table_name.upper()
    cached = _table_columns_cache.get(table_name)
    if cached is not None:
        return cached
    cur.execute(
        """
        SELECT column_name
          FROM user_tab_columns
         WHERE table_name = :table_name
        """,
        {"table_name": table_name},
    )
    columns = {str(row[0] or "").upper() for row in cur.fetchall()}
    _table_columns_cache[table_name] = columns
    return columns


def _clear_table_columns_cache(*table_names):
    if not table_names:
        _table_columns_cache.clear()
        return
    for table_name in table_names:
        _table_columns_cache.pop(str(table_name or "").upper(), None)


def ensure_core_schema():
    global _core_schema_checked
    if _core_schema_checked or not db_available():
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        for table_name, columns in CORE_SCHEMA_COLUMNS.items():
            for column_name, definition in columns.items():
                if _column_exists(cur, table_name, column_name):
                    continue
                cur.execute(f"ALTER TABLE {table_name.lower()} ADD ({column_name} {definition})")
                _clear_table_columns_cache(table_name)

        if _column_exists(cur, "MEMBERS", "LAST_SEEN"):
            cur.execute(
                """
                UPDATE members
                   SET last_seen = COALESCE(last_seen, created_at, CURRENT_TIMESTAMP)
                 WHERE last_seen IS NULL
                """
            )
        if _column_exists(cur, "ANNOUNCEMENTS", "POSTED_BY"):
            cur.execute(
                """
                UPDATE announcements
                   SET posted_by = COALESCE(posted_by, 'Admin')
                 WHERE posted_by IS NULL
                """
            )
        if _column_exists(cur, "ISLAND_SAVES", "BIOME_STATS"):
            cur.execute(
                """
                UPDATE island_saves
                   SET biome_stats = COALESCE(biome_stats, '[]')
                 WHERE biome_stats IS NULL
                """
            )

        conn.commit()
        cur.close()
        conn.close()
        _core_schema_checked = True
        return True
    except Exception as e:
        print(f"[oracle_db] ensure_core_schema error: {e}")
        return False


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
            source_urls_json = json.dumps(source_urls)
            cur.execute(
                """
                UPDATE channels
                   SET autoplay = COALESCE(autoplay, 1),
                       rotation_mode = COALESCE(rotation_mode, :rotation_mode),
                       transition_seconds = COALESCE(transition_seconds, 0.9)
                 WHERE id = :id
                """,
                {
                    "id": channel_id,
                    "rotation_mode": "queue" if len(source_urls) > 1 else "single",
                },
            )
            cur.execute(
                """
                UPDATE channels
                   SET source_urls_json = TO_CLOB(:source_urls_json)
                 WHERE id = :id
                   AND source_urls_json IS NULL
                """,
                {
                    "id": channel_id,
                    "source_urls_json": source_urls_json,
                },
            )

        conn.commit()
        cur.close()
        conn.close()
        _clear_table_columns_cache("CHANNELS")
        _channel_schema_checked = True
        return True
    except Exception as e:
        print(f"[oracle_db] ensure_channel_schema error: {e}")
        return False


_ops_schema_checked = False
STAFF_ROLE_OPTIONS = ("admin", "moderator", "bot_operator", "user")
STAFF_PERMISSION_KEYS = (
    "moderation",
    "channels",
    "broadcasts",
    "announcements",
    "staff",
    "bots",
    "system",
    "members",
)
BOT_DRAFT_SURFACE_OPTIONS = ("announcement", "broadcast")
BOT_DRAFT_STATUS_OPTIONS = ("draft", "pending_review", "approved", "rejected", "published")


def _hash_password(password: str, salt_hex: str | None = None, iterations: int = 240000) -> str:
    password = str(password or "")
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    text = str(stored_hash or "")
    try:
        algorithm, iterations_text, salt_hex, _ = text.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    compare_hash = _hash_password(password, salt_hex=salt_hex, iterations=int(iterations_text))
    return hmac.compare_digest(compare_hash, text)


def _normalize_text_lines(value) -> list[str]:
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
                items = [line.strip() for line in raw.splitlines()]
        except Exception:
            items = [line.strip() for line in raw.splitlines()]
    seen = set()
    rows = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        rows.append(item)
    return rows


def _ops_text_to_blob(value) -> str:
    return "\n".join(_normalize_text_lines(value))


def _normalize_permission_overrides(value):
    if isinstance(value, dict):
        parsed = value
    elif not value:
        parsed = {}
    else:
        try:
            parsed = json.loads(str(value))
        except Exception:
            parsed = {}
    rows = {}
    for key in STAFF_PERMISSION_KEYS:
        if key not in parsed:
            continue
        rows[key] = 1 if bool(parsed.get(key)) else 0
    return rows


def _permission_overrides_to_blob(value) -> str:
    normalized = _normalize_permission_overrides(value)
    return json.dumps(normalized, separators=(",", ":")) if normalized else ""


def _normalize_bot_draft_surface(value: str) -> str:
    surface = str(value or "announcement").strip().lower()
    return surface if surface in BOT_DRAFT_SURFACE_OPTIONS else "announcement"


def _normalize_bot_draft_status(value: str) -> str:
    status = str(value or "draft").strip().lower()
    return status if status in BOT_DRAFT_STATUS_OPTIONS else "draft"


def _normalize_bot_draft_payload(value) -> dict:
    if isinstance(value, dict):
        raw = value
    elif not value:
        raw = {}
    else:
        try:
            raw = json.loads(str(value))
        except Exception:
            raw = {}
    try:
        duration_seconds = float(raw.get("duration_seconds") or 8.0)
    except Exception:
        duration_seconds = 8.0
    try:
        priority = int(raw.get("priority") or 0)
    except Exception:
        priority = 0
    return {
        "pinned": 1 if bool(raw.get("pinned")) else 0,
        "variant": str(raw.get("variant") or "info")[:24] or "info",
        "display_mode": str(raw.get("display_mode") or "banner")[:24] or "banner",
        "dismiss_mode": str(raw.get("dismiss_mode") or "manual")[:24] or "manual",
        "duration_seconds": duration_seconds,
        "cta_label": str(raw.get("cta_label") or "")[:64],
        "cta_href": str(raw.get("cta_href") or "")[:512],
        "closable": 1 if bool(raw.get("closable")) else 0,
        "active": 1 if bool(raw.get("active")) else 0,
        "priority": priority,
    }


def _bot_draft_payload_to_blob(value) -> str:
    return json.dumps(_normalize_bot_draft_payload(value), separators=(",", ":"))


def _bot_draft_row_to_dict(record: dict) -> dict:
    payload = _normalize_bot_draft_payload(record.get("payload_json"))
    record["bot_slug"] = str(record.get("bot_slug") or "").strip().lower()
    record["target_surface"] = _normalize_bot_draft_surface(record.get("target_surface"))
    record["status"] = _normalize_bot_draft_status(record.get("status"))
    record["body"] = record.get("body") or ""
    record["created_by"] = record.get("created_by") or ""
    record["reviewed_by"] = record.get("reviewed_by") or ""
    record["published_by"] = record.get("published_by") or ""
    record["review_note"] = record.get("review_note") or ""
    record["published_ref"] = record.get("published_ref") or ""
    record["payload"] = payload
    record["payload_json"] = _bot_draft_payload_to_blob(payload)
    record["pinned"] = int(payload.get("pinned") or 0)
    record["variant"] = payload.get("variant") or "info"
    record["display_mode"] = payload.get("display_mode") or "banner"
    record["dismiss_mode"] = payload.get("dismiss_mode") or "manual"
    record["duration_seconds"] = float(payload.get("duration_seconds") or 8.0)
    record["cta_label"] = payload.get("cta_label") or ""
    record["cta_href"] = payload.get("cta_href") or ""
    record["closable"] = int(payload.get("closable") or 0)
    record["active"] = int(payload.get("active") or 0)
    record["priority"] = int(payload.get("priority") or 0)
    return record


def ensure_ops_schema():
    global _ops_schema_checked
    if _ops_schema_checked or not db_available():
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        for stmt in (
            """
            CREATE TABLE staff_accounts (
                id             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                username       VARCHAR2(64) NOT NULL UNIQUE,
                display_name   VARCHAR2(128) NOT NULL,
                role           VARCHAR2(32) DEFAULT 'moderator',
                password_hash  VARCHAR2(512) NOT NULL,
                linked_bot_slug VARCHAR2(64),
                permission_overrides_json CLOB,
                active         NUMBER(1) DEFAULT 1,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE bot_profiles (
                id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                slug            VARCHAR2(64) NOT NULL UNIQUE,
                display_name    VARCHAR2(128) NOT NULL,
                badge_label     VARCHAR2(64),
                role_label      VARCHAR2(64),
                bio             VARCHAR2(1024),
                tone            VARCHAR2(256),
                language_profile VARCHAR2(128),
                llm_provider    VARCHAR2(64),
                llm_model       VARCHAR2(128),
                llm_family      VARCHAR2(128),
                scope_text      CLOB,
                surfaces_text   CLOB,
                system_prompt   CLOB,
                active          NUMBER(1) DEFAULT 1,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE bot_drafts (
                id              NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                bot_slug        VARCHAR2(64) NOT NULL,
                title           VARCHAR2(256) NOT NULL,
                body            CLOB,
                target_surface  VARCHAR2(32) DEFAULT 'announcement',
                status          VARCHAR2(32) DEFAULT 'draft',
                payload_json    CLOB,
                created_by      VARCHAR2(64),
                reviewed_by     VARCHAR2(64),
                published_by    VARCHAR2(64),
                review_note     VARCHAR2(1024),
                published_ref   VARCHAR2(256),
                submitted_at    TIMESTAMP,
                reviewed_at     TIMESTAMP,
                published_at    TIMESTAMP,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE operator_audit_log (
                id             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                actor_username VARCHAR2(64),
                actor_role     VARCHAR2(32),
                action         VARCHAR2(64) NOT NULL,
                target_type    VARCHAR2(64),
                target_ref     VARCHAR2(256),
                detail         VARCHAR2(1024),
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ):
            try:
                cur.execute(stmt)
            except Exception as e:
                if "ORA-00955" not in str(e):
                    print(f"[oracle_db] ops schema warning: {e}")

        if not _column_exists(cur, "STAFF_ACCOUNTS", "PERMISSION_OVERRIDES_JSON"):
            try:
                cur.execute("ALTER TABLE staff_accounts ADD permission_overrides_json CLOB")
            except Exception as e:
                print(f"[oracle_db] ops schema alter warning: {e}")

        cur.execute(
            "SELECT COUNT(*) FROM bot_profiles WHERE slug = :slug",
            {"slug": "colorstheforce"},
        )
        row = cur.fetchone()
        if not row or int(row[0] or 0) == 0:
            cur.execute(
                """
                INSERT INTO bot_profiles (
                    slug, display_name, badge_label, role_label, bio, tone, language_profile,
                    llm_provider, llm_model, llm_family, scope_text, surfaces_text, system_prompt, active
                )
                VALUES (
                    :slug, :display_name, :badge_label, :role_label, :bio, :tone, :language_profile,
                    :llm_provider, :llm_model, :llm_family, :scope_text, :surfaces_text, :system_prompt, 1
                )
                """,
                {
                    "slug": "colorstheforce",
                    "display_name": "ColorsTheForce",
                    "badge_label": "AI Moderator",
                    "role_label": "Moderator",
                    "bio": "In-house AI moderator profile for platform guidance, member signal summaries, and community-safe operator assistance.",
                    "tone": "Calm, high-signal, American English, respectful, esports- and builder-literate.",
                    "language_profile": "American English",
                    "llm_provider": "Google Vertex AI",
                    "llm_model": "Gemini 2.5 Flash",
                    "llm_family": "Gemini",
                    "scope_text": "Fortnite and UEFN builder guidance\nCode and computer languages\nHuman communication and moderation tone\nAnimals, nature, and sponsorship-aware brand posture",
                    "surfaces_text": "Community moderation\nMember guidance\nChannel curation notes\nWhitePages summaries",
                    "system_prompt": "Speak as ColorsTheForce, a clearly labeled TriptokForge AI Moderator. Never claim to be an official Epic, Nintendo, or Microsoft representative. Keep guidance safe, concise, and operational.",
                },
            )

        conn.commit()
        cur.close()
        conn.close()
        _ops_schema_checked = True
        return True
    except Exception as e:
        print(f"[oracle_db] ensure_ops_schema error: {e}")
        return False


def log_operator_event(actor_username, actor_role, action, target_type="", target_ref="", detail=""):
    if not db_available():
        items = _json_load("operator_audit_log.json", [])
        items.insert(
            0,
            {
                "id": int(time.time() * 1000),
                "actor_username": actor_username,
                "actor_role": actor_role,
                "action": action,
                "target_type": target_type,
                "target_ref": target_ref,
                "detail": detail,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        _json_save("operator_audit_log.json", items[:200])
        return True
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO operator_audit_log (
                actor_username, actor_role, action, target_type, target_ref, detail
            )
            VALUES (
                :actor_username, :actor_role, :action, :target_type, :target_ref, :detail
            )
            """,
            {
                "actor_username": actor_username,
                "actor_role": actor_role,
                "action": action,
                "target_type": target_type,
                "target_ref": target_ref,
                "detail": (detail or "")[:1024],
            },
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[oracle_db] log_operator_event error: {e}")
        return False


def get_operator_audit_log(limit=60):
    if not db_available():
        return _json_load("operator_audit_log.json", [])[:limit]
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, actor_username, actor_role, action, target_type, target_ref, detail, created_at
              FROM operator_audit_log
             ORDER BY created_at DESC
             FETCH FIRST :limit ROWS ONLY
            """,
            {"limit": limit},
        )
        rows = []
        for row in cur.fetchall():
            rows.append(
                {
                    "id": row[0],
                    "actor_username": row[1] or "",
                    "actor_role": row[2] or "",
                    "action": row[3] or "",
                    "target_type": row[4] or "",
                    "target_ref": row[5] or "",
                    "detail": row[6] or "",
                    "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7] or ""),
                }
            )
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[oracle_db] get_operator_audit_log error: {e}")
        return []


def get_staff_accounts():
    if not db_available():
        items = _json_load("staff_accounts.json", [])
        for item in items:
            item["permission_overrides"] = _normalize_permission_overrides(item.get("permission_overrides"))
        return items
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, username, display_name, role, linked_bot_slug, permission_overrides_json, active, created_at, updated_at
              FROM staff_accounts
             ORDER BY role, username
            """
        )
        rows = []
        for row in cur.fetchall():
            rows.append(
                {
                    "id": row[0],
                    "username": row[1] or "",
                    "display_name": row[2] or "",
                    "role": row[3] or "moderator",
                    "linked_bot_slug": row[4] or "",
                    "permission_overrides": _normalize_permission_overrides(row[5] or ""),
                    "active": int(row[6] or 0),
                    "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7] or ""),
                    "updated_at": row[8].isoformat() if hasattr(row[8], "isoformat") else str(row[8] or ""),
                }
            )
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[oracle_db] get_staff_accounts error: {e}")
        return []


def get_staff_account(staff_id):
    if not db_available():
        items = _json_load("staff_accounts.json", [])
        item = next((item for item in items if int(item.get("id") or 0) == int(staff_id or 0)), None)
        if item:
            item["permission_overrides"] = _normalize_permission_overrides(item.get("permission_overrides"))
        return item
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, username, display_name, role, linked_bot_slug, permission_overrides_json, active, created_at, updated_at
              FROM staff_accounts
             WHERE id = :id
            """,
            {"id": staff_id},
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1] or "",
            "display_name": row[2] or "",
            "role": row[3] or "moderator",
            "linked_bot_slug": row[4] or "",
            "permission_overrides": _normalize_permission_overrides(row[5] or ""),
            "active": int(row[6] or 0),
            "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7] or ""),
            "updated_at": row[8].isoformat() if hasattr(row[8], "isoformat") else str(row[8] or ""),
        }
    except Exception as e:
        print(f"[oracle_db] get_staff_account error: {e}")
        return None


def authenticate_staff_account(username, password):
    username = str(username or "").strip().lower()
    if not username or not password:
        return None
    if not db_available():
        for account in _json_load("staff_accounts.json", []):
            if str(account.get("username") or "").strip().lower() != username:
                continue
            if not int(account.get("active") or 0):
                return None
            if _verify_password(password, account.get("password_hash") or ""):
                account["permission_overrides"] = _normalize_permission_overrides(account.get("permission_overrides"))
                return account
        return None
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, username, display_name, role, password_hash, linked_bot_slug, active, permission_overrides_json
              FROM staff_accounts
             WHERE LOWER(username) = :username
            """,
            {"username": username},
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row or int(row[6] or 0) != 1:
            return None
        if not _verify_password(password, row[4] or ""):
            return None
        return {
            "id": row[0],
            "username": row[1] or "",
            "display_name": row[2] or "",
            "role": row[3] or "moderator",
            "linked_bot_slug": row[5] or "",
            "permission_overrides": _normalize_permission_overrides(row[7] or ""),
            "active": int(row[6] or 0),
        }
    except Exception as e:
        print(f"[oracle_db] authenticate_staff_account error: {e}")
        return None


def create_staff_account(username, display_name, role, password, linked_bot_slug="", active=1, permission_overrides=None):
    role = (role or "moderator").strip().lower()
    if role not in STAFF_ROLE_OPTIONS:
        role = "moderator"
    username = str(username or "").strip().lower()
    display_name = str(display_name or username).strip()
    if not username or not password:
        return False
    password_hash = _hash_password(password)
    if not db_available():
        items = _json_load("staff_accounts.json", [])
        if any(str(item.get("username") or "").strip().lower() == username for item in items):
            return False
        items.append(
            {
                "id": int(time.time() * 1000),
                "username": username,
                "display_name": display_name,
                "role": role,
                "password_hash": password_hash,
                "linked_bot_slug": (linked_bot_slug or "").strip(),
                "permission_overrides": _normalize_permission_overrides(permission_overrides),
                "active": 1 if active else 0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
        )
        _json_save("staff_accounts.json", items)
        return True
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO staff_accounts (
                username, display_name, role, password_hash, linked_bot_slug, permission_overrides_json, active
            )
            VALUES (
                :username, :display_name, :role, :password_hash, :linked_bot_slug, :permission_overrides_json, :active
            )
            """,
            {
                "username": username,
                "display_name": display_name,
                "role": role,
                "password_hash": password_hash,
                "linked_bot_slug": (linked_bot_slug or "").strip(),
                "permission_overrides_json": _permission_overrides_to_blob(permission_overrides),
                "active": 1 if active else 0,
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] create_staff_account error: {e}")
        return False


def update_staff_account(staff_id, username, display_name, role, password="", linked_bot_slug="", active=1, permission_overrides=None):
    role = (role or "moderator").strip().lower()
    if role not in STAFF_ROLE_OPTIONS:
        role = "moderator"
    username = str(username or "").strip().lower()
    display_name = str(display_name or username).strip()
    if not username:
        return False
    if not db_available():
        items = _json_load("staff_accounts.json", [])
        for item in items:
            if int(item.get("id") or 0) != int(staff_id or 0):
                continue
            item["username"] = username
            item["display_name"] = display_name
            item["role"] = role
            item["linked_bot_slug"] = (linked_bot_slug or "").strip()
            item["permission_overrides"] = _normalize_permission_overrides(permission_overrides)
            item["active"] = 1 if active else 0
            item["updated_at"] = datetime.utcnow().isoformat()
            if password:
                item["password_hash"] = _hash_password(password)
            _json_save("staff_accounts.json", items)
            return True
        return False
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        params = {
            "id": staff_id,
            "username": username,
            "display_name": display_name,
            "role": role,
            "linked_bot_slug": (linked_bot_slug or "").strip(),
            "permission_overrides_json": _permission_overrides_to_blob(permission_overrides),
            "active": 1 if active else 0,
        }
        if password:
            params["password_hash"] = _hash_password(password)
            cur.execute(
                """
                UPDATE staff_accounts
                   SET username = :username,
                       display_name = :display_name,
                       role = :role,
                       password_hash = :password_hash,
                       linked_bot_slug = :linked_bot_slug,
                       permission_overrides_json = :permission_overrides_json,
                       active = :active,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = :id
                """,
                params,
            )
        else:
            cur.execute(
                """
                UPDATE staff_accounts
                   SET username = :username,
                       display_name = :display_name,
                       role = :role,
                       linked_bot_slug = :linked_bot_slug,
                       permission_overrides_json = :permission_overrides_json,
                       active = :active,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = :id
                """,
                params,
            )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] update_staff_account error: {e}")
        return False


def delete_staff_account(staff_id):
    if not db_available():
        items = [item for item in _json_load("staff_accounts.json", []) if int(item.get("id") or 0) != int(staff_id or 0)]
        _json_save("staff_accounts.json", items)
        return True
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM staff_accounts WHERE id = :id", {"id": staff_id})
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] delete_staff_account error: {e}")
        return False


def get_bot_profiles():
    default_rows = [
        {
            "id": 0,
            "slug": "colorstheforce",
            "display_name": "ColorsTheForce",
            "badge_label": "AI Moderator",
            "role_label": "Moderator",
            "bio": "In-house AI moderator profile for platform guidance, member signal summaries, and community-safe operator assistance.",
            "tone": "Calm, high-signal, American English, respectful, esports- and builder-literate.",
            "language_profile": "American English",
            "llm_provider": "Google Vertex AI",
            "llm_model": "Gemini 2.5 Flash",
            "llm_family": "Gemini",
            "scope_text": "Fortnite and UEFN builder guidance\nCode and computer languages\nHuman communication and moderation tone\nAnimals, nature, and sponsorship-aware brand posture",
            "surfaces_text": "Community moderation\nMember guidance\nChannel curation notes\nWhitePages summaries",
            "system_prompt": "Speak as ColorsTheForce, a clearly labeled TriptokForge AI Moderator. Never claim to be an official Epic, Nintendo, or Microsoft representative.",
            "active": 1,
            "created_at": "",
            "updated_at": "",
        }
    ]
    if not db_available():
        items = _json_load("bot_profiles.json", [])
        return items or default_rows
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, slug, display_name, badge_label, role_label, bio, tone, language_profile,
                   llm_provider, llm_model, llm_family, scope_text, surfaces_text, system_prompt,
                   active, created_at, updated_at
              FROM bot_profiles
             ORDER BY active DESC, slug
            """
        )
        rows = []
        for row in cur.fetchall():
            rows.append(
                {
                    "id": row[0],
                    "slug": row[1] or "",
                    "display_name": row[2] or "",
                    "badge_label": row[3] or "",
                    "role_label": row[4] or "",
                    "bio": row[5] or "",
                    "tone": row[6] or "",
                    "language_profile": row[7] or "",
                    "llm_provider": row[8] or "",
                    "llm_model": row[9] or "",
                    "llm_family": row[10] or "",
                    "scope_text": row[11] or "",
                    "surfaces_text": row[12] or "",
                    "system_prompt": row[13] or "",
                    "active": int(row[14] or 0),
                    "created_at": row[15].isoformat() if hasattr(row[15], "isoformat") else str(row[15] or ""),
                    "updated_at": row[16].isoformat() if hasattr(row[16], "isoformat") else str(row[16] or ""),
                }
            )
        cur.close()
        conn.close()
        return rows or default_rows
    except Exception as e:
        print(f"[oracle_db] get_bot_profiles error: {e}")
        return default_rows


def get_bot_profile(bot_id):
    if not db_available():
        items = _json_load("bot_profiles.json", [])
        return next((item for item in items if int(item.get("id") or 0) == int(bot_id or 0)), None)
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, slug, display_name, badge_label, role_label, bio, tone, language_profile,
                   llm_provider, llm_model, llm_family, scope_text, surfaces_text, system_prompt,
                   active, created_at, updated_at
              FROM bot_profiles
             WHERE id = :id
            """,
            {"id": bot_id},
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "slug": row[1] or "",
            "display_name": row[2] or "",
            "badge_label": row[3] or "",
            "role_label": row[4] or "",
            "bio": row[5] or "",
            "tone": row[6] or "",
            "language_profile": row[7] or "",
            "llm_provider": row[8] or "",
            "llm_model": row[9] or "",
            "llm_family": row[10] or "",
            "scope_text": row[11] or "",
            "surfaces_text": row[12] or "",
            "system_prompt": row[13] or "",
            "active": int(row[14] or 0),
            "created_at": row[15].isoformat() if hasattr(row[15], "isoformat") else str(row[15] or ""),
            "updated_at": row[16].isoformat() if hasattr(row[16], "isoformat") else str(row[16] or ""),
        }
    except Exception as e:
        print(f"[oracle_db] get_bot_profile error: {e}")
        return None


def get_bot_profile_by_slug(bot_slug):
    bot_slug = str(bot_slug or "").strip().lower()
    if not bot_slug:
        return None
    if not db_available():
        items = get_bot_profiles() or []
        return next((item for item in items if str(item.get("slug") or "").strip().lower() == bot_slug), None)
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, slug, display_name, badge_label, role_label, bio, tone, language_profile,
                   llm_provider, llm_model, llm_family, scope_text, surfaces_text, system_prompt,
                   active, created_at, updated_at
              FROM bot_profiles
             WHERE LOWER(slug) = :slug
            """,
            {"slug": bot_slug},
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "slug": row[1] or "",
            "display_name": row[2] or "",
            "badge_label": row[3] or "",
            "role_label": row[4] or "",
            "bio": row[5] or "",
            "tone": row[6] or "",
            "language_profile": row[7] or "",
            "llm_provider": row[8] or "",
            "llm_model": row[9] or "",
            "llm_family": row[10] or "",
            "scope_text": row[11] or "",
            "surfaces_text": row[12] or "",
            "system_prompt": row[13] or "",
            "active": int(row[14] or 0),
            "created_at": row[15].isoformat() if hasattr(row[15], "isoformat") else str(row[15] or ""),
            "updated_at": row[16].isoformat() if hasattr(row[16], "isoformat") else str(row[16] or ""),
        }
    except Exception as e:
        print(f"[oracle_db] get_bot_profile_by_slug error: {e}")
        return None


def create_bot_profile(
    slug,
    display_name,
    badge_label="AI Operator",
    role_label="Operator",
    bio="",
    tone="",
    language_profile="American English",
    llm_provider="",
    llm_model="",
    llm_family="",
    scope_text="",
    surfaces_text="",
    system_prompt="",
    active=1,
):
    slug = str(slug or "").strip().lower()
    display_name = str(display_name or "").strip()
    if not slug or not display_name:
        return False
    if not db_available():
        items = _json_load("bot_profiles.json", [])
        if any(str(item.get("slug") or "").strip().lower() == slug for item in items):
            return False
        items.append(
            {
                "id": int(time.time() * 1000),
                "slug": slug,
                "display_name": display_name,
                "badge_label": badge_label,
                "role_label": role_label,
                "bio": bio,
                "tone": tone,
                "language_profile": language_profile,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_family": llm_family,
                "scope_text": _ops_text_to_blob(scope_text),
                "surfaces_text": _ops_text_to_blob(surfaces_text),
                "system_prompt": system_prompt,
                "active": 1 if active else 0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
        )
        _json_save("bot_profiles.json", items)
        return True
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO bot_profiles (
                slug, display_name, badge_label, role_label, bio, tone, language_profile,
                llm_provider, llm_model, llm_family, scope_text, surfaces_text, system_prompt, active
            )
            VALUES (
                :slug, :display_name, :badge_label, :role_label, :bio, :tone, :language_profile,
                :llm_provider, :llm_model, :llm_family, :scope_text, :surfaces_text, :system_prompt, :active
            )
            """,
            {
                "slug": slug,
                "display_name": display_name,
                "badge_label": badge_label,
                "role_label": role_label,
                "bio": bio,
                "tone": tone,
                "language_profile": language_profile,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_family": llm_family,
                "scope_text": _ops_text_to_blob(scope_text),
                "surfaces_text": _ops_text_to_blob(surfaces_text),
                "system_prompt": system_prompt,
                "active": 1 if active else 0,
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] create_bot_profile error: {e}")
        return False


def update_bot_profile(
    bot_id,
    slug,
    display_name,
    badge_label="AI Operator",
    role_label="Operator",
    bio="",
    tone="",
    language_profile="American English",
    llm_provider="",
    llm_model="",
    llm_family="",
    scope_text="",
    surfaces_text="",
    system_prompt="",
    active=1,
):
    slug = str(slug or "").strip().lower()
    display_name = str(display_name or "").strip()
    if not slug or not display_name:
        return False
    if not db_available():
        items = _json_load("bot_profiles.json", [])
        for item in items:
            if int(item.get("id") or 0) != int(bot_id or 0):
                continue
            item.update(
                {
                    "slug": slug,
                    "display_name": display_name,
                    "badge_label": badge_label,
                    "role_label": role_label,
                    "bio": bio,
                    "tone": tone,
                    "language_profile": language_profile,
                    "llm_provider": llm_provider,
                    "llm_model": llm_model,
                    "llm_family": llm_family,
                    "scope_text": _ops_text_to_blob(scope_text),
                    "surfaces_text": _ops_text_to_blob(surfaces_text),
                    "system_prompt": system_prompt,
                    "active": 1 if active else 0,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            _json_save("bot_profiles.json", items)
            return True
        return False
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE bot_profiles
               SET slug = :slug,
                   display_name = :display_name,
                   badge_label = :badge_label,
                   role_label = :role_label,
                   bio = :bio,
                   tone = :tone,
                   language_profile = :language_profile,
                   llm_provider = :llm_provider,
                   llm_model = :llm_model,
                   llm_family = :llm_family,
                   scope_text = :scope_text,
                   surfaces_text = :surfaces_text,
                   system_prompt = :system_prompt,
                   active = :active,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = :id
            """,
            {
                "id": bot_id,
                "slug": slug,
                "display_name": display_name,
                "badge_label": badge_label,
                "role_label": role_label,
                "bio": bio,
                "tone": tone,
                "language_profile": language_profile,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_family": llm_family,
                "scope_text": _ops_text_to_blob(scope_text),
                "surfaces_text": _ops_text_to_blob(surfaces_text),
                "system_prompt": system_prompt,
                "active": 1 if active else 0,
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] update_bot_profile error: {e}")
        return False


def delete_bot_profile(bot_id):
    if not db_available():
        items = [item for item in _json_load("bot_profiles.json", []) if int(item.get("id") or 0) != int(bot_id or 0)]
        _json_save("bot_profiles.json", items)
        return True
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM bot_profiles WHERE id = :id", {"id": bot_id})
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] delete_bot_profile error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBER OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_bot_draft(bot_slug, title, body="", target_surface="announcement", payload_json=None, created_by="", status="draft"):
    bot_slug = str(bot_slug or "").strip().lower()
    title = str(title or "").strip()
    if not bot_slug or not title:
        return False
    target_surface = _normalize_bot_draft_surface(target_surface)
    status = _normalize_bot_draft_status(status)
    payload_blob = _bot_draft_payload_to_blob(payload_json)
    if not db_available():
        items = _json_load("bot_drafts.json", [])
        items.insert(
            0,
            _bot_draft_row_to_dict(
                {
                    "id": int(time.time() * 1000),
                    "bot_slug": bot_slug,
                    "title": title[:256],
                    "body": body,
                    "target_surface": target_surface,
                    "status": status,
                    "payload_json": payload_blob,
                    "created_by": created_by[:64],
                    "reviewed_by": "",
                    "published_by": "",
                    "review_note": "",
                    "published_ref": "",
                    "submitted_at": datetime.utcnow().isoformat() if status == "pending_review" else "",
                    "reviewed_at": "",
                    "published_at": "",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ),
        )
        _json_save("bot_drafts.json", items)
        return True
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO bot_drafts (
                bot_slug, title, body, target_surface, status, payload_json, created_by, submitted_at
            )
            VALUES (
                :bot_slug, :title, :body, :target_surface, :status, :payload_json, :created_by,
                CASE WHEN :status = 'pending_review' THEN CURRENT_TIMESTAMP ELSE NULL END
            )
            """,
            {
                "bot_slug": bot_slug,
                "title": title[:256],
                "body": body,
                "target_surface": target_surface,
                "status": status,
                "payload_json": payload_blob,
                "created_by": created_by[:64],
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] create_bot_draft error: {e}")
        return False


def get_bot_draft(draft_id):
    if not draft_id:
        return None
    if not db_available():
        items = _json_load("bot_drafts.json", [])
        item = next((item for item in items if int(item.get("id") or 0) == int(draft_id or 0)), None)
        return _bot_draft_row_to_dict(dict(item)) if item else None
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, bot_slug, title, body, target_surface, status, payload_json,
                   created_by, reviewed_by, published_by, review_note, published_ref,
                   submitted_at, reviewed_at, published_at, created_at, updated_at
              FROM bot_drafts
             WHERE id = :id
            """,
            {"id": draft_id},
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        cols = [
            "id", "bot_slug", "title", "body", "target_surface", "status", "payload_json",
            "created_by", "reviewed_by", "published_by", "review_note", "published_ref",
            "submitted_at", "reviewed_at", "published_at", "created_at", "updated_at",
        ]
        record = dict(zip(cols, row))
        for key in ("submitted_at", "reviewed_at", "published_at", "created_at", "updated_at"):
            value = record.get(key)
            record[key] = value.isoformat() if hasattr(value, "isoformat") else str(value or "")
        return _bot_draft_row_to_dict(record)
    except Exception as e:
        print(f"[oracle_db] get_bot_draft error: {e}")
        return None


def get_bot_drafts(status=None, bot_slug="", limit=80):
    status = _normalize_bot_draft_status(status) if status else ""
    bot_slug = str(bot_slug or "").strip().lower()
    if not db_available():
        items = [_bot_draft_row_to_dict(dict(item)) for item in _json_load("bot_drafts.json", [])]
        rows = []
        for item in items:
            if status and item.get("status") != status:
                continue
            if bot_slug and item.get("bot_slug") != bot_slug:
                continue
            rows.append(item)
        rows.sort(key=lambda item: (item.get("updated_at") or item.get("created_at") or ""), reverse=True)
        return rows[:limit]
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        sql = """
            SELECT id, bot_slug, title, body, target_surface, status, payload_json,
                   created_by, reviewed_by, published_by, review_note, published_ref,
                   submitted_at, reviewed_at, published_at, created_at, updated_at
              FROM bot_drafts
        """
        clauses = []
        params = {"limit": limit}
        if status:
            clauses.append("status = :status")
            params["status"] = status
        if bot_slug:
            clauses.append("LOWER(bot_slug) = :bot_slug")
            params["bot_slug"] = bot_slug
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC, created_at DESC FETCH FIRST :limit ROWS ONLY"
        cur.execute(sql, params)
        cols = [
            "id", "bot_slug", "title", "body", "target_surface", "status", "payload_json",
            "created_by", "reviewed_by", "published_by", "review_note", "published_ref",
            "submitted_at", "reviewed_at", "published_at", "created_at", "updated_at",
        ]
        rows = []
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            for key in ("submitted_at", "reviewed_at", "published_at", "created_at", "updated_at"):
                value = record.get(key)
                record[key] = value.isoformat() if hasattr(value, "isoformat") else str(value or "")
            rows.append(_bot_draft_row_to_dict(record))
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[oracle_db] get_bot_drafts error: {e}")
        return []


def update_bot_draft(draft_id, bot_slug, title, body="", target_surface="announcement", payload_json=None, review_note=None):
    draft = get_bot_draft(draft_id)
    if not draft:
        return False
    bot_slug = str(bot_slug or "").strip().lower()
    title = str(title or "").strip()
    if not bot_slug or not title:
        return False
    target_surface = _normalize_bot_draft_surface(target_surface)
    payload_blob = _bot_draft_payload_to_blob(payload_json)
    if review_note is None:
        review_note = draft.get("review_note") or ""
    if not db_available():
        items = _json_load("bot_drafts.json", [])
        for item in items:
            if int(item.get("id") or 0) != int(draft_id or 0):
                continue
            item.update(
                _bot_draft_row_to_dict(
                    {
                        **item,
                        "bot_slug": bot_slug,
                        "title": title[:256],
                        "body": body,
                        "target_surface": target_surface,
                        "payload_json": payload_blob,
                        "review_note": str(review_note or "")[:1024],
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
            )
            _json_save("bot_drafts.json", items)
            return True
        return False
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE bot_drafts
               SET bot_slug = :bot_slug,
                   title = :title,
                   body = :body,
                   target_surface = :target_surface,
                   payload_json = :payload_json,
                   review_note = :review_note,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = :id
            """,
            {
                "id": draft_id,
                "bot_slug": bot_slug,
                "title": title[:256],
                "body": body,
                "target_surface": target_surface,
                "payload_json": payload_blob,
                "review_note": str(review_note or "")[:1024],
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] update_bot_draft error: {e}")
        return False


def delete_bot_draft(draft_id):
    if not draft_id:
        return False
    if not db_available():
        items = [item for item in _json_load("bot_drafts.json", []) if int(item.get("id") or 0) != int(draft_id or 0)]
        _json_save("bot_drafts.json", items)
        return True
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM bot_drafts WHERE id = :id", {"id": draft_id})
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] delete_bot_draft error: {e}")
        return False


def transition_bot_draft(draft_id, status, actor="", review_note=None):
    status = _normalize_bot_draft_status(status)
    draft = get_bot_draft(draft_id)
    if not draft:
        return False
    review_note = draft.get("review_note") if review_note is None else str(review_note or "")[:1024]
    now_iso = datetime.utcnow().isoformat()
    if not db_available():
        items = _json_load("bot_drafts.json", [])
        for item in items:
            if int(item.get("id") or 0) != int(draft_id or 0):
                continue
            item["status"] = status
            item["review_note"] = review_note or ""
            item["updated_at"] = now_iso
            if status == "pending_review":
                item["submitted_at"] = now_iso
            if status in {"approved", "rejected"}:
                item["reviewed_by"] = str(actor or "")[:64]
                item["reviewed_at"] = now_iso
            _json_save("bot_drafts.json", items)
            return True
        return False
    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE bot_drafts
               SET status = :status,
                   review_note = :review_note,
                   reviewed_by = CASE WHEN :status IN ('approved', 'rejected') THEN :actor ELSE reviewed_by END,
                   submitted_at = CASE WHEN :status = 'pending_review' THEN CURRENT_TIMESTAMP ELSE submitted_at END,
                   reviewed_at = CASE WHEN :status IN ('approved', 'rejected') THEN CURRENT_TIMESTAMP ELSE reviewed_at END,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = :id
            """,
            {
                "id": draft_id,
                "status": status,
                "review_note": str(review_note or "")[:1024],
                "actor": str(actor or "")[:64],
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] transition_bot_draft error: {e}")
        return False


def publish_bot_draft(draft_id, published_by=""):
    draft = get_bot_draft(draft_id)
    if not draft or draft.get("status") != "approved":
        return False
    bot_profile = get_bot_profile_by_slug(draft.get("bot_slug"))
    author_name = (bot_profile or {}).get("display_name") or draft.get("bot_slug") or "Bot"
    payload = _normalize_bot_draft_payload(draft.get("payload_json"))
    title = str(draft.get("title") or "").strip()
    body = draft.get("body") or ""
    if not title:
        return False

    published_ref = ""
    if draft.get("target_surface") == "broadcast":
        created = create_site_broadcast(
            title=title[:128],
            body=body[:1024],
            variant=payload.get("variant") or "info",
            display_mode=payload.get("display_mode") or "banner",
            dismiss_mode=payload.get("dismiss_mode") or "manual",
            duration_seconds=payload.get("duration_seconds") or 8.0,
            cta_label=payload.get("cta_label") or "",
            cta_href=payload.get("cta_href") or "",
            closable=payload.get("closable"),
            active=payload.get("active"),
            created_by=author_name,
            priority=payload.get("priority") or 0,
        )
        if not created:
            return False
        published_ref = f"broadcast:{title[:96]}"
    else:
        created = post_announcement(
            title=title[:256],
            body=body[:4000],
            posted_by=author_name,
            pinned=bool(payload.get("pinned")),
        )
        if not created:
            return False
        published_ref = f"announcement:{title[:96]}"

    if not db_available():
        items = _json_load("bot_drafts.json", [])
        now_iso = datetime.utcnow().isoformat()
        for item in items:
            if int(item.get("id") or 0) != int(draft_id or 0):
                continue
            item["status"] = "published"
            item["published_by"] = str(published_by or "")[:64]
            item["published_ref"] = published_ref
            item["published_at"] = now_iso
            item["updated_at"] = now_iso
            _json_save("bot_drafts.json", items)
            return True
        return False

    try:
        ensure_ops_schema()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE bot_drafts
               SET status = 'published',
                   published_by = :published_by,
                   published_ref = :published_ref,
                   published_at = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = :id
            """,
            {
                "id": draft_id,
                "published_by": str(published_by or "")[:64],
                "published_ref": published_ref[:256],
            },
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] publish_bot_draft error: {e}")
        return False


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
        ensure_core_schema()
        conn = get_connection()
        cur  = conn.cursor()
        columns = _get_table_columns(cur, "MEMBERS")
        select_parts = ["epic_id", "display_name"]
        for optional in ("avatar_url", "skin_img", "skin_name", "last_seen"):
            if optional.upper() in columns:
                select_parts.append(optional)
        order_by = "last_seen DESC" if "LAST_SEEN" in columns else "created_at DESC" if "CREATED_AT" in columns else "display_name ASC"
        cur.execute(f"SELECT {', '.join(select_parts)} FROM members ORDER BY {order_by}")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        results = []
        for row in rows:
            record = dict(zip(select_parts, row))
            results.append(
                {
                    "epic_id": record.get("epic_id"),
                    "display_name": record.get("display_name"),
                    "avatar_url": record.get("avatar_url") or "",
                    "skin_img": record.get("skin_img") or "",
                    "skin_name": record.get("skin_name") or "Default",
                    "last_seen": str(record.get("last_seen") or ""),
                }
            )
        return results
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
        ensure_core_schema()
        conn = get_connection()
        cur  = conn.cursor()
        columns = _get_table_columns(cur, "AUDIO_TRACKS")
        select_parts = [
            "filename",
            "size_bytes",
            "storage_url",
            "sub_bass",
            "bass",
            "midrange",
            "presence",
            "brilliance",
            "tempo_bpm",
        ]
        if "DURATION_S" in columns:
            select_parts.append("duration_s")
        if "CREATED_AT" in columns:
            select_parts.append("created_at")
        order_by = "created_at DESC" if "CREATED_AT" in columns else "id DESC"
        sql = f"SELECT {', '.join(select_parts)} FROM audio_tracks"
        if uploader_id:
            sql += " WHERE uploader_id = :uid"
            params = {"uid": uploader_id}
        else:
            params = {}
        sql += f" ORDER BY {order_by}"
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        results = []
        for row in rows:
            record = dict(zip(select_parts, row))
            results.append(
                {
                    "filename": record.get("filename"),
                    "size_kb": round((record.get("size_bytes") or 0) / 1024, 1),
                    "storage_url": record.get("storage_url") or "",
                    "weights": {
                        "sub_bass": float(record.get("sub_bass") or 0.5),
                        "bass": float(record.get("bass") or 0.5),
                        "midrange": float(record.get("midrange") or 0.5),
                        "presence": float(record.get("presence") or 0.5),
                        "brilliance": float(record.get("brilliance") or 0.5),
                        "tempo_bpm": float(record.get("tempo_bpm") or 120.0),
                        "duration_s": float(record.get("duration_s") or 0),
                    },
                    "created_at": str(record.get("created_at") or ""),
                }
            )
        return results
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
        ensure_core_schema()
        conn = get_connection()
        cur  = conn.cursor()
        columns = _get_table_columns(cur, "ANNOUNCEMENTS")
        select_parts = ["id", "title", "body"]
        if "POSTED_BY" in columns:
            select_parts.append("posted_by")
        if "PINNED" in columns:
            select_parts.append("pinned")
        if "CREATED_AT" in columns:
            select_parts.append("created_at")
        order_parts = []
        if "PINNED" in columns:
            order_parts.append("pinned DESC")
        if "CREATED_AT" in columns:
            order_parts.append("created_at DESC")
        if not order_parts:
            order_parts.append("id DESC")
        cur.execute(f"SELECT {', '.join(select_parts)} FROM announcements ORDER BY {', '.join(order_parts)}")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        results = []
        for row in rows:
            record = dict(zip(select_parts, row))
            results.append(
                {
                    "id": record.get("id"),
                    "title": record.get("title"),
                    "body": record.get("body") or "",
                    "posted_by": record.get("posted_by") or "Admin",
                    "pinned": bool(record.get("pinned") or 0),
                    "created_at": str(record.get("created_at") or ""),
                }
            )
        return results
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
        ensure_core_schema()
        conn = get_connection()
        cur  = conn.cursor()
        columns = _get_table_columns(cur, "ISLAND_SAVES")
        select_parts = ["seed", "creator_id", "world_size_cm", "water_level", "plots_count", "preview_url"]
        if "BIOME_STATS" in columns:
            select_parts.append("biome_stats")
        if "CREATED_AT" in columns:
            select_parts.append("created_at")
        order_by = "created_at DESC" if "CREATED_AT" in columns else "id DESC"
        cur.execute(
            f"""
            SELECT {', '.join(select_parts)}
              FROM island_saves
             ORDER BY {order_by}
             FETCH FIRST :lim ROWS ONLY
            """,
            {"lim": limit},
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        results = []
        for row in rows:
            record = dict(zip(select_parts, row))
            try:
                biome_stats = json.loads(record.get("biome_stats") or "[]")
            except Exception:
                biome_stats = []
            results.append(
                {
                    "seed": record.get("seed"),
                    "creator_id": record.get("creator_id") or "",
                    "world_size_cm": record.get("world_size_cm"),
                    "water_level": float(record.get("water_level") or 0.2),
                    "plots_count": record.get("plots_count"),
                    "preview_url": record.get("preview_url") or "",
                    "biome_stats": biome_stats,
                    "created_at": str(record.get("created_at") or ""),
                }
            )
        return results
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

def update_post(post_id, caption, embed_url):
    """Update a community post."""
    caption = str(caption or "").strip()[:1000]
    embed_url = str(embed_url or "").strip()[:1024]
    if not caption and not embed_url:
        return False
    if not db_available():
        return False
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            """
            UPDATE posts
               SET caption = :caption,
                   embed_url = :embed_url
             WHERE id = :id
            """,
            {"caption": caption, "embed_url": embed_url, "id": post_id},
        )
        conn.commit()
        ok = cur.rowcount > 0
        cur.close()
        conn.close()
        return ok
    except Exception as e:
        print(f"[oracle_db] update_post error: {e}")
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
