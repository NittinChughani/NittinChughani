#!/usr/bin/env python3
"""Build a self-hosted profile dashboard from public GitHub API data."""
import json
import os
from collections import Counter
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

USER = os.environ.get("PROFILE_USER", "NittinChughani")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
OUT = Path("assets/github-stats.svg")
LOGOS = json.loads(Path("scripts/language_logos.json").read_text(encoding="utf-8"))["logos"]

def embedded_logo(name, x, y):
    raw = LOGOS.get(name)
    if not raw:
        return None
    # All images are embedded as real vector paths, never external links.
    content = raw[raw.index(">") + 1:raw.rfind("</svg>")]
    return '<svg x="%d" y="%d" width="64" height="64" viewBox="0 0 128 128" aria-label="%s logo">%s</svg>' % (x, y, escape(name), content)


def request(path, params=None):
    url = API + path
    if params:
        url += "?" + urlencode(params)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme-generator", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)

def get_public_repos():
    results = []
    page = 1
    while True:
        batch = request("/users/" + quote(USER) + "/repos", {"type": "owner", "per_page": 100, "page": page})
        results.extend(batch)
        if len(batch) < 100:
            return [r for r in results if not r.get("private") and not r.get("fork")]
        page += 1

def search_count(kind):
    data = request("/search/issues", {"q": "author:" + USER + " type:" + kind, "per_page": 1})
    return int(data["total_count"])

def commit_count():
    return int(request("/search/commits", {"q": "author:" + USER, "per_page": 1})["total_count"])

COLORS = {
    "JavaScript": ("#F7DF1E", "#272313", "JS"), "TypeScript": ("#64A7FC", "#112640", "TS"),
    "Python": ("#FFCA65", "#253449", "PY"), "C": ("#9EC6E4", "#1D3449", "C"),
    "C++": ("#79AFFF", "#17294B", "C++"), "C#": ("#B794FF", "#291D48", "C#"),
    "HTML": ("#F79363", "#39201A", "H5"), "CSS": ("#76BFFF", "#162D47", "CSS"),
    "Java": ("#FF9B71", "#34201E", "JV"), "Shell": ("#9FE7B5", "#19362C", "SH"),
    "Ruby": ("#FF7C8C", "#3A1A2A", "RB"), "PHP": ("#ADACFF", "#27274D", "PHP"),
    "SQL": ("#8ED4D3", "#173538", "SQL")
}

def make_dashboard_svg(stats, languages):
    """A single compact panel: GitHub stats on the left, icon-only languages on the right.

    Language logos are self-contained vector artwork from scripts/language_logos.json.
    No names, proportions, or usage bars are displayed for languages.
    """
    width, height = 1400, 225
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="GitHub statistics and languages used">' % (width, height, width, height),
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#161C2B"/><stop offset="1" stop-color="#111827"/></linearGradient></defs>',
        '<rect x="1" y="1" width="1398" height="223" rx="18" fill="url(#bg)" stroke="#3D4C65" stroke-width="2"/>',
        '<text x="35" y="38" font-family="Arial,Segoe UI,sans-serif" font-size="26" font-weight="700" fill="#F2F6FF">GitHub Stats</text>',
        '<text x="777" y="38" font-family="Arial,Segoe UI,sans-serif" font-size="26" font-weight="700" fill="#F2F6FF">Languages Used</text>',
        '<path d="M757 27V201" stroke="#40516C" stroke-width="2"/>',
    ]
    for index, (label, value) in enumerate(stats):
        x = 35 + (index % 2) * 362
        y = 53 + (index // 2) * 77
        out.extend([
            '<rect x="%d" y="%d" width="342" height="67" rx="11" fill="#222E43" stroke="#40516A"/>' % (x, y),
            '<text x="%d" y="%d" font-family="Arial,Segoe UI,sans-serif" text-anchor="middle" font-size="31" font-weight="800" fill="#F3F6FF">%s</text>' % (x + 171, y + 31, escape(str(value))),
            '<text x="%d" y="%d" font-family="Arial,Segoe UI,sans-serif" text-anchor="middle" font-size="13" letter-spacing=".5" fill="#A9BAD4">%s</text>' % (x + 171, y + 53, escape(label)),
        ])
    # Six compact logo tiles in one row; further languages wrap to a second row.
    visible = languages[:12]
    if len(visible) <= 6:
        count = len(visible)
        tile_w = 82
        step = 96
        start = 782 + max(0, (582 - (count * tile_w + (count - 1) * (step - tile_w))) // 2)
        for i, (name, _) in enumerate(visible):
            x, y = start + i * step, 74
            out.extend(language_tile(name, x, y, tile_w))
    else:
        step = 96
        for i, (name, _) in enumerate(visible):
            x = 782 + (i % 6) * step
            y = 58 + (i // 6) * 83
            out.extend(language_tile(name, x, y, 73))
    out.append('</svg>')
    return "\n".join(out) + "\n"


def language_tile(name, x, y, tile_w):
    fg, bg, fallback = COLORS.get(name, ("#9EB9E9", "#24344A", name[:3].upper()))
    out = ['<rect x="%d" y="%d" width="%d" height="%d" rx="17" fill="%s" stroke="%s" stroke-opacity=".6"/>' %
           (x, y, tile_w, tile_w, bg, fg)]
    icon_w = 58 if tile_w >= 80 else 50
    margin = (tile_w - icon_w) // 2
    mark = embedded_logo(name, x + margin, y + margin)
    if mark:
        out.append(mark.replace('width="64" height="64"', 'width="%d" height="%d"' % (icon_w, icon_w)))
    else:
        out.append('<text x="%d" y="%d" text-anchor="middle" font-size="18" font-weight="800" font-family="Arial" fill="%s">%s</text>' %
                   (x + tile_w // 2, y + tile_w // 2 + 6, fg, escape(fallback)))
    return out


def main():
    person = request("/users/" + quote(USER))
    repos = get_public_repos()
    sizes = Counter()
    stars = 0
    for r in repos:
        stars += int(r.get("stargazers_count", 0))
        langs = request("/repos/" + quote(USER) + "/" + quote(r["name"]) + "/languages")
        sizes.update({lang: int(amount) for lang, amount in langs.items()})
    if not sizes:
        raise RuntimeError("No languages found; refusing to overwrite existing chart")
    stats = [
        ("PUBLIC REPOS", len(repos)),
        ("STARS EARNED", stars),
        ("TOTAL COMMITS", commit_count()),
        ("PULL REQUESTS", search_count("pr"))
    ]
    languages = sorted(sizes.items(), key=lambda row: row[1], reverse=True)[:9]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(make_dashboard_svg(stats, languages), encoding="utf-8")
    print("Updated compact stats and language-logo dashboard:", OUT)

if __name__ == "__main__":
    main()
