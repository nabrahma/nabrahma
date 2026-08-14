#!/usr/bin/env python3
"""
Generate assets/oss.svg from live GitHub data.

Runs in GitHub Actions on a schedule. Because the SVG is committed to this
repo and served from raw.githubusercontent.com, it can never fail to render
the way a third-party stats service can.

Usage:  python scripts/gen_oss_svg.py
Env:    GITHUB_TOKEN (optional but recommended — raises the API rate limit)
        GH_USER      (defaults to nabrahma)
"""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "nabrahma")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = "assets/oss.svg"

API = "https://api.github.com/search/issues?q="


def query(q, retries=4):
    """Call the GitHub search API, backing off on secondary rate limits."""
    headers = {
        "User-Agent": f"{USER}-profile-stats",
        "Accept": "application/vnd.github+json",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(API + q, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < retries - 1:
                time.sleep(15 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def collect():
    merged = query(f"author:{USER}+is:pr+is:merged")
    opened = query(f"author:{USER}+is:pr")
    time.sleep(2)
    issues = query(f"author:{USER}+is:issue")
    closed = query(f"author:{USER}+is:issue+is:closed")

    repos = sorted(
        {
            i["repository_url"].split("/repos/")[1]
            for i in merged["items"]
        }
    )
    return {
        "merged": merged["total_count"],
        "opened": opened["total_count"],
        "issues": issues["total_count"],
        "issues_closed": closed["total_count"],
        "repos": repos,
    }


def bar(x, y, w, pct, delay):
    """A track plus a fill that animates out to `pct` on load."""
    fill_w = max(2, round(w * pct / 100))
    return f"""    <rect x="{x}" y="{y}" width="{w}" height="7" rx="3.5" class="track"/>
    <rect x="{x}" y="{y}" width="{fill_w}" height="7" rx="3.5" class="fill"
          style="animation-delay:{delay}s"/>"""


def build(d):
    rows = [
        ("MERGED UPSTREAM", d["merged"] / max(d["opened"], 1) * 100,
         f'{d["merged"]} merged / {d["opened"]} opened'),
        ("ISSUES RESOLVED", d["issues_closed"] / max(d["issues"], 1) * 100,
         f'{d["issues_closed"]} closed / {d["issues"]} filed'),
        ("REPOS LANDED IN", 100, f'{len(d["repos"])} upstream projects'),
    ]

    W, H = 480, 190
    parts = []
    y = 64
    for idx, (label, pct, note) in enumerate(rows):
        parts.append(f'    <text class="lbl" x="20" y="{y}">{esc(label)}</text>')
        parts.append(f'    <text class="val" x="460" y="{y}" text-anchor="end">{esc(note)}</text>')
        parts.append(bar(20, y + 9, 440, pct, round(0.18 * idx + 0.25, 2)))
        y += 42

    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")
    repo_line = " · ".join(r.split("/")[-1] for r in d["repos"][:4])

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img" aria-label="open source contribution stats">
  <style>
    .bg    {{ fill: #0d1117; }}
    .frame {{ fill: none; stroke: #30363d; stroke-width: 1; }}
    .ttl   {{ font: 600 13px ui-monospace, "SF Mono", Menlo, monospace; fill: #ffffff; letter-spacing: 1.2px; }}
    .lbl   {{ font: 400 11px ui-monospace, "SF Mono", Menlo, monospace; fill: #8b949e; letter-spacing: 1px; }}
    .val   {{ font: 400 11px ui-monospace, "SF Mono", Menlo, monospace; fill: #c9d1d9; }}
    .foot  {{ font: 400 10px ui-monospace, "SF Mono", Menlo, monospace; fill: #6e7681; }}
    .track {{ fill: #21262d; }}
    .fill  {{ fill: #ffffff; transform-origin: 20px 0; transform: scaleX(0);
             animation: grow 1.1s cubic-bezier(.2,.8,.2,1) forwards; }}
    @keyframes grow {{ to {{ transform: scaleX(1) }} }}

    @media (prefers-color-scheme: light) {{
      .bg {{ fill: #ffffff; }} .frame {{ stroke: #d0d7de; }}
      .ttl {{ fill: #1f2328; }} .lbl {{ fill: #656d76; }} .val {{ fill: #1f2328; }}
      .foot {{ fill: #8c959f; }} .track {{ fill: #eaeef2; }} .fill {{ fill: #1f2328; }}
    }}
  </style>

  <rect class="bg" width="{W}" height="{H}" rx="8"/>
  <rect class="frame" x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="8"/>

  <text class="ttl" x="20" y="32">OPEN SOURCE</text>
  <line x1="20" y1="44" x2="460" y2="44" stroke="#30363d" stroke-width="1"/>

{chr(10).join(parts)}

  <text class="foot" x="20" y="{H - 16}">{esc(repo_line)}</text>
  <text class="foot" x="460" y="{H - 16}" text-anchor="end">updated {stamp}</text>
</svg>
"""


def main():
    d = collect()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(d))
    print(f"wrote {OUT}: {d['merged']} merged / {d['opened']} opened, "
          f"{d['issues']} issues, {len(d['repos'])} repos")


if __name__ == "__main__":
    main()
