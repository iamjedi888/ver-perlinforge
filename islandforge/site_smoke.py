"""
TriptokForge smoke test runner.

Run on Oracle after deploy:
    python3 site_smoke.py --base-url http://127.0.0.1:5000

The script checks:
- public health/public pages
- Epic auth entry behavior
- logged-out member gate redirects
- logged-out API gate responses
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirectHandler())


def fetch(base_url: str, path: str, method: str = "GET", data: bytes | None = None) -> tuple[int, dict, str]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"User-Agent": "TriptokForgeSmoke/1.0"},
    )
    try:
        with OPENER.open(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.getcode(), dict(response.headers.items()), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, dict(exc.headers.items()), body


def yes_no(flag: bool) -> str:
    return "YES" if flag else "NO"


def contains_all(body: str, needles: list[str]) -> bool:
    return all(needle in body for needle in needles)


def run_tests(base_url: str) -> int:
    checks = []

    checks.append(
        {
            "name": "health",
            "path": "/health",
            "method": "GET",
            "validate": lambda s, h, b: s == 200 and '"service":"triptokforge"' in b and '"version":"4.1"' in b,
            "detail": "health JSON",
        }
    )
    checks.append(
        {
            "name": "home",
            "path": "/home",
            "method": "GET",
            "validate": lambda s, h, b: s == 200 and ("Connect Epic" in b or "Connect Epic Account" in b),
            "detail": "public home",
        }
    )
    checks.append(
        {
            "name": "privacy",
            "path": "/privacy",
            "method": "GET",
            "validate": lambda s, h, b: s == 200 and "privacy" in b.lower(),
            "detail": "public privacy",
        }
    )
    checks.append(
        {
            "name": "admin_login",
            "path": "/ops",
            "method": "GET",
            "validate": lambda s, h, b: s == 200 and ("ops login" in b.lower() or "staff username" in b.lower()),
            "detail": "ops login screen",
        }
    )
    checks.append(
        {
            "name": "legacy_admin_redirect",
            "path": "/admin",
            "method": "GET",
            "validate": lambda s, h, b: s == 302 and h.get("Location", "").endswith("/ops"),
            "detail": "legacy admin redirect",
        }
    )
    checks.append(
        {
            "name": "epic_entry",
            "path": "/auth/epic",
            "method": "GET",
            "validate": lambda s, h, b: s in {302, 503},
            "detail": "Epic auth entry",
        }
    )

    protected_pages = [
        "/gallery",
        "/feed",
        "/forge",
        "/channels",
        "/community",
        "/esports",
        "/arena",
        "/leaderboard",
        "/news",
        "/cardgame",
        "/dashboard",
        "/room",
    ]
    for path in protected_pages:
        checks.append(
            {
                "name": f"gate_{path.strip('/').replace('/', '_') or 'root'}",
                "path": path,
                "method": "GET",
                "validate": lambda s, h, b: s == 302 and h.get("Location", "").endswith("/home"),
                "detail": "member gate redirect",
            }
        )

    api_checks = [
        ("/api/members", "GET", None),
        ("/api/leaderboard/members", "GET", None),
        ("/api/leaderboard/global", "GET", None),
        ("/api/ecosystem/summary", "GET", None),
        ("/api/news/latest", "GET", None),
        ("/api/news/preferences", "GET", None),
        ("/api/presets", "GET", None),
        ("/api/post", "POST", b"{}"),
        ("/api/suggest_channel", "POST", b"{}"),
        ("/api/save_island", "POST", b"{}"),
        ("/api/set_room_theme", "POST", b"{}"),
        ("/api/forge/download-verse", "POST", b"{}"),
        ("/generate", "POST", b"{}"),
    ]
    for path, method, data in api_checks:
        expected = 302 if path == "/generate" else 401
        checks.append(
            {
                "name": f"api_{path.strip('/').replace('/', '_')}",
                "path": path,
                "method": method,
                "data": data,
                "validate": (
                    (lambda s, h, b: s == 302 and h.get("Location", "").endswith("/home"))
                    if expected == 302
                    else (lambda s, h, b: s == 401 and '"login_required"' in b)
                ),
                "detail": "API/member gate",
            }
        )

    checks.append(
        {
            "name": "whitepages_public",
            "path": "/whitepages",
            "method": "GET",
            "validate": lambda s, h, b: s == 200 and "Whitepages" in b,
            "detail": "public whitepages",
        }
    )

    checks.append(
        {
            "name": "whitepages_tracks_public",
            "path": "/api/whitepages/tracks",
            "method": "GET",
            "validate": lambda s, h, b: s == 200 and b.strip().startswith("["),
            "detail": "public whitepages feed",
        }
    )

    failures = 0
    print(f"Smoke test base URL: {base_url}")
    print("-" * 72)
    for check in checks:
        status, headers, body = fetch(
            base_url,
            check["path"],
            method=check.get("method", "GET"),
            data=check.get("data"),
        )
        ok = check["validate"](status, headers, body)
        if not ok:
            failures += 1
        location = headers.get("Location", "")
        suffix = f" location={location}" if location else ""
        print(f"{yes_no(ok):>3}  status={status:<3}  path={check['path']:<28}  {check['detail']}{suffix}")

    print("-" * 72)
    passed = len(checks) - failures
    print(f"Passed {passed}/{len(checks)} checks")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TriptokForge smoke tests.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Base URL to test")
    args = parser.parse_args()
    return run_tests(args.base_url)


if __name__ == "__main__":
    raise SystemExit(main())
