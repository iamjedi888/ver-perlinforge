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

ESPORTS_SECTIONS = [
    {
        "slug": "arena",
        "title": "Arena",
        "status": "Active build",
        "copy": "Competitive hub for ranked ladders, customs, scrims, replay review, and watch-party routing.",
    },
    {
        "slug": "tournaments",
        "title": "Tournaments",
        "status": "Planned ops",
        "copy": "Bracketed events, finals nights, creator cups, rulesets, prize messaging, and admin check-in flow.",
    },
    {
        "slug": "watch",
        "title": "Watch",
        "status": "Live now",
        "copy": "Pull the existing channels rail, replay feeds, and arena watchlist into one esports surface.",
    },
    {
        "slug": "leaderboards",
        "title": "Leaderboards",
        "status": "Live now",
        "copy": "Member stats, ranked divisions, and global Fortnite snapshots already exist and should route through esports.",
    },
    {
        "slug": "teams",
        "title": "Teams + Calendar",
        "status": "Next up",
        "copy": "Squad finder, team cards, match calendar, check-in windows, and season schedules.",
    },
    {
        "slug": "rewards",
        "title": "Rewards + Replay Lab",
        "status": "Next up",
        "copy": "Prize vault, ticket rewards, VOD study rooms, featured clips, and coaching-style breakdowns.",
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

def serve_index():
    return send_from_directory(ROOT, "index.html")


def _is_checked(value):
    return str(value).lower() in {"1", "true", "on", "yes"}


def _to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _short_id(value):
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) <= 18:
        return value
    return f"{value[:8]}...{value[-6:]}"


def _channel_payload(form):
    return {
        "channel_id": _to_int(form.get("channel_id")),
        "name": (form.get("name") or "").strip()[:128],
        "category": ((form.get("category") or "").strip()[:64] or "Other"),
        "embed_url": (form.get("embed_url") or "").strip()[:1024],
        "description": (form.get("description") or "").strip()[:512],
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
