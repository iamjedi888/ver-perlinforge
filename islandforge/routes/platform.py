from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
import os
from oracle_db import (
    authenticate_staff_account,
    create_bot_draft,
    create_site_broadcast,
    create_channel,
    create_staff_account,
    create_bot_profile,
    delete_bot_draft,
    delete_bot_profile,
    delete_channel,
    delete_post,
    delete_staff_account,
    delete_site_broadcast,
    get_all_members,
    get_announcements,
    get_audio_tracks,
    get_bot_profile,
    get_bot_profile_by_slug,
    get_bot_draft,
    get_bot_drafts,
    get_bot_profiles,
    get_channel,
    get_channels,
    get_member_islands,
    get_member_room,
    get_member_tickets,
    get_operator_audit_log,
    get_posts,
    get_recent_islands,
    get_site_broadcast,
    get_site_broadcasts,
    get_staff_account,
    get_staff_accounts,
    get_wp_tracks,
    log_operator_event,
    post_announcement,
    set_site_broadcast_active,
    status,
    STAFF_ROLE_OPTIONS,
    transition_bot_draft,
    update_channel,
    update_bot_draft,
    update_post,
    update_staff_account,
    update_site_broadcast,
    update_bot_profile,
    approve_channel,
    publish_bot_draft,
)

platform_bp = Blueprint("platform", __name__)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "triptokadmin2026")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMON_CHANNEL_CATEGORIES = [
    "Fortnite Competitive",
    "Game Developers",
    "Esports",
    "Creative / UEFN",
    "Gaming News",
    "Community Picks",
    "Chill Gaming",
    "Chill / Music",
]
CHANNEL_PROVIDER_HINTS = [
    "youtube",
    "twitch",
    "kick",
    "streamable",
    "mixed",
]
CHANNEL_ROTATION_MODES = [
    "single",
    "queue",
    "random_pool",
]
BROADCAST_VARIANTS = [
    "info",
    "success",
    "warning",
    "critical",
]
BROADCAST_DISPLAY_MODES = [
    "banner",
    "ticker",
    "blip",
    "modal",
]
BROADCAST_DISMISS_MODES = [
    "auto",
    "manual",
    "persistent",
]
STAFF_ROLE_LABELS = {
    "admin": "Admin",
    "moderator": "Moderator",
    "bot_operator": "Bot Operator",
    "user": "User",
}
STAFF_PERMISSION_LABELS = {
    "moderation": "Moderate posts",
    "channels": "Manage channels",
    "broadcasts": "Manage sitewide broadcasts",
    "announcements": "Publish announcements",
    "staff": "Create and edit staff profiles",
    "bots": "Edit bot profiles",
    "system": "View system-level controls",
    "members": "Member directory and account controls",
}
STAFF_ROLE_DEFAULTS = {
    "admin": {
        "moderation": 1,
        "channels": 1,
        "broadcasts": 1,
        "announcements": 1,
        "staff": 1,
        "bots": 1,
        "system": 1,
        "members": 1,
    },
    "moderator": {
        "moderation": 1,
    },
    "bot_operator": {
        "bots": 1,
    },
    "user": {},
}
BOT_PROVIDER_CATALOG = [
    {
        "provider": "OpenAI",
        "family": "GPT",
        "models": ["GPT-5", "GPT-5 mini", "GPT-5 nano"],
        "notes": "Strong general reasoning, writing, coding, and tool-using assistants for premium operator workflows.",
        "source": "https://platform.openai.com/docs/guides/models",
    },
    {
        "provider": "Google Vertex AI",
        "family": "Gemini",
        "models": ["Gemini 2.5 Pro", "Gemini 2.5 Flash", "Gemini 2.5 Flash-Lite"],
        "notes": "Strong multimodal and reasoning surface for ops copilots and moderation summaries.",
        "source": "https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models",
    },
    {
        "provider": "Anthropic",
        "family": "Claude",
        "models": ["Claude Sonnet", "Claude Haiku", "Claude Opus"],
        "notes": "High-signal writing and safety-friendly assistants for moderation, summaries, and operator guidance.",
        "source": "https://docs.anthropic.com/en/docs/about-claude/models",
    },
    {
        "provider": "IBM watsonx.ai",
        "family": "Granite + partner models",
        "models": ["Granite 3.3 8B Instruct", "Granite Guardian", "Meta Llama family on watsonx"],
        "notes": "Enterprise governance posture with Granite and partner-hosted model options.",
        "source": "https://www.ibm.com/products/watsonx-ai",
    },
    {
        "provider": "Amazon Bedrock",
        "family": "Foundation model gateway",
        "models": ["Anthropic Claude via Bedrock", "Meta Llama via Bedrock", "Amazon Nova"],
        "notes": "Useful if you want one managed provider layer for multiple model families with AWS-native controls.",
        "source": "https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html",
    },
    {
        "provider": "NVIDIA NIM",
        "family": "Nemotron + partner models",
        "models": ["Nemotron Nano", "Nemotron Mini", "Llama 3.3 Nemotron Super"],
        "notes": "Good fit if you want in-house accelerated inference and safety microservices.",
        "source": "https://docs.nvidia.com/nim/large-language-models/latest/supported-models.html",
    },
    {
        "provider": "Mistral",
        "family": "Mistral",
        "models": ["Mistral Large", "Mistral Small", "Codestral"],
        "notes": "Strong compact model family for coding, tool use, and lower-latency assistants.",
        "source": "https://docs.mistral.ai/getting-started/models/",
    },
    {
        "provider": "Meta Llama",
        "family": "Llama",
        "models": ["Llama 4 Scout", "Llama 4 Maverick", "Llama 3.3"],
        "notes": "Open-weight family often deployed through another provider or your own stack.",
        "source": "https://www.llama.com",
    },
    {
        "provider": "Cohere",
        "family": "Command",
        "models": ["Command", "Command R", "Command R+"],
        "notes": "Good enterprise and retrieval-friendly surface for grounded assistants and structured ops writing.",
        "source": "https://docs.cohere.com/docs/models",
    },
    {
        "provider": "Hugging Face",
        "family": "Inference Providers / model hub",
        "models": ["Provider gateway", "Hosted OSS catalog", "Custom model routing"],
        "notes": "Best as a flexible model catalog and provider broker rather than a single model family.",
        "source": "https://huggingface.co/docs/inference-providers/index",
    },
]
CHANNEL_AUTO_TOKENS = {
    "",
    "auto",
    "auto detect",
    "auto-detect",
    "detect",
    "suggested",
}
BOT_DRAFT_SURFACES = [
    ("announcement", "Announcement"),
    ("broadcast", "Broadcast"),
]
BOT_DRAFT_STATUSES = {
    "draft": "Draft",
    "pending_review": "Pending Review",
    "approved": "Approved",
    "rejected": "Rejected",
    "published": "Published",
}


def _staff_role() -> str:
    if session.get("staff_role"):
        return str(session.get("staff_role") or "")
    if session.get("admin_authed"):
        return "admin"
    return ""


def _staff_name() -> str:
    return (
        session.get("staff_name")
        or session.get("display_name")
        or session.get("staff_username")
        or "Operator"
    )


def _normalize_staff_override_map(value) -> dict:
    if isinstance(value, dict):
        raw = value
    else:
        raw = {}
    return {key: 1 if bool(raw.get(key)) else 0 for key in STAFF_PERMISSION_LABELS if key in raw}


def _staff_permissions(role: str | None = None, overrides: dict | None = None) -> dict:
    role = role or _staff_role()
    if overrides is None:
        overrides = session.get("staff_permission_overrides") or {}
    base = dict(STAFF_ROLE_DEFAULTS.get(role, {}))
    normalized = _normalize_staff_override_map(overrides)
    base.update(normalized)
    return {
        "admin": role == "admin",
        "moderation": bool(base.get("moderation")),
        "channels": bool(base.get("channels")),
        "broadcasts": bool(base.get("broadcasts")),
        "announcements": bool(base.get("announcements")),
        "staff": bool(base.get("staff")),
        "bots": bool(base.get("bots")),
        "system": bool(base.get("system")),
        "members": bool(base.get("members")),
    }


def _staff_authed() -> bool:
    return bool(_staff_role())


