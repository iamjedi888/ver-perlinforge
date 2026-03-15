"""
Build a static GitHub repo vault manifest from one or more GitHub usernames.

Usage:
    python tools/build_repo_vault.py --config config/repo_vault_sources.example.json

Optional env:
    GITHUB_TOKEN=...   # recommended for higher API rate limits
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"
USER_AGENT = "TriptokForgeRepoVault/1.0"

SECTION_ORDER = [
    ("graphics_3d", "3D / XR / Graphics"),
    ("uefn_verse", "UEFN / Verse / Fortnite"),
    ("data_viz", "Charts / Telemetry / Dashboards"),
    ("broadcast_media", "Broadcast / Media / TV"),
    ("platform_ops", "Platform / Admin / Tooling"),
    ("ai_llm", "AI / LLM / Agents"),
    ("uncategorized", "Other / Manual Review"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def github_get(path: str, token: str | None = None) -> tuple[dict | list, dict]:
    request = Request(f"{API_ROOT}{path}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", USER_AGENT)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
        headers = dict(response.headers.items())
        return json.loads(body), headers


def list_user_repos(username: str, token: str | None, max_count: int, include_forks: bool) -> list[dict]:
    repos: list[dict] = []
    page = 1
    while len(repos) < max_count:
        query = urlencode(
            {
                "per_page": min(100, max_count),
                "page": page,
                "sort": "updated",
                "direction": "desc",
            }
        )
        payload, _headers = github_get(f"/users/{username}/repos?{query}", token=token)
        if not isinstance(payload, list) or not payload:
            break
        for repo in payload:
            if not include_forks and bool(repo.get("fork")):
                continue
            repos.append(repo)
            if len(repos) >= max_count:
                break
        if len(payload) < 100:
            break
        page += 1
    return repos


def days_since(date_text: str | None) -> int:
    if not date_text:
        return 3650
    try:
        stamp = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
    except ValueError:
        return 3650
    delta = datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)
    return max(int(delta.days), 0)


def score_repo(repo: dict, pinned: set[str]) -> float:
    full_name = str(repo.get("full_name") or "")
    stars = int(repo.get("stargazers_count") or 0)
    forks = int(repo.get("forks_count") or 0)
    watchers = int(repo.get("watchers_count") or 0)
    archived = 1 if repo.get("archived") else 0
    recent_days = days_since(repo.get("pushed_at"))
    recency_bonus = max(0, 180 - recent_days) / 30.0
    score = stars * 4 + forks * 2 + watchers + recency_bonus
    if full_name in pinned:
        score += 50
    if repo.get("fork"):
        score -= 5
    if archived:
        score -= 25
    return round(score, 2)


def normalize_blob(repo: dict, manual_tags: dict[str, list[str]]) -> str:
    values = [
        repo.get("name") or "",
        repo.get("full_name") or "",
        repo.get("description") or "",
        repo.get("language") or "",
        repo.get("homepage") or "",
    ]
    manual = manual_tags.get(repo.get("name") or "", []) + manual_tags.get(repo.get("full_name") or "", [])
    values.extend(manual)
    return " ".join(str(value) for value in values).casefold()


def infer_tags(repo: dict, manual_tags: dict[str, list[str]], tag_rules: dict[str, list[str]]) -> list[str]:
    signal = normalize_blob(repo, manual_tags)
    tags: set[str] = set()
    for tag, needles in tag_rules.items():
        if any(str(needle).casefold() in signal for needle in needles):
            tags.add(tag)
    for value in manual_tags.get(repo.get("name") or "", []):
        tags.add(str(value))
    for value in manual_tags.get(repo.get("full_name") or "", []):
        tags.add(str(value))
    return sorted(tags)


def best_section(tags: list[str]) -> str:
    section_slugs = {slug for slug, _title in SECTION_ORDER}
    for tag in tags:
        if tag in section_slugs:
            return tag
    return "uncategorized"


def summarize_repo(repo: dict, tags: list[str], pinned: set[str]) -> dict:
    full_name = str(repo.get("full_name") or "")
    return {
        "name": repo.get("name") or "",
        "full_name": full_name,
        "owner": (repo.get("owner") or {}).get("login") or "",
        "html_url": repo.get("html_url") or "",
        "homepage": repo.get("homepage") or "",
        "description": repo.get("description") or "",
        "language": repo.get("language") or "",
        "default_branch": repo.get("default_branch") or "main",
        "updated_at": repo.get("updated_at") or "",
        "pushed_at": repo.get("pushed_at") or "",
        "stars": int(repo.get("stargazers_count") or 0),
        "forks": int(repo.get("forks_count") or 0),
        "open_issues": int(repo.get("open_issues_count") or 0),
        "fork": bool(repo.get("fork")),
        "archived": bool(repo.get("archived")),
        "tags": tags,
        "section": best_section(tags),
        "score": score_repo(repo, pinned),
        "pinned": full_name in pinned,
    }


def build_manifest(config: dict, token: str | None) -> tuple[dict, dict]:
    users = [str(item).strip() for item in config.get("users", []) if str(item).strip()]
    include_forks = bool(config.get("include_forks"))
    max_repos = int(config.get("max_repos_per_user") or 250)
    pinned = {str(item).strip() for item in config.get("pinned_repos", []) if str(item).strip()}
    manual_tags = config.get("manual_tags", {}) or {}
    tag_rules = config.get("tag_rules", {}) or {}

    all_repos: list[dict] = []
    errors: list[str] = []
    for user in users:
        try:
            repos = list_user_repos(user, token=token, max_count=max_repos, include_forks=include_forks)
            all_repos.extend(repos)
        except HTTPError as exc:
            errors.append(f"{user}: HTTP {exc.code}")
        except URLError as exc:
            errors.append(f"{user}: {exc.reason}")

    summarized = []
    for repo in all_repos:
        tags = infer_tags(repo, manual_tags, tag_rules)
        summarized.append(summarize_repo(repo, tags, pinned))

    summarized.sort(key=lambda item: (-float(item.get("score") or 0), item.get("full_name") or ""))

    sections = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    for repo in summarized:
        grouped[repo.get("section") or "uncategorized"].append(repo)

    for slug, title in SECTION_ORDER:
        repos = grouped.get(slug, [])
        if not repos:
            continue
        sections.append(
            {
                "slug": slug,
                "title": title,
                "count": len(repos),
                "repos": repos[:50],
            }
        )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_users": users,
        "repo_count": len(summarized),
        "pinned_count": len([repo for repo in summarized if repo.get("pinned")]),
        "sections": sections,
        "top_repos": summarized[:40],
        "notes": {
            "include_forks": include_forks,
            "max_repos_per_user": max_repos,
            "uses_github_token": bool(token),
        },
    }

    meta = {
        "errors": errors,
        "users": users,
    }
    return manifest, meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a static GitHub repo vault manifest.")
    parser.add_argument("--config", default="config/repo_vault_sources.example.json", help="Path to repo vault config JSON")
    parser.add_argument("--output", default="", help="Override output path")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 1

    config = load_json(config_path)
    token = os.environ.get("GITHUB_TOKEN") or ""
    manifest, meta = build_manifest(config, token=token or None)

    output_path = Path(args.output or config.get("output_path") or "data/repo_vault_manifest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote repo vault manifest to {output_path}")
    print(f"Users: {', '.join(meta['users'])}")
    print(f"Repos indexed: {manifest['repo_count']}")
    if meta["errors"]:
        print("Warnings:")
        for item in meta["errors"]:
            print(f"  - {item}")
    if token:
        print("Authenticated mode enabled via GITHUB_TOKEN.")
    else:
        print("No GITHUB_TOKEN provided. Expect lower API rate limits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
