"""
Manage TriptokForge staff and bot-operator logins from the terminal.
"""

from __future__ import annotations

import argparse
import secrets
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from oracle_db import (
    STAFF_ROLE_OPTIONS,
    authenticate_staff_account,
    create_bot_profile,
    create_staff_account,
    get_bot_profile_by_slug,
    get_staff_accounts,
    update_staff_account,
)


DEFAULT_COLORSTHEFORCE = {
    "slug": "colorstheforce",
    "display_name": "ColorsTheForce",
    "badge_label": "AI Moderator",
    "role_label": "Moderator",
    "bio": "In-house TriptokForge AI moderator profile for platform guidance, member signal summaries, and community-safe operator assistance.",
    "tone": "Calm, high-signal, premium console operator",
    "language_profile": "American English",
    "llm_provider": "Google Vertex AI",
    "llm_model": "Gemini 2.5 Flash",
    "llm_family": "Gemini",
    "scope_text": "\n".join(
        [
            "Fortnite and UEFN",
            "Code and computer languages",
            "Human communication and moderation tone",
            "Animals, nature, and conservation",
            "Business, sponsorships, and creator operations",
        ]
    ),
    "surfaces_text": "\n".join(
        [
            "Community moderation",
            "Member guidance",
            "Channel curation notes",
            "WhitePages summaries",
        ]
    ),
    "system_prompt": "Speak as ColorsTheForce, a clearly labeled TriptokForge AI Moderator. Never claim to be an official Epic, Nintendo, or Microsoft representative.",
}


def _generate_password(length: int = 24) -> str:
    # Keep generated passwords easy to transcribe from SSH output and browser-safe.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _print_account(account: dict):
    role = account.get("role") or "unknown"
    username = account.get("username") or ""
    display_name = account.get("display_name") or ""
    linked_bot = account.get("linked_bot_slug") or "-"
    active = "yes" if int(account.get("active") or 0) else "no"
    print(f"{username:20} role={role:12} active={active:3} linked_bot={linked_bot:16} display={display_name}")


def _find_staff_by_username(username: str) -> dict | None:
    username = str(username or "").strip().lower()
    for account in get_staff_accounts() or []:
        if str(account.get("username") or "").strip().lower() == username:
            return account
    return None


def _normalize_overrides(grants: list[str]) -> dict:
    rows = {}
    for grant in grants or []:
        grant = str(grant or "").strip().lower()
        if grant:
            rows[grant] = 1
    return rows


def _ensure_bot_profile():
    existing = get_bot_profile_by_slug(DEFAULT_COLORSTHEFORCE["slug"])
    if existing:
        return existing
    ok = create_bot_profile(**DEFAULT_COLORSTHEFORCE, active=1)
    if not ok:
        raise RuntimeError("Failed to create default ColorsTheForce bot profile.")
    created = get_bot_profile_by_slug(DEFAULT_COLORSTHEFORCE["slug"])
    if not created:
        raise RuntimeError("ColorsTheForce bot profile was created but could not be loaded.")
    return created


def cmd_list(_args: argparse.Namespace) -> int:
    accounts = get_staff_accounts() or []
    if not accounts:
        print("No staff accounts found.")
        return 0
    for account in accounts:
        _print_account(account)
    return 0


def cmd_upsert_staff(args: argparse.Namespace) -> int:
    username = args.username.strip().lower()
    role = args.role.strip().lower()
    if role not in STAFF_ROLE_OPTIONS:
        raise SystemExit(f"Unsupported role: {role}")

    password = args.password or (_generate_password() if args.generate_password else "")
    if not password:
        raise SystemExit("Provide --password or use --generate-password.")

    overrides = _normalize_overrides(args.grant)
    linked_bot_slug = (args.linked_bot_slug or "").strip().lower()
    existing = _find_staff_by_username(username)

    if existing:
        ok = update_staff_account(
            existing.get("id"),
            username,
            args.display_name,
            role,
            password=password,
            linked_bot_slug=linked_bot_slug,
            active=1 if args.active else 0,
            permission_overrides=overrides,
        )
        action = "updated"
    else:
        ok = create_staff_account(
            username,
            args.display_name,
            role,
            password,
            linked_bot_slug=linked_bot_slug,
            active=1 if args.active else 0,
            permission_overrides=overrides,
        )
        action = "created"

    if not ok:
        raise SystemExit(f"Staff account {action} failed for {username}.")

    print(f"Staff account {action}: {username}")
    print(f"Role: {role}")
    if linked_bot_slug:
        print(f"Linked bot: {linked_bot_slug}")
    if overrides:
        print("Overrides:", ", ".join(sorted(overrides)))
    print(f"Password: {password}")
    return 0