def _set_staff_session(account: dict):
    role = str(account.get("role") or "moderator")
    overrides = _normalize_staff_override_map(account.get("permission_overrides"))
    session["admin_authed"] = role == "admin"
    session["staff_role"] = role
    session["staff_name"] = account.get("display_name") or account.get("username") or STAFF_ROLE_LABELS.get(role, "Operator")
    session["staff_username"] = account.get("username") or ""
    session["staff_id"] = int(account.get("id") or 0)
    session["linked_bot_slug"] = account.get("linked_bot_slug") or ""
    session["staff_permission_overrides"] = overrides


def _clear_staff_session():
    for key in ("admin_authed", "staff_role", "staff_name", "staff_username", "staff_id", "linked_bot_slug", "staff_permission_overrides"):
        session.pop(key, None)

ESPORTS_SECTIONS = [
    {
        "slug": "arena",
        "title": "Arena",
        "status": "Active build",
        "copy": "Competitive hub for ranked ladders, customs, scrims, replay review, and watch-party routing.",
        "href": "/arena",
        "cta": "Open arena",
    },
    {
        "slug": "tournaments",
        "title": "Tournaments",
        "status": "Planned ops",
        "copy": "Bracketed events, finals nights, creator cups, rulesets, prize messaging, and admin check-in flow.",
        "href": "#tournaments",
        "cta": "Open lanes",
    },
    {
        "slug": "watch",
        "title": "Watch",
        "status": "Live now",
        "copy": "Pull the existing channels rail, replay feeds, and arena watchlist into one esports surface.",
        "href": "/channels",
        "cta": "Open watch",
    },
    {
        "slug": "leaderboards",
        "title": "Leaderboards",
        "status": "Live now",
        "copy": "Member stats, ranked divisions, and global Fortnite snapshots already exist and should route through esports.",
        "href": "/leaderboard",
        "cta": "Open board",
    },
    {
        "slug": "teams",
        "title": "Teams + Calendar",
        "status": "Next up",
        "copy": "Squad finder, team cards, match calendar, check-in windows, and season schedules.",
        "href": "#ideas",
        "cta": "View ideas",
    },
    {
        "slug": "rewards",
        "title": "Rewards + Replay Lab",
        "status": "Next up",
        "copy": "Prize vault, ticket rewards, VOD study rooms, featured clips, and coaching-style breakdowns.",
        "href": "#roadmap",
        "cta": "View roadmap",
    },
]

TOURNAMENT_LANES = [
    {
        "name": "Night Customs",
        "format": "Open queue",
        "cadence": "Nightly",
        "copy": "Fast queue for customs, scrims, and warmup lobbies with replay capture and mod tools.",
    },
    {
        "name": "Creator Cup",
        "format": "Invite + qualifiers",
        "cadence": "Weekly",
        "copy": "Spotlight creators, UEFN builders, and featured islands with a cleaner broadcast shell.",
    },
    {
        "name": "Forge Finals",
        "format": "Bracket finals",
        "cadence": "Seasonal",
        "copy": "Final-stage event surface for brackets, finals timing, prize messaging, and featured match cards.",
    },
]

ESPORTS_SUBSECTION_IDEAS = [
    "Scrims",
    "Replay Review",
    "Team HQ",
    "Schedule",
    "Creator Cups",
    "Prize Vault",
    "Rules Center",
    "Clips",
    "Stats Lab",
    "Watch Parties",
    "Check-In Desk",
    "Coaching Lab",
]

ESPORTS_ROADMAP = [
    {
        "phase": "Now",
        "status": "Build",
        "copy": "Create the esports hub, route traffic from leaderboard and channels, and define the section architecture.",
    },
    {
        "phase": "Next",
        "status": "Ops",
        "copy": "Add tournament cards, bracket states, team surfaces, schedule rails, and admin-run event tools.",
    },
    {
        "phase": "Later",
        "status": "Depth",
        "copy": "Bring in replay review, coaching overlays, prize flows, squad profiles, and more serious event automation.",
    },
]

ARENA_MODULES = [
    {
        "title": "Arena Floor",
        "status": "Live now",
        "copy": "Roamable spectator room with theater screen, leaderboard wall, concession counter, and quick-focus camera presets.",
    },
    {
        "title": "Tournament Ops",
        "status": "Next",
        "copy": "Check-in desk, lane schedule, bracket state, and admin-driven finals-night messaging.",
    },
    {
        "title": "Replay Lab",
        "status": "Next",
        "copy": "Film room for VOD review, clip callouts, and coaching overlays tied back to feed and channels.",
    },
    {
        "title": "Broadcast Booth",
        "status": "Later",
        "copy": "Caster desk, sponsor loops, match cards, and presentation controls that feel like a premium console deck.",
    },
    {
        "title": "Team Garage",
        "status": "Later",
        "copy": "Roster bays, team identity, squad schedule, and private prep surfaces for customs and cup nights.",
    },
    {
        "title": "Prize Vault",
        "status": "Later",
        "copy": "Reward tracks, ticket sinks, featured drops, and finals-night unlock messaging.",
    },
]

ARENA_ASSET_REFERENCES = [
    {
        "title": "Theater Interior",
        "slot": "Auditorium shell",
        "source": "Fab",
        "url": "https://www.fab.com/listings/72f2981d-e02f-4641-9fb6-5bbb0fb9d5ef",
    },
    {
        "title": "Ultimate Cinema & Movie Theater - Auditorium, Lobby & Snacks",
        "slot": "Full premium theater pass",
        "source": "Fab",
        "url": "https://www.fab.com/listings/7efdc1c8-0d4d-4ff2-bf99-d4a374d018dd",
    },
    {
        "title": "Movie Theater Pack - Realistic Movie Theater Props",
        "slot": "Seats and screen props",
        "source": "Fab",
        "url": "https://www.fab.com/listings/110c753b-78d2-4028-8a4d-3b196bae136c",
    },
    {
        "title": "Stylized Popcorn Machine / Cart - Game Ready",
        "slot": "Concession counter hero prop",
        "source": "Fab",
        "url": "https://www.fab.com/listings/6b850edd-ea1a-4840-915a-027de4aa71fe",
    },
    {
        "title": "Sci-Fi Wall Display Panel - Modular Futuristic Screen",
        "slot": "Leaderboard wall upgrade",
        "source": "Fab",
        "url": "https://www.fab.com/listings/6f9d35eb-0ddd-48d9-96fa-60d8955f5c10",
    },
    {
        "title": "Unfinished Building",
        "slot": "Exterior arena shell",
        "source": "Fab / Quixel Megascans",
        "url": "https://www.fab.com/listings/25f2e7e5-5cca-48a5-99a3-35c38b8240ac",
    },
    {
        "title": "Abandoned Warehouse",
        "slot": "Mechanic pit exterior",
        "source": "Fab",
        "url": "https://www.fab.com/listings/eb6fd9a2-9658-42cb-966c-90e5099b4aa3",
    },
]

def serve_index():
    return send_from_directory(ROOT, "index.html")


def _is_checked(value):
    return str(value).lower() in {"1", "true", "on", "yes"}


def _to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _short_id(value):
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) <= 18:
        return value
    return f"{value[:8]}...{value[-6:]}"


def _normalize_channel_lines(value):
    if isinstance(value, (list, tuple, set)):
        items = [str(item or "").strip() for item in value]
    else:
        items = [line.strip() for line in str(value or "").splitlines()]
    return [item for item in items if item]


def _channel_signal_blob(*parts):
    chunks = []
    for part in parts:
        if isinstance(part, (list, tuple, set)):
            chunks.extend(str(item or "") for item in part)
        else:
            chunks.append(str(part or ""))
    return " ".join(chunks).casefold()


def _score_signal(signal, needles):
    return sum(1 for needle in needles if needle in signal)


