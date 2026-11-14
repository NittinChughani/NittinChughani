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

def make_svg(stats, languages):
    width = 1400
    lang_rows = max(1, (len(languages) + 2) // 3)
    height = 369 + 165 * lang_rows + 34
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="GitHub statistics and most used programming languages">' % (width, height, width, height)]
    out += [
      '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#161A22"/><stop offset="1" stop-color="#10141B"/></linearGradient><linearGradient id="tile" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#252A34"/><stop offset="1" stop-color="#1C212B"/></linearGradient></defs>',
      '<style>text{font-family:Arial,\'Segoe UI\',sans-serif}.head{fill:#E7EBF6;font-size:28px;font-weight:700}.number{font-size:39px;fill:#F1F3FB;font-weight:800}.label{font-size:16px;letter-spacing:1.1px;fill:#AAB5C9}.lang{font-size:25px;font-weight:700;fill:#F1F4FD}.pct{font-size:24px;font-weight:700;fill:#BBC9E8}</style>',
      '<rect x="2" y="2" rx="16" width="1396" height="268" fill="url(#bg)" stroke="#3C4558" stroke-width="2"/>',
      '<text x="36" y="53" class="head">GitHub Stats</text><path d="M35 69H1365" stroke="#323948"/>'
    ]
    for index, (label, value) in enumerate(stats):
        x = 34 + (index % 3) * 447
        y = 87 + (index // 3) * 83
        out.append('<rect x="%d" y="%d" width="423" height="72" rx="10" fill="url(#tile)" stroke="#4B5362"/>' % (x, y))
        out.append('<text x="%d" y="%d" class="number" text-anchor="middle">%s</text>' % (x + 211, y + 33, escape(str(value))))
        out.append('<text x="%d" y="%d" class="label" text-anchor="middle">%s</text>' % (x + 211, y + 57, escape(label)))
    bottom_height = 78 + 165 * lang_rows + 19
    out += [
      '<rect x="2" y="288" rx="16" width="1396" height="%d" fill="url(#bg)" stroke="#3C4558" stroke-width="2"/>' % bottom_height,
      '<text x="36" y="335" class="head">Most Used Languages</text>',
      '<text x="1364" y="332" fill="#8794AF" font-size="16" text-anchor="end">Based on code in public repositories</text>',
      '<path d="M35 351H1365" stroke="#323948"/>'
    ]
    total = sum(n for _, n in languages)
    for index, (name, size) in enumerate(languages):
        x = 35 + (index % 3) * 447
        y = 373 + (index // 3) * 165
        fg, bg, icon = COLORS.get(name, ("#98B6E8", "#233149", name[:3].upper()))
        pct = (size / total) * 100 if total else 0
        out.append('<rect x="%d" y="%d" width="423" height="148" rx="12" fill="url(#tile)" stroke="#4B5362"/>' % (x, y))
        out.append('<rect x="%d" y="%d" width="90" height="90" rx="19" fill="%s" stroke="%s" stroke-opacity=".48"/>' % (x + 22, y + 23, bg, fg))
        out.append('<text x="%d" y="%d" fill="%s" font-size="%d" font-weight="800" text-anchor="middle">%s</text>' % (x + 67, y + 80, fg, 27 if len(icon) > 2 else 33, escape(icon)))
        out.append('<text x="%d" y="%d" class="lang">%s</text>' % (x + 130, y + 65, escape(name)))
        out.append('<text x="%d" y="%d" class="pct" text-anchor="end">%.1f%%</text>' % (x + 383, y + 65, pct))
        out.append('<rect x="%d" y="%d" width="251" height="10" rx="5" fill="#343B4A"/>' % (x + 130, y + 92))
        out.append('<rect x="%d" y="%d" width="%.2f" height="10" rx="5" fill="%s"/>' % (x + 130, y + 92, max(1, 251 * pct / 100), fg))
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
    OUT.write_text(make_svg(stats, languages), encoding="utf-8")
    print("Updated", OUT, "with", len(languages), "languages")

if __name__ == "__main__":
    main()
