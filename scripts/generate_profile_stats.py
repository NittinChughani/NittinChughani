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
LANG_OUT = Path("assets/languages-used.svg")
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

def make_stats_svg(stats):
    """Compact, responsive GitHub statistics image."""
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="290" viewBox="0 0 1400 290" role="img" aria-label="Automatically refreshed GitHub statistics">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#151B2C"/><stop offset="1" stop-color="#111724"/></linearGradient></defs>',
        '<rect x="2" y="2" width="1396" height="286" rx="20" fill="url(#bg)" stroke="#3E4B63" stroke-width="2"/>',
        '<text x="38" y="50" font-family="Arial,Segoe UI,sans-serif" font-size="31" font-weight="700" fill="#ECF3FF">GitHub Stats</text>',
        '<path d="M38 70H1362" stroke="#39475E"/>',
    ]
    for idx, (label, value) in enumerate(stats):
        x = 35 + (idx % 3) * 448
        y = 88 + (idx // 3) * 87
        out += [
            '<rect x="%d" y="%d" width="424" height="75" rx="12" fill="#202A3C" stroke="#43516B"/>' % (x, y),
            '<text x="%d" y="%d" text-anchor="middle" font-family="Arial,Segoe UI,sans-serif" font-size="37" font-weight="800" fill="#F2F5FF">%s</text>' % (x + 212, y + 36, escape(str(value))),
            '<text x="%d" y="%d" text-anchor="middle" font-family="Arial,Segoe UI,sans-serif" font-size="15" letter-spacing="1.1" fill="#A6B8D2">%s</text>' % (x + 212, y + 61, escape(label))
        ]
    out.append('</svg>')
    return "\n".join(out) + "\n"


def make_languages_svg(languages):
    """Display original vector language logos, with no usage bars or percentages."""
    rows = max(1, (len(languages) + 2) // 3)
    height = 100 + rows * 182 + 18
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="%d" viewBox="0 0 1400 %d" role="img" aria-label="Programming languages detected in public repositories">' % (height, height),
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#151B2C"/><stop offset="1" stop-color="#111724"/></linearGradient></defs>',
        '<rect x="2" y="2" width="1396" height="%d" rx="20" fill="url(#bg)" stroke="#3E4B63" stroke-width="2"/>' % (height - 4),
        '<text x="38" y="52" font-family="Arial,Segoe UI,sans-serif" font-size="31" font-weight="700" fill="#ECF3FF">Languages Used</text>',
        '<text x="1362" y="50" text-anchor="end" font-family="Arial,Segoe UI,sans-serif" font-size="18" fill="#9BABBD">Detected in public repositories</text>',
        '<path d="M38 70H1362" stroke="#39475E"/>'
    ]
    for i, (name, _) in enumerate(languages):
        x, y = 35 + (i % 3) * 448, 88 + (i // 3) * 182
        fg, bg, fallback = COLORS.get(name, ("#96B5EB", "#23324B", name[:3].upper()))
        out.append('<rect x="%d" y="%d" width="424" height="166" rx="18" fill="#202A3C" stroke="#475672"/>' % (x, y))
        out.append('<rect x="%d" y="%d" width="112" height="112" rx="25" fill="%s" stroke="%s" stroke-opacity=".5" stroke-width="2"/>' % (x + 20, y + 27, bg, fg))
        logo = embedded_logo(name, x + 39, y + 46)
        if logo:
            out.append(logo.replace('width="64" height="64"', 'width="74" height="74"'))
        else:
            out.append('<text x="%d" y="%d" text-anchor="middle" font-size="31" font-family="Arial" font-weight="800" fill="%s">%s</text>' % (x + 76, y + 94, fg, escape(fallback)))
        out.append('<text x="%d" y="%d" font-family="Arial,Segoe UI,sans-serif" font-size="30" font-weight="700" fill="#F2F6FF">%s</text>' % (x + 155, y + 97, escape(name)))
    out.append('</svg>')
    return "\n".join(out) + "\n"

def main():
    person = request("/users/" + quote(USER))
    repos = get_public_repos()
    sizes = Counter()
    stars = forks = 0
    for r in repos:
        stars += int(r.get("stargazers_count", 0))
        forks += int(r.get("forks_count", 0))
        langs = request("/repos/" + quote(USER) + "/" + quote(r["name"]) + "/languages")
        sizes.update({lang: int(amount) for lang, amount in langs.items()})
    if not sizes:
        raise RuntimeError("No languages found; refusing to overwrite existing chart")
    stats = [
        ("PUBLIC REPOS", person["public_repos"]),
        ("STARS EARNED", stars),
        ("TOTAL COMMITS", commit_count()),
        ("PULL REQUESTS", search_count("pr")),
        ("ISSUES", search_count("issue")),
        ("FOLLOWERS", person["followers"])
    ]
    languages = sorted(sizes.items(), key=lambda row: row[1], reverse=True)[:9]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(make_stats_svg(stats), encoding="utf-8")
    LANG_OUT.write_text(make_languages_svg(languages), encoding="utf-8")
    print("Updated", OUT, "and", LANG_OUT, "with", len(languages), "language logos")

if __name__ == "__main__":
    main()