def _infer_channel_category(name="", description="", source_urls_text="", search_terms_text="", provider_hint=""):
    signal = _channel_signal_blob(name, description, source_urls_text, search_terms_text, provider_hint)
    if not signal.strip():
        return "Community Picks"

    scores = {
        "Fortnite Competitive": 0,
        "Game Developers": 0,
        "Esports": 0,
        "Creative / UEFN": 0,
        "Gaming News": 0,
        "Community Picks": 0,
        "Chill / Music": 0,
    }

    scores["Fortnite Competitive"] += _score_signal(
        signal,
        [
            "fortnite",
            "fncs",
            "cash cup",
            "battle royale",
            "epic games fortnite",
            "@fn_competitive",
            "ranked",
            "fortnite competitive",
            "fortnite world cup",
        ],
    ) * 2
    scores["Creative / UEFN"] += _score_signal(
        signal,
        [
            "uefn",
            "verse",
            "creative 2.0",
            "creative / uefn",
            "fortnite creative",
            "island builder",
            "build your first island",
            "unreal editor for fortnite",
        ],
    ) * 2
    scores["Game Developers"] += _score_signal(
        signal,
        [
            "unreal engine",
            "unity",
            "gdc",
            "game developers conference",
            "naughty dog",
            "bungie",
            "playstation",
            "xbox",
            "nintendo",
            "developer",
            "devlog",
            "postmortem",
        ],
    ) * 2
    scores["Esports"] += _score_signal(
        signal,
        [
            "esports",
            "valorant",
            "counter-strike",
            "cs2",
            "rocket league",
            "overwatch league",
            "lck",
            "vct",
            "pgl",
            "tournament",
            "scrim",
            "finals",
        ],
    ) * 2
    scores["Gaming News"] += _score_signal(
        signal,
        [
            "news",
            "ign",
            "gamespot",
            "kotaku",
            "digital foundry",
            "pokemon",
            "direct",
            "showcase",
            "state of play",
            "update",
            "headline",
            "signal",
        ],
    ) * 2
    scores["Community Picks"] += _score_signal(
        signal,
        [
            "creator",
            "community",
            "highlights",
            "clips",
            "sypherpk",
            "lachlan",
            "ali-a",
            "mythpat",
            "fan",
            "streamer",
        ],
    ) * 2
    scores["Chill / Music"] += _score_signal(
        signal,
        [
            "music",
            "lofi",
            "ost",
            "soundtrack",
            "square enix",
            "final fantasy",
            "nier",
            "radio",
            "beats",
            "chill",
            "piano",
            "ambient",
        ],
    ) * 2

    if "youtube.com/@" in signal or "twitch.tv/" in signal:
        scores["Community Picks"] += 1
    if "youtube.com/channel/ucmx60hycw1ieiplzzagfqxq" in signal:
        scores["Chill / Music"] += 3
    if "fortnite-api" in signal or "dev.epicgames.com" in signal:
        scores["Game Developers"] += 1
        scores["Fortnite Competitive"] += 1

    best_category = max(scores, key=scores.get)
    return best_category if scores[best_category] > 0 else "Community Picks"


def _infer_channel_provider_hint(source_urls_text=""):
    urls = _normalize_channel_lines(source_urls_text)
    providers = set()
    for url in urls:
        signal = str(url or "").casefold()
        if "youtube.com" in signal or "youtu.be" in signal:
            providers.add("youtube")
        elif "twitch.tv" in signal:
            providers.add("twitch")
        elif "kick.com" in signal:
            providers.add("kick")
        elif "streamable.com" in signal:
            providers.add("streamable")

    if not providers:
        return ""
    if len(providers) == 1:
        return next(iter(providers))
    return "mixed"


def _infer_channel_rotation_mode(source_urls_text="", search_terms_text=""):
    urls = _normalize_channel_lines(source_urls_text)
    search_terms = _normalize_channel_lines(search_terms_text)
    if len(urls) > 1:
        return "random_pool"
    if search_terms:
        return "queue"
    for url in urls:
        signal = str(url or "").casefold()
        if any(marker in signal for marker in ("/videos", "/streams", "/featured", "youtube.com/@", "youtube.com/channel/")):
            return "queue"
    return "single"


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _top_member_rows(members=None, limit=8):
    rows = []
    pool = members if members is not None else (get_all_members() or [])
    ranked = sorted(
        pool,
        key=lambda member: (
            _to_int(member.get("wins"), 0),
            _safe_float(member.get("kd"), 0.0),
            _to_int(member.get("tickets"), 0),
        ),
        reverse=True,
    )[:limit]
    for index, member in enumerate(ranked, start=1):
        rows.append(
            {
                "rank": index,
                "display_name": (member.get("display_name") or "Unknown")[:24],
                "wins": _to_int(member.get("wins"), 0),
                "kd": round(_safe_float(member.get("kd"), 0.0), 2),
                "tickets": _to_int(member.get("tickets"), 0),
                "ranked_division": (member.get("ranked_division") or "Forge Open")[:28],
            }
        )
    return rows


def _channel_payload(form):
    source_urls_text = (form.get("source_urls_text") or form.get("embed_url") or "").strip()[:4000]
    source_urls = [line.strip() for line in source_urls_text.splitlines() if line.strip()]
    primary_url = source_urls[0] if source_urls else ""
    search_terms_text = (form.get("search_terms_text") or "").strip()[:2000]
    category_value = (form.get("category") or "").strip()[:64]
    provider_hint = (form.get("provider_hint") or "").strip()[:32]
    rotation_mode = (form.get("rotation_mode") or "").strip()[:32]
    detected_category = _infer_channel_category(
        name=form.get("name"),
        description=form.get("description"),
        source_urls_text=source_urls_text,
        search_terms_text=search_terms_text,
        provider_hint=provider_hint,
    )
    detected_provider_hint = _infer_channel_provider_hint(source_urls_text)
    detected_rotation_mode = _infer_channel_rotation_mode(source_urls_text, search_terms_text)
    return {
        "channel_id": _to_int(form.get("channel_id")),
        "name": (form.get("name") or "").strip()[:128],
        "category": detected_category if category_value.casefold() in CHANNEL_AUTO_TOKENS else (category_value or detected_category),
        "embed_url": primary_url[:1024],
        "source_urls_text": source_urls_text,
        "search_terms_text": search_terms_text,
        "description": (form.get("description") or "").strip()[:512],
        "provider_hint": detected_provider_hint if provider_hint.casefold() in CHANNEL_AUTO_TOKENS else (provider_hint or detected_provider_hint),
        "rotation_mode": detected_rotation_mode if rotation_mode.casefold() in CHANNEL_AUTO_TOKENS else (rotation_mode or detected_rotation_mode),
        "autoplay": 1 if _is_checked(form.get("autoplay")) else 0,
        "transition_title": (form.get("transition_title") or "").strip()[:128],
        "transition_copy": (form.get("transition_copy") or "").strip()[:512],
        "transition_seconds": _to_float((form.get("transition_seconds") or "").strip(), 0.9),
        "sort_order": _to_int((form.get("sort_order") or "").strip(), None),
        "approved": 1 if _is_checked(form.get("approved")) else 0,
        "detected_category": detected_category,
        "detected_provider_hint": detected_provider_hint,
        "detected_rotation_mode": detected_rotation_mode,
    }


def _broadcast_payload(form):
    variant = ((form.get("variant") or "").strip()[:24] or "info").lower()
    display_mode = ((form.get("display_mode") or "").strip()[:24] or "banner").lower()
    dismiss_mode = ((form.get("dismiss_mode") or "").strip()[:24] or "manual").lower()
    return {
        "broadcast_id": _to_int(form.get("broadcast_id")),
        "title": (form.get("title") or "").strip()[:128],
        "body": (form.get("body") or "").strip()[:1024],
        "variant": variant if variant in BROADCAST_VARIANTS else "info",
        "display_mode": display_mode if display_mode in BROADCAST_DISPLAY_MODES else "banner",
        "dismiss_mode": dismiss_mode if dismiss_mode in BROADCAST_DISMISS_MODES else "manual",
        "duration_seconds": _to_float((form.get("duration_seconds") or "").strip(), 8.0),
        "cta_label": (form.get("cta_label") or "").strip()[:64],
        "cta_href": (form.get("cta_href") or "").strip()[:512],
        "closable": 1 if _is_checked(form.get("closable")) else 0,
        "active": 1 if _is_checked(form.get("active")) else 0,
        "priority": _to_int((form.get("priority") or "").strip(), 0) or 0,
    }


