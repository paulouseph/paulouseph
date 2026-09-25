"""
generate_stats.py

Pulls basic GitHub stats and top languages for a user via the GitHub REST API
and renders them into two theme-matched SVG files: stats.svg and languages.svg.

Usage (locally):
    export GITHUB_TOKEN=ghp_xxx        # a token with public_repo / repo scope
    export GITHUB_USERNAME=paulouseph
    python generate_stats.py

This is also run automatically by .github/workflows/update-stats.yml on a
schedule, so the two SVGs stay current without manual updates.
"""

import os
import sys
import requests
from collections import Counter

USERNAME = os.environ.get("GITHUB_USERNAME", "paulouseph")
TOKEN = os.environ.get("GITHUB_TOKEN")

API_ROOT = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": f"{USERNAME}-profile-readme-stats",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# Theme colors — keep in sync with README.md / divider.svg
BG = "#060912"
PANEL = "#0d1526"
BORDER = "#1f3b73"
ACCENT = "#6f9bd1"
HIGHLIGHT = "#b53737"
TEXT = "#dbe6f5"
MUTED = "#8fa3c4"


def fetch_user():
    r = requests.get(f"{API_ROOT}/users/{USERNAME}", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_repos():
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"{API_ROOT}/users/{USERNAME}/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "type": "owner"},
            timeout=15,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def fetch_languages(repos):
    totals = Counter()
    for repo in repos:
        if repo.get("fork"):
            continue
        try:
            r = requests.get(repo["languages_url"], headers=HEADERS, timeout=15)
            r.raise_for_status()
            for lang, bytes_count in r.json().items():
                totals[lang] += bytes_count
        except requests.RequestException:
            continue
    return totals


def render_stats_svg(user, repos):
    public_repos = user.get("public_repos", len(repos))
    followers = user.get("followers", 0)
    stars = sum(r.get("stargazers_count", 0) for r in repos)

    rows = [
        ("Public repos", public_repos),
        ("Followers", followers),
        ("Total stars", stars),
    ]

    height = 60 + 34 * len(rows)
    svg_rows = ""
    for i, (label, value) in enumerate(rows):
        y = 70 + i * 34
        svg_rows += f'''
  <text x="30" y="{y}" font-family="Fira Code, monospace" font-size="14" fill="{MUTED}">{label}</text>
  <text x="330" y="{y}" font-family="Fira Code, monospace" font-size="14" font-weight="700" fill="{TEXT}" text-anchor="end">{value}</text>'''

    svg = f'''<svg width="360" height="{height}" viewBox="0 0 360 {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="360" height="{height}" rx="10" fill="{PANEL}"/>
  <rect x="1" y="1" width="358" height="{height - 2}" rx="9" fill="none" stroke="{BORDER}" stroke-opacity="0.6"/>
  <text x="30" y="34" font-family="Fira Code, monospace" font-size="15" font-weight="700" fill="{ACCENT}">GITHUB STATS</text>{svg_rows}
</svg>'''
    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(svg)


def render_languages_svg(totals):
    top = totals.most_common(6)
    total_bytes = sum(v for _, v in top) or 1

    height = 60 + 26 * len(top)
    bars = ""
    colors = [ACCENT, HIGHLIGHT, "#4f7cac", "#8b1e1e", "#2c4a7c", "#5e2a2a"]
    for i, (lang, count) in enumerate(top):
        pct = count / total_bytes
        bar_width = int(220 * pct)
        y = 55 + i * 26
        color = colors[i % len(colors)]
        bars += f'''
  <text x="30" y="{y}" font-family="Fira Code, monospace" font-size="12" fill="{TEXT}">{lang}</text>
  <rect x="120" y="{y - 11}" width="220" height="12" rx="4" fill="{BORDER}" fill-opacity="0.3"/>
  <rect x="120" y="{y - 11}" width="{max(bar_width, 4)}" height="12" rx="4" fill="{color}"/>
  <text x="345" y="{y}" font-family="Fira Code, monospace" font-size="11" fill="{MUTED}">{pct * 100:.0f}%</text>'''

    svg = f'''<svg width="380" height="{height}" viewBox="0 0 380 {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="380" height="{height}" rx="10" fill="{PANEL}"/>
  <rect x="1" y="1" width="378" height="{height - 2}" rx="9" fill="none" stroke="{BORDER}" stroke-opacity="0.6"/>
  <text x="30" y="34" font-family="Fira Code, monospace" font-size="15" font-weight="700" fill="{ACCENT}">TOP LANGUAGES</text>{bars}
</svg>'''
    with open("languages.svg", "w", encoding="utf-8") as f:
        f.write(svg)


def main():
    try:
        user = fetch_user()
        repos = fetch_repos()
        languages = fetch_languages(repos)
    except requests.RequestException as exc:
        print(f"GitHub API request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    render_stats_svg(user, repos)
    render_languages_svg(languages)
    print("Wrote stats.svg and languages.svg")


if __name__ == "__main__":
    main()
