#!/usr/bin/env python3
"""Synchronize verifiable GitHub development milestones into the profile README.

Only the content between the AUTO-ACHIEVEMENTS markers is managed.
Uses GitHub's public REST API; no external achievement service is required.
"""
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from html import escape

USER = os.environ.get("PROFILE_USER", "NittinChughani")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = Path("README.md")
START = "<!-- AUTO-ACHIEVEMENTS:START -->"
END = "<!-- AUTO-ACHIEVEMENTS:END -->"


def github(path, params=None):
    url = "https://api.github.com" + path
    if params:
        url += "?" + urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nittinchughani-profile-achievements",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def public_repositories():
    repos = []
    page = 1
    while True:
        batch = github("/users/" + quote(USER) + "/repos",
                       {"type": "owner", "per_page": 100, "page": page})
        repos.extend(repo for repo in batch if not repo.get("private")
                     and not repo.get("fork"))
        if len(batch) < 100:
            return repos
        page += 1


def reached(count, thresholds):
    return max((threshold for threshold in thresholds if count >= threshold),
               default=None)


def milestones(repos, merged_prs):
    repo_count = len(repos)
    pages = sum(bool(repo.get("has_pages")) for repo in repos)
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in repos)
    items = []

    level = reached(repo_count, (1, 5, 10, 25, 50, 100))
    if level:
        items.append(("🧩", f"{level}+ Public Repositories",
                      f"{repo_count} original public repositories published."))

    level = reached(pages, (1, 3, 5, 10, 25))
    if level:
        items.append(("🌐", f"{level}+ GitHub Pages Projects",
                      f"{pages} public repositories have GitHub Pages enabled."))

    level = reached(stars, (1, 5, 10, 25, 50, 100, 500, 1000))
    if level:
        items.append(("⭐", f"{level}+ Stars Received",
                      f"{stars} stars across original public repositories."))

    level = reached(merged_prs, (1, 2, 5, 10, 25, 50, 100, 250))
    if level:
        items.append(("🤝", f"{level}+ Merged Pull Requests",
                      f"{merged_prs} authored pull requests merged on GitHub."))
    return items


def render(items):
    lines = ["", '<table>']
    for index in range(0, len(items), 2):
        lines.append("<tr>")
        for icon, title, detail in items[index:index + 2]:
            lines.append(
                '<td width="50%" valign="top">'
                f'<strong>{icon} {escape(title)}</strong>'
                f'<p>{escape(detail)}</p>'
                '</td>'
            )
        if index + 1 == len(items):
            lines.append('<td width="50%"></td>')
        lines.append("</tr>")
    lines += [
        "</table>",
        "",
        "<sub>Updated daily from public GitHub data. These are development milestones, not GitHub-issued achievement badges. "
        f'<a href="https://github.com/{quote(USER)}?tab=achievements">View official GitHub achievements</a>.</sub>',
        "",
    ]
    return "\n".join(lines)


def replace_between_markers(original, replacement):
    if original.count(START) != 1 or original.count(END) != 1:
        raise ValueError("Exactly one pair of achievements markers is required.")
    before, remainder = original.split(START, 1)
    _, after = remainder.split(END, 1)
    return before + START + replacement + END + after


def main():
    repos = public_repositories()
    if not repos:
        raise RuntimeError("No public repositories returned; refusing to erase achievements.")
    # Search results include public pull requests across repositories.
    search = github("/search/issues", {
        "q": f"author:{USER} type:pr is:merged",
        "per_page": 1,
    })
    if search.get("incomplete_results"):
        raise RuntimeError("GitHub search was incomplete; keeping the existing milestones.")
    merged = int(search["total_count"])
    block = render(milestones(repos, merged))
    content = README.read_text(encoding="utf-8")
    updated = replace_between_markers(content, block)
    if updated != content:
        README.write_text(updated, encoding="utf-8")
        print("Achievements updated.")
    else:
        print("Achievements already up to date.")


if __name__ == "__main__":
    main()