def _normalize_bot_draft_payload(form, target_surface: str):
    target_surface = (target_surface or "announcement").strip().lower()
    payload = {
        "pinned": 1 if _is_checked(form.get("pinned")) else 0,
        "variant": ((form.get("variant") or "").strip()[:24] or "info").lower(),
        "display_mode": ((form.get("display_mode") or "").strip()[:24] or "banner").lower(),
        "dismiss_mode": ((form.get("dismiss_mode") or "").strip()[:24] or "manual").lower(),
        "duration_seconds": _to_float((form.get("duration_seconds") or "").strip(), 8.0),
        "cta_label": (form.get("cta_label") or "").strip()[:64],
        "cta_href": (form.get("cta_href") or "").strip()[:512],
        "closable": 1 if _is_checked(form.get("closable")) else 0,
        "active": 1 if _is_checked(form.get("active")) else 0,
        "priority": _to_int((form.get("priority") or "").strip(), 0) or 0,
    }
    if target_surface == "announcement":
        payload.update(
            {
                "variant": "info",
                "display_mode": "banner",
                "dismiss_mode": "manual",
                "duration_seconds": 8.0,
                "cta_label": "",
                "cta_href": "",
                "closable": 1,
                "active": 1,
                "priority": 0,
            }
        )
    return payload


def _bot_draft_payload(form):
    target_surface = ((form.get("target_surface") or "announcement").strip()[:32] or "announcement").lower()
    target_surface = target_surface if target_surface in {item[0] for item in BOT_DRAFT_SURFACES} else "announcement"
    return {
        "draft_id": _to_int(form.get("draft_id")),
        "bot_slug": (form.get("bot_slug") or "").strip().lower()[:64],
        "title": (form.get("title") or "").strip()[:256],
        "body": (form.get("body") or "").strip(),
        "target_surface": target_surface,
        "review_note": (form.get("review_note") or "").strip()[:1024],
        "payload_json": _normalize_bot_draft_payload(form, target_surface),
    }


def _admin_redirect(anchor="overview", edit_channel=None, edit_broadcast=None):
    params = {}
    if edit_channel is not None:
        params["edit_channel"] = edit_channel
    if edit_broadcast is not None:
        params["edit_broadcast"] = edit_broadcast
    target = url_for("platform.admin", **params) if params else url_for("platform.admin")
    return redirect(f"{target}#{anchor}")


def _ops_redirect(anchor="overview", edit_staff=None, edit_bot=None, edit_draft=None):
    params = {}
    if edit_staff is not None:
        params["edit_staff"] = edit_staff
    if edit_bot is not None:
        params["edit_bot"] = edit_bot
    if edit_draft is not None:
        params["edit_draft"] = edit_draft
    target = url_for("platform.ops", **params) if params else url_for("platform.ops")
    return redirect(f"{target}#{anchor}" if anchor else target)


def _operator_username() -> str:
    return (
        session.get("staff_username")
        or session.get("display_name")
        or session.get("epic_id")
        or "root-admin"
    )


def _root_admin_alias(username: str) -> bool:
    normalized = str(username or "").strip().lower()
    return normalized in {"", "admin", "root", "root-admin", "rootadmin"}


def _log_auth_attempt(surface: str, username: str, success: bool, note: str = "") -> None:
    safe_username = str(username or "root-admin").strip() or "root-admin"
    remote_addr = request.headers.get("X-Forwarded-For") or request.remote_addr or "-"
    outcome = "success" if success else "failure"
    message = f"[auth] surface={surface} username={safe_username} outcome={outcome} remote={remote_addr}"
    if note:
        message += f" note={note}"
    logger = getattr(current_app, "logger", None)
    if logger is not None:
        if success:
            logger.info(message)
        else:
            logger.warning(message)


def _permission_overrides_from_form(form) -> dict:
    rows = {}
    for key in STAFF_PERMISSION_LABELS:
        rows[key] = 1 if _is_checked(form.get(f"perm_{key}")) else 0
    return rows


def _can_manage_bot_profile(role: str, linked_bot_slug: str, bot_profile: dict | None) -> bool:
    if not bot_profile:
        return False
    if role == "admin":
        return True
    if role == "bot_operator":
        return bool(linked_bot_slug and linked_bot_slug == (bot_profile.get("slug") or ""))
    return False


def _can_manage_bot_draft(role: str, linked_bot_slug: str, draft: dict | None) -> bool:
    if not draft:
        return False
    if role == "admin":
        return True
    if role == "bot_operator":
        return bool(linked_bot_slug and linked_bot_slug == (draft.get("bot_slug") or ""))
    return False

@platform_bp.route("/")
@platform_bp.route("/home")
def home():
    user = session.get("user")
    members = get_all_members() or []
    islands = get_recent_islands(limit=999) or []
    return render_template("home.html",
        user=user,
        n_members=len(members),
        n_islands=len(islands))

@platform_bp.route("/gallery")
def gallery():
    return serve_index()

@platform_bp.route("/feed")
def feed():
    posts = get_posts(limit=50)
    from flask import current_app
    t = os.path.join(ROOT, "templates", "feed.html")
    if os.path.exists(t):
        return render_template("feed.html", posts=posts)
    return serve_index()

@platform_bp.route("/community")
def community():
    t = os.path.join(ROOT, "templates", "community.html")
    if os.path.exists(t):
        return render_template("community.html", members=get_all_members(), announcements=get_announcements())
    return serve_index()

@platform_bp.route("/esports")
def esports():
    channels = get_channels() or []
    posts = get_posts(limit=6) or []
    announcements = get_announcements() or []
    members = get_all_members() or []
    arena_channels = [
        channel for channel in channels
        if (channel.get("category") or "") in {"Esports", "Fortnite Competitive"}
    ][:6]
    highlighted_posts = [post for post in posts if post.get("embed_url") or post.get("caption")][:4]
    return render_template(
        "esports.html",
        members_total=len(members),
        announcements_total=len(announcements),
        arena_channel_total=len(arena_channels),
        post_total=len(posts),
        arena_channels=arena_channels,
        highlighted_posts=highlighted_posts,
        announcements=announcements[:4],
        esports_sections=ESPORTS_SECTIONS,
        tournament_lanes=TOURNAMENT_LANES,
        subsection_ideas=ESPORTS_SUBSECTION_IDEAS,
        esports_roadmap=ESPORTS_ROADMAP,
    )


@platform_bp.route("/arena")
def arena():
    members = get_all_members() or []
    announcements = get_announcements() or []
    channels = get_channels() or []
    posts = get_posts(limit=10) or []
    arena_channels = [
        channel for channel in channels
        if (channel.get("category") or "") in {"Esports", "Fortnite Competitive", "Creative / UEFN"}
    ][:6]
    featured_channel = arena_channels[0] if arena_channels else {}
    leaderboard_rows = _top_member_rows(members, limit=8)
    ticker_lines = [item.get("title") for item in announcements[:4] if item.get("title")]
    if not ticker_lines:
        ticker_lines = [
            "Arena deck live",
            "Tournament lanes staged",
            "Leaderboard wall synced",
            "Replay lab planned",
        ]
    featured_posts = [
        {
            "caption": (post.get("caption") or "Arena update")[:72],
            "platform": (post.get("platform") or "Feed")[:24],
            "embed_url": post.get("embed_url") or "",
        }
        for post in posts
        if post.get("caption") or post.get("embed_url")
    ][:4]
    scene_payload = {
        "leaderboard": leaderboard_rows[:5],
        "ticker": ticker_lines,
        "feature_title": featured_channel.get("name") or "Forge Finals Theater",
        "feature_copy": (
            featured_channel.get("description")
            or "Live match review, watch-party routing, and event night replays sit on the main screen."
        ),
        "announcement_lines": ticker_lines[:3],
    }
    return render_template(
        "arena.html",
        leaderboard_rows=leaderboard_rows,
        announcements=announcements[:5],
        arena_channels=arena_channels,
        featured_channel=featured_channel,
        featured_posts=featured_posts,
        tournament_lanes=TOURNAMENT_LANES,
        arena_modules=ARENA_MODULES,
        asset_refs=ARENA_ASSET_REFERENCES,
        scene_payload=scene_payload,
        members_total=len(members),
        announcement_total=len(announcements),
        arena_channel_total=len(arena_channels),
    )

