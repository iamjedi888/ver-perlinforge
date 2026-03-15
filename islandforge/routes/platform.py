from flask import (
    Blueprint,
    Response,
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
    create_channel,
    delete_channel,
    get_all_members,
    get_announcements,
    get_audio_tracks,
    get_channel,
    get_channels,
    get_member_islands,
    get_member_room,
    get_member_tickets,
    get_posts,
    get_recent_islands,
    get_wp_tracks,
    post_announcement,
    status,
    update_channel,
    approve_channel,
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
    return {
        "channel_id": _to_int(form.get("channel_id")),
        "name": (form.get("name") or "").strip()[:128],
        "category": ((form.get("category") or "").strip()[:64] or "Other"),
        "embed_url": primary_url[:1024],
        "source_urls_text": source_urls_text,
        "search_terms_text": search_terms_text,
        "description": (form.get("description") or "").strip()[:512],
        "provider_hint": (form.get("provider_hint") or "").strip()[:32],
        "rotation_mode": ((form.get("rotation_mode") or "").strip()[:32] or "single"),
        "autoplay": 1 if _is_checked(form.get("autoplay")) else 0,
        "transition_title": (form.get("transition_title") or "").strip()[:128],
        "transition_copy": (form.get("transition_copy") or "").strip()[:512],
        "transition_seconds": _to_float((form.get("transition_seconds") or "").strip(), 0.9),
        "sort_order": _to_int((form.get("sort_order") or "").strip(), None),
        "approved": 1 if _is_checked(form.get("approved")) else 0,
    }


def _admin_redirect(anchor="overview", edit_channel=None):
    target = url_for("platform.admin", edit_channel=edit_channel) if edit_channel else url_for("platform.admin")
    return redirect(f"{target}#{anchor}")

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
    if not user:
        epic_id = session.get("epic_id")
        if not epic_id:
            return redirect("/home")
        user = {
            "display_name": session.get("display_name", epic_id),
            "account_id": session.get("epic_account_id", epic_id),
            "skin_img": session.get("skin_img", ""),
            "skin_name": session.get("skin_name", "Default"),
        }
    account_id = (
        user.get("account_id")
        or session.get("epic_account_id")
        or session.get("epic_id")
        or ""
    )
    room_data = get_member_room(account_id) if account_id else {"theme": "", "tickets": 0}
    tickets = get_member_tickets(account_id) if account_id else int(room_data.get("tickets") or 0)
    islands = get_member_islands(account_id, limit=6) if account_id else []
    uploads = (get_audio_tracks(account_id) or [])[:6] if account_id else []
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
        epic_connected=bool(session.get("epic_access_token") or session.get("access_token") or account_id),
        admin_authed=bool(session.get("admin_authed")))

@platform_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@platform_bp.route("/admin", methods=["GET","POST"])
def admin():
    authed = bool(session.get("admin_authed"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "login":
            if request.form.get("password") == ADMIN_PASSWORD:
                session["admin_authed"] = True
                flash("Admin session opened.", "success")
                return _admin_redirect("overview")
            else:
                flash("Wrong admin password.", "error")
                return _admin_redirect("login")
        if action == "logout":
            session.pop("admin_authed", None)
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
        }
        return render_template(
            "admin.html",
            authed=authed,
            members=members,
            announcements=announcements,
            approved_channels=approved_channels,
            pending_channels=pending_channels,
            edit_channel=edit_channel,
            channel_categories=sorted(category_values),
            channel_provider_hints=CHANNEL_PROVIDER_HINTS,
            channel_rotation_modes=CHANNEL_ROTATION_MODES,
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
