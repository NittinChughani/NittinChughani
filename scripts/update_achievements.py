#!/usr/bin/env python3
"""Refresh earned GitHub achievements in the profile README (not just a link)."""
import json
import os
import re
from html import escape
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

USER = os.environ.get("PROFILE_USER", "NittinChughani")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = Path("README.md")
SVG = Path("assets/achievement-milestones.svg")
START, END = "<!-- AUTO-ACHIEVEMENTS:START -->", "<!-- AUTO-ACHIEVEMENTS:END -->"

NAMES = {
    "pull-shark": "Pull Shark",
    "quickdraw": "Quickdraw",
    "yolo": "YOLO",
    "pair-extraordinaire": "Pair Extraordinaire",
    "galaxy-brain": "Galaxy Brain",
    "starstruck": "Starstruck",
    "public-sponsor": "Public Sponsor",
    "arctic-code-vault-contributor": "Arctic Code Vault Contributor",
    "mars-2020-contributor": "Mars 2020 Contributor",
}
BADGE_PATTERN = re.compile(
    r"(?:https?:)?//github\.githubassets\.com/images/modules/profile/achievements/"
    r"([a-z0-9-]+)-(default|bronze|silver|gold)\.png", re.I
)


def api(path, params=None):
    url = "https://api.github.com" + path
    if params:
        url += "?" + urlencode(params)
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "profile-milestone-updater",
               "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def public_repos():
    data, page = [], 1
    while True:
        batch = api("/users/" + quote(USER) + "/repos",
                    {"type": "owner", "per_page": 100, "page": page})
        data.extend(r for r in batch if not r.get("private") and not r.get("fork"))
        if len(batch) < 100:
            return data
        page += 1


def level(value, steps):
    return max((s for s in steps if value >= s), default=None)


def metrics(repos):
    prs = api("/search/issues",
              {"q": "author:" + USER + " type:pr is:merged", "per_page": 1})
    if prs.get("incomplete_results"):
        raise RuntimeError("GitHub PR search incomplete, preserving last achievement cards")
    count = len(repos)
    pages = sum(1 for r in repos if r.get("has_pages"))
    stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    merged = int(prs["total_count"])
    result = []
    for name, value, limits, desc in [
        ("Public Repositories", count, (1, 5, 10, 25, 50, 100), "original public repositories"),
        ("GitHub Pages Projects", pages, (1, 3, 5, 10, 25), "repos with GitHub Pages enabled"),
        ("Stars Received", stars, (1, 5, 10, 25, 50, 100, 500, 1000), "stars across original repositories"),
        ("Merged Pull Requests", merged, (1, 2, 5, 10, 25, 50, 100, 250), "authored PRs merged on GitHub"),
    ]:
        tier = level(value, limits)
        if tier is not None:
            result.append((name, tier, value, desc))
    return result


def official_badges(previous):
    """Read badges visibly awarded on GitHub. No invented badges or static list."""
    url = "https://github.com/" + quote(USER) + "?tab=achievements"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ProfileBot/1.0)",
                                    "Accept": "text/html"})
    try:
        with urlopen(request, timeout=30) as response:
            markup = response.read().decode("utf-8", "replace")
    except Exception as exc:
        print("Public GitHub profile unavailable; retaining previous verified badges:", exc)
        markup = previous  # Preserve badges only if previously recorded in README.

    result = {}
    rank = {"default": 0, "bronze": 1, "silver": 2, "gold": 3}
    for slug, tier in BADGE_PATTERN.findall(markup):
        slug, tier = slug.lower(), tier.lower()
        if slug in NAMES and rank[tier] > rank.get(result.get(slug), -1):
            result[slug] = tier
    return sorted(result.items())


def milestone_svg(items):
    cols, width = 2, 1200
    rows = max(1, (len(items) + cols - 1) // cols)
    height = rows * 132 + 26
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="%d" viewBox="0 0 1200 %d" role="img" aria-label="GitHub development milestones">' % (height, height),
        '<rect x="1" y="1" width="1198" height="%d" rx="20" fill="#121928" stroke="#43506A" stroke-width="2"/>' % (height - 2)
    ]
    colors = ("#A4BAFF", "#72E2D3", "#F9CE83", "#B99BFF")
    for i, (title, tier, value, desc) in enumerate(items):
        x, y = 23 + (i % cols) * 590, 15 + (i // cols) * 132
        accent = colors[i % len(colors)]
        out += [
            '<rect x="%d" y="%d" width="565" height="115" rx="16" fill="#202B40" stroke="#4C5A75"/>' % (x, y),
            '<rect x="%d" y="%d" width="86" height="86" rx="22" fill="#313F5A"/>' % (x+16,y+15),
            '<text x="%d" y="%d" font-size="34" fill="%s" font-weight="800" text-anchor="middle" font-family="Arial,Segoe UI,sans-serif">%d+</text>' % (x+59,y+68,accent,tier),
            '<text x="%d" y="%d" font-size="25" fill="#F2F6FF" font-weight="700" font-family="Arial,Segoe UI,sans-serif">%s</text>' % (x+118,y+49,escape(title)),
            '<text x="%d" y="%d" font-size="17" fill="#B6C7DA" font-family="Arial,Segoe UI,sans-serif">%d %s</text>' % (x+118,y+81,value,escape(desc))
        ]
    out.append('</svg>')
    return "\n".join(out) + "\n"


def render(badges):
    lines = ["", '<p align="center">',
             '<img src="https://raw.githubusercontent.com/' + USER + '/' + USER +
             '/main/assets/achievement-milestones.svg" width="100%" alt="Verified GitHub milestones" />',
             '</p>', '']
    if badges:
        lines += ['<p align="center"><strong>Official GitHub Achievement Badges</strong></p>',
                  '<p align="center">']
        for slug, tier in badges:
            name = NAMES[slug]
            url = ("https://github.githubassets.com/images/modules/profile/achievements/"
                   + slug + "-" + tier + ".png")
            lines.append('<img src="%s" width="92" alt="%s badge" title="%s — %s" />' %
                         (url, escape(name), escape(name), tier))
        lines += ['</p>', '']
    lines += ['<sub>Development milestones and publicly visible GitHub achievement badges '
              'refresh daily. Only badges actually detected on GitHub are shown.</sub>', '']
    return "\n".join(lines)


def main():
    repos = public_repos()
    if not repos:
        raise RuntimeError("No public repos returned; not replacing achievements.")
    items = metrics(repos)
    README.parent.mkdir(parents=True, exist_ok=True)
    data = README.read_text(encoding="utf-8")
    if data.count(START) != 1 or data.count(END) != 1:
        raise RuntimeError("Missing or duplicated README achievement markers.")
    badges = official_badges(data)
    left, suffix = data.split(START, 1)
    _, right = suffix.split(END, 1)
    updated = left + START + render(badges) + END + right
    SVG.parent.mkdir(parents=True, exist_ok=True)
    SVG.write_text(milestone_svg(items), encoding="utf-8")
    if data != updated:
        README.write_text(updated, encoding="utf-8")
    print("Updated milestones:", len(items), "public achievement badges:", len(badges))


if __name__ == "__main__":
    main()