@platform_bp.route("/dashboard")
def dashboard():
    user = session.get("user")
    staff_role = _staff_role()
    staff_authed = _staff_authed()
    if not user:
        epic_id = session.get("epic_id")
        if epic_id:
            user = {
                "display_name": session.get("display_name", epic_id),
                "account_id": session.get("epic_account_id", epic_id),
                "skin_img": session.get("skin_img", ""),
                "skin_name": session.get("skin_name", "Default"),
            }
        elif staff_authed:
            user = {
                "display_name": _staff_name(),
                "account_id": f"staff:{session.get('staff_username') or staff_role or 'ops'}",
                "skin_img": "",
                "skin_name": STAFF_ROLE_LABELS.get(staff_role, "Operator"),
            }
        else:
            return redirect("/home")
    account_id = (
        user.get("account_id")
        or session.get("epic_account_id")
        or session.get("epic_id")
        or ""
    )
    account_is_staff = str(account_id).startswith("staff:")
    room_data = get_member_room(account_id) if account_id and not account_is_staff else {"theme": "ops", "tickets": 0}
    tickets = get_member_tickets(account_id) if account_id and not account_is_staff else int(room_data.get("tickets") or 0)
    islands = get_member_islands(account_id, limit=6) if account_id and not account_is_staff else []
    uploads = (get_audio_tracks(account_id) or [])[:6] if account_id and not account_is_staff else []
    announcements = (get_announcements() or [])[:4]
    return render_template("dashboard.html",
        name=user.get("display_name", "Player"),
        account_id=account_id,
        account_id_short=_short_id(account_id),
        skin_img=user.get("skin_img", "") or session.get("skin_img", ""),
        skin_name=user.get("skin_name", "Default") or session.get("skin_name", "Default"),
        room_theme=room_data.get("theme", "") or "stock",
        tickets=tickets,
        islands=islands,
        island_count=len(islands),
        uploads=uploads,
        upload_count=len(uploads),
        announcements=announcements,
        announcement_count=len(announcements),
        epic_connected=bool(session.get("epic_access_token") or session.get("access_token") or (account_id and not account_is_staff)),
        admin_authed=staff_role == "admin")