def cmd_reset_password(args: argparse.Namespace) -> int:
    username = args.username.strip().lower()
    existing = _find_staff_by_username(username)
    if not existing:
        raise SystemExit(f"Staff account not found: {username}")

    password = args.password or (_generate_password() if args.generate_password else "")
    if not password:
        raise SystemExit("Provide --password or use --generate-password.")

    ok = update_staff_account(
        existing.get("id"),
        existing.get("username") or username,
        existing.get("display_name") or username,
        existing.get("role") or "moderator",
        password=password,
        linked_bot_slug=existing.get("linked_bot_slug") or "",
        active=int(existing.get("active") or 0),
        permission_overrides=existing.get("permission_overrides") or {},
    )
    if not ok:
        raise SystemExit(f"Password reset failed for {username}.")

    print(f"Password reset: {username}")
    print(f"Password: {password}")
    return 0


def cmd_verify_login(args: argparse.Namespace) -> int:
    username = args.username.strip().lower()
    password = args.password or ""
    if not password:
        raise SystemExit("Provide --password to verify a login.")

    account = authenticate_staff_account(username, password)
    if not account:
        print(f"Login check failed: {username}")
        return 1

    print(f"Login check passed: {username}")
    print(f"Role: {account.get('role') or 'unknown'}")
    print(f"Display Name: {account.get('display_name') or username}")
    print(f"Linked Bot: {account.get('linked_bot_slug') or '-'}")
    return 0


def cmd_ensure_colorstheforce(args: argparse.Namespace) -> int:
    _ensure_bot_profile()
    username = (args.username or "colorstheforce").strip().lower()
    display_name = args.display_name or "ColorsTheForce Operator"
    password = args.password or (_generate_password() if args.generate_password else "")
    if not password:
        raise SystemExit("Provide --password or use --generate-password.")

    overrides = {"bots": 1}
    if args.allow_moderation:
        overrides["moderation"] = 1

    existing = _find_staff_by_username(username)
    if existing:
        ok = update_staff_account(
            existing.get("id"),
            username,
            display_name,
            "bot_operator",
            password=password,
            linked_bot_slug="colorstheforce",
            active=1,
            permission_overrides=overrides,
        )
        action = "updated"
    else:
        ok = create_staff_account(
            username,
            display_name,
            "bot_operator",
            password,
            linked_bot_slug="colorstheforce",
            active=1,
            permission_overrides=overrides,
        )
        action = "created"

    if not ok:
        raise SystemExit(f"ColorsTheForce operator account {action} failed.")

    print(f"ColorsTheForce operator {action}: {username}")
    print("Linked bot: colorstheforce")
    print(f"Moderation enabled: {'yes' if args.allow_moderation else 'no'}")
    print(f"Password: {password}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage TriptokForge staff and bot-operator accounts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List current staff accounts.")
    list_parser.set_defaults(func=cmd_list)

    upsert_parser = subparsers.add_parser("upsert-staff", help="Create or update a named staff account.")
    upsert_parser.add_argument("--username", required=True)
    upsert_parser.add_argument("--display-name", required=True)
    upsert_parser.add_argument("--role", required=True, choices=STAFF_ROLE_OPTIONS)
    upsert_parser.add_argument("--password")
    upsert_parser.add_argument("--generate-password", action="store_true")
    upsert_parser.add_argument("--linked-bot-slug", default="")
    upsert_parser.add_argument("--grant", action="append", default=[], help="Permission override to enable. Repeat as needed.")
    upsert_parser.add_argument("--active", action="store_true", default=True)
    upsert_parser.set_defaults(func=cmd_upsert_staff)

    reset_parser = subparsers.add_parser("reset-password", help="Reset the password for an existing staff account.")
    reset_parser.add_argument("--username", required=True)
    reset_parser.add_argument("--password")
    reset_parser.add_argument("--generate-password", action="store_true")
    reset_parser.set_defaults(func=cmd_reset_password)

    verify_parser = subparsers.add_parser("verify-login", help="Verify that a staff login works before using it on the site.")
    verify_parser.add_argument("--username", required=True)
    verify_parser.add_argument("--password", required=True)
    verify_parser.set_defaults(func=cmd_verify_login)

    color_parser = subparsers.add_parser("ensure-colorstheforce", help="Ensure the default ColorsTheForce bot profile and linked bot-operator login exist.")
    color_parser.add_argument("--username", default="colorstheforce")
    color_parser.add_argument("--display-name", default="ColorsTheForce Operator")
    color_parser.add_argument("--password")
    color_parser.add_argument("--generate-password", action="store_true")
    color_parser.add_argument("--allow-moderation", action="store_true", help="Grant moderation override to the linked bot operator.")
    color_parser.set_defaults(func=cmd_ensure_colorstheforce)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