@platform_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@platform_bp.route("/ops", methods=["GET", "POST"])
def ops():
    authed = _staff_authed()
    role = _staff_role()
    linked_bot_slug = str(session.get("linked_bot_slug") or "")
    permissions = _staff_permissions(role)

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()

        if action == "login":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            account = None
            if _root_admin_alias(username) and password == ADMIN_PASSWORD:
                account = {
                    "id": 0,
                    "username": "root-admin",
                    "display_name": "Root Admin",
                    "role": "admin",
                    "linked_bot_slug": "",
                    "active": 1,
                }
            elif username:
                account = authenticate_staff_account(username, password)
            if not account:
                _log_auth_attempt("ops", username or "root-admin", False, "credentials rejected")
                flash("Wrong username or password.", "error")
                return _ops_redirect("login")
            _set_staff_session(account)
            _log_auth_attempt("ops", account.get("username") or "root-admin", True, account.get("role") or "admin")
            log_operator_event(
                _operator_username(),
                _staff_role(),
                "ops_login",
                "session",
                account.get("username") or "root-admin",
                "Ops console login",
            )
            flash(f"{STAFF_ROLE_LABELS.get(_staff_role(), 'Operator')} session opened.", "success")
            return _ops_redirect("overview")

        if action == "logout":
            if authed:
                log_operator_event(
                    _operator_username(),
                    role or "admin",
                    "ops_logout",
                    "session",
                    session.get("staff_username") or "root-admin",
                    "Ops console logout",
                )
            _clear_staff_session()
            flash("Ops session closed.", "success")
            return _ops_redirect("login")

        if not authed:
            return Response("Unauthorized", 403)

        role = _staff_role()
        linked_bot_slug = str(session.get("linked_bot_slug") or "")
        permissions = _staff_permissions(role)
        actor_username = _operator_username()
        actor_role = role or "admin"

        if action == "post_update":
            if not permissions["moderation"]:
                flash("Moderation access required.", "error")
                return _ops_redirect("moderation")
            post_id = _to_int(request.form.get("post_id"))
            caption = (request.form.get("caption") or "").strip()
            embed_url = (request.form.get("embed_url") or "").strip()
            if not post_id or not caption and not embed_url:
                flash("Post update requires a post and at least one field.", "error")
                return _ops_redirect("moderation")
            if update_post(post_id, caption, embed_url):
                log_operator_event(actor_username, actor_role, "post_update", "post", str(post_id), "Edited post content")
                flash("Post updated.", "success")
            else:
                flash("Post update failed.", "error")
            return _ops_redirect("moderation")

        if action == "post_delete":
            if not permissions["moderation"]:
                flash("Moderation access required.", "error")
                return _ops_redirect("moderation")
            post_id = _to_int(request.form.get("post_id"))
            if post_id and delete_post(post_id):
                log_operator_event(actor_username, actor_role, "post_delete", "post", str(post_id), "Removed community post")
                flash("Post removed.", "success")
            else:
                flash("Post removal failed.", "error")
            return _ops_redirect("moderation")

        if action == "staff_create":
            if not permissions["staff"]:
                flash("Admin staff controls required.", "error")
                return _ops_redirect("staff")
            username = (request.form.get("username") or "").strip().lower()
            display_name = (request.form.get("display_name") or "").strip()
            new_role = (request.form.get("role") or "moderator").strip().lower()
            password = request.form.get("password") or ""
            linked_slug = (request.form.get("linked_bot_slug") or "").strip().lower()
            permission_overrides = _permission_overrides_from_form(request.form)
            if create_staff_account(
                username,
                display_name,
                new_role,
                password,
                linked_bot_slug=linked_slug,
                active=_is_checked(request.form.get("active")),
                permission_overrides=permission_overrides,
            ):
                log_operator_event(actor_username, actor_role, "staff_create", "staff", username, f"role={new_role}")
                flash("Staff account created.", "success")
            else:
                flash("Staff account creation failed. Check username/password.", "error")
            return _ops_redirect("staff")

        if action == "staff_update":
            if not permissions["staff"]:
                flash("Admin staff controls required.", "error")
                return _ops_redirect("staff")
            staff_id = _to_int(request.form.get("staff_id"))
            username = (request.form.get("username") or "").strip().lower()
            display_name = (request.form.get("display_name") or "").strip()
            new_role = (request.form.get("role") or "moderator").strip().lower()
            password = request.form.get("password") or ""
            linked_slug = (request.form.get("linked_bot_slug") or "").strip().lower()
            permission_overrides = _permission_overrides_from_form(request.form)
            if update_staff_account(
                staff_id,
                username,
                display_name,
                new_role,
                password=password,
                linked_bot_slug=linked_slug,
                active=_is_checked(request.form.get("active")),
                permission_overrides=permission_overrides,
            ):
                log_operator_event(actor_username, actor_role, "staff_update", "staff", username or str(staff_id), f"role={new_role}")
                flash("Staff account updated.", "success")
            else:
                flash("Staff account update failed.", "error")
            return _ops_redirect("staff", edit_staff=staff_id)

        if action == "staff_delete":
            if not permissions["staff"]:
                flash("Admin staff controls required.", "error")
                return _ops_redirect("staff")
            staff_id = _to_int(request.form.get("staff_id"))
            if staff_id and staff_id == _to_int(session.get("staff_id")):
                flash("Use logout instead of deleting the account in your current session.", "error")
                return _ops_redirect("staff")
            target = get_staff_account(staff_id) if staff_id else None
            if staff_id and delete_staff_account(staff_id):
                log_operator_event(actor_username, actor_role, "staff_delete", "staff", (target or {}).get("username") or str(staff_id), "Removed staff account")
                flash("Staff account removed.", "success")
            else:
                flash("Staff account removal failed.", "error")
            return _ops_redirect("staff")

        if action == "bot_profile_create":
            if role != "admin":
                flash("Admin bot controls required.", "error")
                return _ops_redirect("bots")
            provider = (request.form.get("llm_provider") or "").strip()
            catalog_row = next((item for item in BOT_PROVIDER_CATALOG if item["provider"] == provider), None)
            llm_family = (request.form.get("llm_family") or (catalog_row or {}).get("family") or "").strip()
            slug = (request.form.get("slug") or "").strip().lower()
            display_name = (request.form.get("display_name") or "").strip()
            if create_bot_profile(
                slug=slug,
                display_name=display_name,
                badge_label=(request.form.get("badge_label") or "").strip() or "AI Operator",
                role_label=(request.form.get("role_label") or "").strip() or "Operator",
                bio=(request.form.get("bio") or "").strip(),
                tone=(request.form.get("tone") or "").strip(),
                language_profile=(request.form.get("language_profile") or "").strip() or "American English",
                llm_provider=provider,
                llm_model=(request.form.get("llm_model") or "").strip(),
                llm_family=llm_family,
                scope_text=(request.form.get("scope_text") or "").strip(),
                surfaces_text=(request.form.get("surfaces_text") or "").strip(),
                system_prompt=(request.form.get("system_prompt") or "").strip(),
                active=_is_checked(request.form.get("active")),
            ):
                log_operator_event(actor_username, actor_role, "bot_create", "bot", slug, provider or "unassigned")
                flash("Bot profile created.", "success")
            else:
                flash("Bot profile creation failed.", "error")
            return _ops_redirect("bots")

        if action == "bot_profile_update":
            bot_id = _to_int(request.form.get("bot_id"))
            target_bot = get_bot_profile(bot_id) if bot_id else None
            if not _can_manage_bot_profile(role, linked_bot_slug, target_bot):
                flash("You do not have access to that bot profile.", "error")
                return _ops_redirect("bots")
            provider = (request.form.get("llm_provider") or "").strip()
            catalog_row = next((item for item in BOT_PROVIDER_CATALOG if item["provider"] == provider), None)
            llm_family = (request.form.get("llm_family") or (catalog_row or {}).get("family") or "").strip()
            submitted_slug = (request.form.get("slug") or "").strip().lower()
            safe_slug = target_bot.get("slug") if role == "bot_operator" else submitted_slug
            if update_bot_profile(
                bot_id=bot_id,
                slug=safe_slug,
                display_name=(request.form.get("display_name") or "").strip(),
                badge_label=(request.form.get("badge_label") or "").strip() or "AI Operator",
                role_label=(request.form.get("role_label") or "").strip() or "Operator",
                bio=(request.form.get("bio") or "").strip(),
                tone=(request.form.get("tone") or "").strip(),
                language_profile=(request.form.get("language_profile") or "").strip() or "American English",
                llm_provider=provider,
                llm_model=(request.form.get("llm_model") or "").strip(),
                llm_family=llm_family,
                scope_text=(request.form.get("scope_text") or "").strip(),
                surfaces_text=(request.form.get("surfaces_text") or "").strip(),
                system_prompt=(request.form.get("system_prompt") or "").strip(),
                active=_is_checked(request.form.get("active")),
            ):
                log_operator_event(actor_username, actor_role, "bot_update", "bot", safe_slug or str(bot_id), provider or "unassigned")
                flash("Bot profile updated.", "success")
            else:
                flash("Bot profile update failed.", "error")
            return _ops_redirect("bots", edit_bot=bot_id)

        if action == "bot_profile_delete":
            if role != "admin":
                flash("Admin bot controls required.", "error")
                return _ops_redirect("bots")
            bot_id = _to_int(request.form.get("bot_id"))
            target_bot = get_bot_profile(bot_id) if bot_id else None
            if bot_id and delete_bot_profile(bot_id):
                log_operator_event(actor_username, actor_role, "bot_delete", "bot", (target_bot or {}).get("slug") or str(bot_id), "Removed bot profile")
                flash("Bot profile removed.", "success")
            else:
                flash("Bot profile removal failed.", "error")
            return _ops_redirect("bots")

        if action == "bot_draft_create":
            if not permissions["bots"]:
                flash("Bot controls required.", "error")
                return _ops_redirect("drafts")
            payload = _bot_draft_payload(request.form)
            target_bot = get_bot_profile_by_slug(payload["bot_slug"])
            if not _can_manage_bot_profile(role, linked_bot_slug, target_bot):
                flash("You do not have access to create a draft for that bot.", "error")
                return _ops_redirect("drafts")
            if not payload["title"]:
                flash("Draft title is required.", "error")
                return _ops_redirect("drafts")
            if create_bot_draft(
                bot_slug=payload["bot_slug"],
                title=payload["title"],
                body=payload["body"],
                target_surface=payload["target_surface"],
                payload_json=payload["payload_json"],
                created_by=actor_username,
                status="draft",
            ):
                log_operator_event(actor_username, actor_role, "bot_draft_create", "bot_draft", payload["bot_slug"], payload["target_surface"])
                flash("Bot draft created.", "success")
            else:
                flash("Bot draft creation failed.", "error")
            return _ops_redirect("drafts")

        if action == "bot_draft_update":
            if not permissions["bots"]:
                flash("Bot controls required.", "error")
                return _ops_redirect("drafts")
            payload = _bot_draft_payload(request.form)
            draft = get_bot_draft(payload["draft_id"]) if payload["draft_id"] else None
            if not _can_manage_bot_draft(role, linked_bot_slug, draft):
                flash("You do not have access to that draft.", "error")
                return _ops_redirect("drafts")
            if draft and draft.get("status") == "published":
                flash("Published drafts cannot be edited here.", "error")
                return _ops_redirect("drafts", edit_draft=payload["draft_id"])
            if not payload["title"]:
                flash("Draft title is required.", "error")
                return _ops_redirect("drafts", edit_draft=payload["draft_id"])
            if update_bot_draft(
                draft_id=payload["draft_id"],
                bot_slug=payload["bot_slug"],
                title=payload["title"],
                body=payload["body"],
                target_surface=payload["target_surface"],
                payload_json=payload["payload_json"],
                review_note=payload["review_note"],
            ):
                log_operator_event(actor_username, actor_role, "bot_draft_update", "bot_draft", str(payload["draft_id"]), payload["target_surface"])
                flash("Bot draft updated.", "success")
            else:
                flash("Bot draft update failed.", "error")
            return _ops_redirect("drafts", edit_draft=payload["draft_id"])

        if action == "bot_draft_delete":
            if not permissions["bots"]:
                flash("Bot controls required.", "error")
                return _ops_redirect("drafts")
            draft_id = _to_int(request.form.get("draft_id"))
            draft = get_bot_draft(draft_id) if draft_id else None
            if not _can_manage_bot_draft(role, linked_bot_slug, draft):
                flash("You do not have access to that draft.", "error")
                return _ops_redirect("drafts")
            if draft and draft.get("status") == "published":
                flash("Published drafts should be managed from the live surface instead of deleted.", "error")
                return _ops_redirect("drafts", edit_draft=draft_id)
            if draft_id and delete_bot_draft(draft_id):
                log_operator_event(actor_username, actor_role, "bot_draft_delete", "bot_draft", str(draft_id), draft.get("bot_slug") if draft else "")
                flash("Bot draft removed.", "success")
            else:
                flash("Bot draft removal failed.", "error")
            return _ops_redirect("drafts")

        if action == "bot_draft_submit":
            if not permissions["bots"]:
                flash("Bot controls required.", "error")
                return _ops_redirect("drafts")
            draft_id = _to_int(request.form.get("draft_id"))
            review_note = (request.form.get("review_note") or "").strip()[:1024] or None
            draft = get_bot_draft(draft_id) if draft_id else None
            if not _can_manage_bot_draft(role, linked_bot_slug, draft):
                flash("You do not have access to that draft.", "error")
                return _ops_redirect("drafts")
            if draft and draft.get("status") == "published":
                flash("Published drafts cannot be resubmitted.", "error")
                return _ops_redirect("drafts", edit_draft=draft_id)
            if draft_id and transition_bot_draft(draft_id, "pending_review", actor=actor_username, review_note=review_note):
                log_operator_event(actor_username, actor_role, "bot_draft_submit", "bot_draft", str(draft_id), draft.get("bot_slug") if draft else "")
                flash("Draft submitted for admin review.", "success")
            else:
                flash("Draft submission failed.", "error")
            return _ops_redirect("drafts", edit_draft=draft_id)

        if action == "bot_draft_approve":
            if role != "admin":
                flash("Admin approval required.", "error")
                return _ops_redirect("drafts")
            draft_id = _to_int(request.form.get("draft_id"))
            review_note = (request.form.get("review_note") or "").strip()[:1024] or None
            draft = get_bot_draft(draft_id) if draft_id else None
            if not draft:
                flash("Draft not found.", "error")
                return _ops_redirect("drafts")
            if transition_bot_draft(draft_id, "approved", actor=actor_username, review_note=review_note):
                log_operator_event(actor_username, actor_role, "bot_draft_approve", "bot_draft", str(draft_id), draft.get("bot_slug") or "")
                flash("Draft approved.", "success")
            else:
                flash("Draft approval failed.", "error")
            return _ops_redirect("drafts", edit_draft=draft_id)

        if action == "bot_draft_reject":
            if role != "admin":
                flash("Admin approval required.", "error")
                return _ops_redirect("drafts")
            draft_id = _to_int(request.form.get("draft_id"))
            review_note = (request.form.get("review_note") or "").strip()[:1024] or None
            draft = get_bot_draft(draft_id) if draft_id else None
            if not draft:
                flash("Draft not found.", "error")
                return _ops_redirect("drafts")
            if transition_bot_draft(draft_id, "rejected", actor=actor_username, review_note=review_note):
                log_operator_event(actor_username, actor_role, "bot_draft_reject", "bot_draft", str(draft_id), draft.get("bot_slug") or "")
                flash("Draft rejected.", "success")
            else:
                flash("Draft rejection failed.", "error")
            return _ops_redirect("drafts", edit_draft=draft_id)

        if action == "bot_draft_publish":
            if role != "admin":
                flash("Admin publish controls required.", "error")
                return _ops_redirect("drafts")
            draft_id = _to_int(request.form.get("draft_id"))
            draft = get_bot_draft(draft_id) if draft_id else None
            if not draft:
                flash("Draft not found.", "error")
                return _ops_redirect("drafts")
            if publish_bot_draft(draft_id, published_by=actor_username):
                log_operator_event(actor_username, actor_role, "bot_draft_publish", "bot_draft", str(draft_id), draft.get("target_surface") or "")
                flash("Draft published to the live site surface.", "success")
            else:
                flash("Draft publish failed. Approve it first and verify the payload.", "error")
            return _ops_redirect("drafts", edit_draft=draft_id)

        flash("Unknown ops action.", "error")
        return _ops_redirect("overview")

    posts = []
    staff_accounts = []
    bot_profiles = []
    bot_drafts = []
    audit_rows = []
    if authed and permissions["moderation"]:
        posts = get_posts(limit=60, approved_only=False) or []
    if authed and permissions["staff"]:
        staff_accounts = get_staff_accounts() or []
    if authed and permissions["bots"]:
        bot_profiles = get_bot_profiles() or []
    elif authed and role == "bot_operator":
        bot_profiles = get_bot_profiles() or []
    if authed and permissions["bots"]:
        bot_drafts = get_bot_drafts(limit=120) or []
    elif authed and role == "bot_operator":
        bot_drafts = get_bot_drafts(limit=120) or []

    if authed:
        audit_rows = get_operator_audit_log(limit=40) or []

    if role == "bot_operator" and linked_bot_slug:
        bot_profiles = [item for item in bot_profiles if (item.get("slug") or "") == linked_bot_slug]
        bot_drafts = [item for item in bot_drafts if (item.get("bot_slug") or "") == linked_bot_slug]

    edit_staff_id = _to_int(request.args.get("edit_staff"))
    edit_staff = get_staff_account(edit_staff_id) if authed and permissions["staff"] and edit_staff_id else None

    edit_bot_id = _to_int(request.args.get("edit_bot"))
    edit_bot = get_bot_profile(edit_bot_id) if authed and edit_bot_id else None
    if edit_bot and not _can_manage_bot_profile(role, linked_bot_slug, edit_bot):
        edit_bot = None
    if authed and role == "bot_operator" and not edit_bot and bot_profiles:
        edit_bot = bot_profiles[0]

    edit_draft_id = _to_int(request.args.get("edit_draft"))
    edit_draft = get_bot_draft(edit_draft_id) if authed and edit_draft_id else None
    if edit_draft and not _can_manage_bot_draft(role, linked_bot_slug, edit_draft):
        edit_draft = None
    if authed and role == "bot_operator" and not edit_draft and bot_drafts:
        draft_order = {
            "pending_review": 0,
            "rejected": 1,
            "draft": 2,
            "approved": 3,
            "published": 4,
        }
        edit_draft = sorted(bot_drafts, key=lambda item: draft_order.get(item.get("status") or "", 99))[0]

    bot_choices = [{"slug": item.get("slug") or "", "display_name": item.get("display_name") or item.get("slug") or "Bot"} for item in (get_bot_profiles() or [])]
    draft_bot_choices = [{"slug": item.get("slug") or "", "display_name": item.get("display_name") or item.get("slug") or "Bot"} for item in bot_profiles]
    draft_counts = {key: 0 for key in BOT_DRAFT_STATUSES}
    for draft in bot_drafts:
        key = draft.get("status") or "draft"
        if key in draft_counts:
            draft_counts[key] += 1
    ops_metrics = {
        "posts": len(posts),
        "staff": len(staff_accounts),
        "bots": len(bot_profiles),
        "drafts": len(bot_drafts),
        "pending_drafts": draft_counts.get("pending_review", 0),
        "audit": len(audit_rows),
    }
    legacy_admin_links = [
        {"label": "Channel Editor", "href": "/admin#channel-editor"},
        {"label": "Broadcasts", "href": "/admin#broadcasts"},
        {"label": "Announcements", "href": "/admin#announcements"},
        {"label": "Catalog", "href": "/admin#catalog"},
    ]

    return render_template(
        "ops.html",
        authed=authed,
        current_role=role,
        current_role_label=STAFF_ROLE_LABELS.get(role, "Admin" if authed else "Guest"),
        current_staff_name=_staff_name() if authed else "",
        current_staff_username=session.get("staff_username") or "",
        linked_bot_slug=linked_bot_slug,
        staff_permissions=permissions,
        moderation_posts=posts,
        staff_accounts=staff_accounts,
        bot_profiles=bot_profiles,
        bot_drafts=bot_drafts,
        edit_staff=edit_staff,
        edit_bot=edit_bot,
        edit_draft=edit_draft,
        bot_choices=bot_choices,
        draft_bot_choices=draft_bot_choices,
        draft_counts=draft_counts,
        audit_rows=audit_rows,
        ops_metrics=ops_metrics,
        llm_provider_catalog=BOT_PROVIDER_CATALOG,
        role_choices=STAFF_ROLE_OPTIONS,
        role_labels=STAFF_ROLE_LABELS,
        permission_labels=STAFF_PERMISSION_LABELS,
        role_default_permissions=STAFF_ROLE_DEFAULTS,
        bot_draft_surfaces=BOT_DRAFT_SURFACES,
        bot_draft_statuses=BOT_DRAFT_STATUSES,
        legacy_admin_links=legacy_admin_links,
    )

@platform_bp.route("/admin", methods=["GET","POST"])
def admin():
    authed = bool(session.get("admin_authed"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "login":
            if request.form.get("password") == ADMIN_PASSWORD:
                _set_staff_session(
                    {
                        "id": 0,
                        "username": "root-admin",
                        "display_name": "Root Admin",
                        "role": "admin",
                        "linked_bot_slug": "",
                        "active": 1,
                    }
                )
                _log_auth_attempt("admin", "root-admin", True, "legacy admin login")
                flash("Admin session opened.", "success")
                return _admin_redirect("overview")
            else:
                _log_auth_attempt("admin", "root-admin", False, "legacy admin password rejected")
                flash("Wrong admin password.", "error")
                return _admin_redirect("login")
        if action == "logout":
            _clear_staff_session()
            flash("Admin session closed.", "success")
            return _admin_redirect("login")
        if not authed:
            return Response("Unauthorized", 403)

        if action == "announce":
            title = (request.form.get("title") or "").strip()
            body = (request.form.get("body") or "").strip()
            if not title:
                flash("Announcement title is required.", "error")
            else:
                post_announcement(title=title, body=body, pinned=bool(request.form.get("pinned")))
                flash("Announcement posted.", "success")
            return _admin_redirect("announcements")

        if action == "broadcast_create":
            payload = _broadcast_payload(request.form)
            if not payload["title"]:
                flash("Broadcast title is required.", "error")
                return _admin_redirect("broadcasts")
            created = create_site_broadcast(
                title=payload["title"],
                body=payload["body"],
                variant=payload["variant"],
                display_mode=payload["display_mode"],
                dismiss_mode=payload["dismiss_mode"],
                duration_seconds=payload["duration_seconds"],
                cta_label=payload["cta_label"],
                cta_href=payload["cta_href"],
                closable=payload["closable"],
                active=payload["active"],
                created_by=session.get("display_name") or session.get("epic_id") or "admin",
                priority=payload["priority"],
            )
            if not created:
                flash("Broadcast creation failed.", "error")
                return _admin_redirect("broadcasts")
            flash("Broadcast published to the site controls.", "success")
            return _admin_redirect("broadcasts")

        if action == "broadcast_update":
            payload = _broadcast_payload(request.form)
            if not payload["broadcast_id"]:
                flash("Broadcast id missing for update.", "error")
                return _admin_redirect("broadcasts")
            if not payload["title"]:
                flash("Broadcast title is required.", "error")
                return _admin_redirect("broadcasts", edit_broadcast=payload["broadcast_id"])
            ok = update_site_broadcast(
                broadcast_id=payload["broadcast_id"],
                title=payload["title"],
                body=payload["body"],
                variant=payload["variant"],
                display_mode=payload["display_mode"],
                dismiss_mode=payload["dismiss_mode"],
                duration_seconds=payload["duration_seconds"],
                cta_label=payload["cta_label"],
                cta_href=payload["cta_href"],
                closable=payload["closable"],
                active=payload["active"],
                priority=payload["priority"],
            )
            if not ok:
                flash("Broadcast update failed.", "error")
                return _admin_redirect("broadcasts", edit_broadcast=payload["broadcast_id"])
            flash("Broadcast updated.", "success")
            return _admin_redirect("broadcasts")

        if action == "channel_create":
            payload = _channel_payload(request.form)
            if not payload["name"] or not payload["embed_url"]:
                flash("Channel name and source URL are required.", "error")
                return _admin_redirect("channel-editor")
            created = create_channel(
                name=payload["name"],
                category=payload["category"],
                embed_url=payload["embed_url"],
                description=payload["description"],
                suggested_by=session.get("display_name") or "admin",
                approved=payload["approved"],
                sort_order=payload["sort_order"],
                source_urls_json=payload["source_urls_text"],
                search_terms_json=payload["search_terms_text"],
                provider_hint=payload["provider_hint"],
                rotation_mode=payload["rotation_mode"],
                autoplay=payload["autoplay"],
                transition_title=payload["transition_title"],
                transition_copy=payload["transition_copy"],
                transition_seconds=payload["transition_seconds"],
            )
            if not created:
                flash("Channel creation failed.", "error")
                return _admin_redirect("channel-editor")
            flash("Channel created.", "success")
            return _admin_redirect("catalog")

        if action == "channel_update":
            payload = _channel_payload(request.form)
            if not payload["channel_id"]:
                flash("Channel id missing for update.", "error")
                return _admin_redirect("channel-editor")
            if not payload["name"] or not payload["embed_url"]:
                flash("Channel name and source URL are required.", "error")
                return _admin_redirect("channel-editor", payload["channel_id"])
            ok = update_channel(
                channel_id=payload["channel_id"],
                name=payload["name"],
                category=payload["category"],
                embed_url=payload["embed_url"],
                description=payload["description"],
                sort_order=payload["sort_order"],
                approved=payload["approved"],
                source_urls_json=payload["source_urls_text"],
                search_terms_json=payload["search_terms_text"],
                provider_hint=payload["provider_hint"],
                rotation_mode=payload["rotation_mode"],
                autoplay=payload["autoplay"],
                transition_title=payload["transition_title"],
                transition_copy=payload["transition_copy"],
                transition_seconds=payload["transition_seconds"],
            )
            if not ok:
                flash("Channel update failed.", "error")
                return _admin_redirect("channel-editor", payload["channel_id"])
            flash("Channel updated.", "success")
            return _admin_redirect("catalog")

        channel_id = _to_int(request.form.get("channel_id"))
        if action == "channel_approve":
            if channel_id and approve_channel(channel_id, 1):
                flash("Submission approved.", "success")
            else:
                flash("Approval failed.", "error")
            return _admin_redirect("queue")

        if action == "channel_unpublish":
            if channel_id and approve_channel(channel_id, 0):
                flash("Channel moved back to pending.", "success")
            else:
                flash("Unable to move channel back to pending.", "error")
            return _admin_redirect("catalog")

        if action in {"channel_delete", "channel_reject"}:
            if channel_id and delete_channel(channel_id):
                flash("Submission removed." if action == "channel_reject" else "Channel deleted.", "success")
            else:
                flash("Delete failed.", "error")
            return _admin_redirect("queue" if action == "channel_reject" else "catalog")

        broadcast_id = _to_int(request.form.get("broadcast_id"))
        if action == "broadcast_activate":
            if broadcast_id and set_site_broadcast_active(broadcast_id, True):
                flash("Broadcast activated sitewide.", "success")
            else:
                flash("Unable to activate broadcast.", "error")
            return _admin_redirect("broadcasts")

        if action == "broadcast_deactivate":
            if broadcast_id and set_site_broadcast_active(broadcast_id, False):
                flash("Broadcast deactivated.", "success")
            else:
                flash("Unable to deactivate broadcast.", "error")
            return _admin_redirect("broadcasts")

        if action == "broadcast_delete":
            if broadcast_id and delete_site_broadcast(broadcast_id):
                flash("Broadcast deleted.", "success")
            else:
                flash("Unable to delete broadcast.", "error")
            return _admin_redirect("broadcasts")

        flash("Unknown admin action.", "error")
        return _admin_redirect("overview")

    t = os.path.join(ROOT, "templates", "admin.html")
    if os.path.exists(t):
        members = (get_all_members() or []) if authed else []
        announcements = (get_announcements() or []) if authed else []
        audio_tracks = (get_audio_tracks() or []) if authed else []
        islands = (get_recent_islands(limit=999) or []) if authed else []
        wp_tracks = (get_wp_tracks() or []) if authed else []
        channels = (get_channels(approved_only=False) or []) if authed else []
        broadcasts = (get_site_broadcasts(limit=100) or []) if authed else []
        approved_channels = []
        pending_channels = []
        for channel in channels:
            if channel.get("approved"):
                approved_channels.append(channel)
            else:
                pending_channels.append(channel)
        approved_channels.sort(key=lambda item: ((item.get("category") or ""), int(item.get("sort_order") or 0), item.get("name") or ""))
        pending_channels.sort(key=lambda item: (item.get("category") or "", item.get("name") or "", -(item.get("id") or 0)))

        edit_channel_id = _to_int(request.args.get("edit_channel"))
        edit_channel = get_channel(edit_channel_id) if authed and edit_channel_id else None
        edit_broadcast_id = _to_int(request.args.get("edit_broadcast"))
        edit_broadcast = get_site_broadcast(edit_broadcast_id) if authed and edit_broadcast_id else None
        category_values = set(COMMON_CHANNEL_CATEGORIES)
        category_values.update(
            channel.get("category") or "Other"
            for channel in channels
            if channel.get("category")
        )
        admin_stats = {
            "approved_channels": len(approved_channels),
            "pending_channels": len(pending_channels),
            "channel_categories": len({channel.get("category") or "Other" for channel in channels}),
            "members": len(members or []),
            "announcements": len(announcements or []),
            "whitepages_tracks": len(wp_tracks or []),
            "islands": len(islands or []),
            "audio": len(audio_tracks or []),
            "broadcasts": len(broadcasts or []),
            "active_broadcasts": len([item for item in broadcasts if item.get("active")]),
        }
        return render_template(
            "admin.html",
            authed=authed,
            members=members,
            announcements=announcements,
            broadcasts=broadcasts,
            approved_channels=approved_channels,
            pending_channels=pending_channels,
            edit_channel=edit_channel,
            edit_broadcast=edit_broadcast,
            channel_categories=sorted(category_values),
            channel_provider_hints=CHANNEL_PROVIDER_HINTS,
            channel_rotation_modes=CHANNEL_ROTATION_MODES,
            broadcast_variants=BROADCAST_VARIANTS,
            broadcast_display_modes=BROADCAST_DISPLAY_MODES,
            broadcast_dismiss_modes=BROADCAST_DISMISS_MODES,
            admin_stats=admin_stats,
            system_status=status() if authed else {},
        )
    return serve_index()

@platform_bp.route("/health")
def health():
    st = status()
    members = get_all_members() or []
    islands = get_recent_islands(limit=999) or []
    audio = get_audio_tracks() or []
    return jsonify({**st, "service":"triptokforge","version":"4.1","members":len(members),"islands":len(islands),"audio":len(audio)})
