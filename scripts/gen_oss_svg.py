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

W, H = 720, 214
PAD = 22
BAR_W = W - PAD * 2


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

    # merged PRs per upstream repo, busiest first
    per_repo = {}
    for i in merged["items"]:
        name = i["repository_url"].split("/repos/")[1]
        per_repo[name] = per_repo.get(name, 0) + 1
    ranked = sorted(per_repo.items(), key=lambda kv: (-kv[1], kv[0]))

    return {
        "merged": merged["total_count"],
        "opened": opened["total_count"],
        "issues": issues["total_count"],
        "issues_closed": closed["total_count"],
        "repos": ranked,
    }


def row(idx, label, note, pct, y):
    """A labelled track, a fill that grows on load, and a highlight that keeps
    travelling along the filled portion so the card never looks frozen."""
    fill_w = max(3, round(BAR_W * pct / 100))
    delay = round(0.18 * idx + 0.2, 2)
    return f"""  <g>
    <text class="lbl" x="{PAD}" y="{y}">{esc(label)}</text>
    <text class="val" x="{W - PAD}" y="{y}" text-anchor="end" style="animation-delay:{delay + 0.5}s">{esc(note)}</text>
    <rect class="track" x="{PAD}" y="{y + 9}" width="{BAR_W}" height="8" rx="4"/>
    <rect class="fill"  x="{PAD}" y="{y + 9}" width="{fill_w}" height="8" rx="4"
          style="animation-delay:{delay}s"/>
    <g clip-path="url(#clip{idx})">
      <rect class="gleam g{idx}" x="{PAD}" y="{y + 9}" width="90" height="8"
            fill="url(#gleamGrad)" style="animation-delay:{delay}s"/>
    </g>
  </g>"""


def gleam_keyframes(idx, pct):
    """The highlight is clipped to the filled portion, so it has to travel
    exactly that far — a shared distance would leave short bars looking dead."""
    fill_w = max(3, round(BAR_W * pct / 100))
    return (f"    @keyframes gleam{idx} {{\n"
            f"      0%       {{ transform: translateX(-100px); opacity: 0 }}\n"
            f"      14%      {{ opacity: .95 }}\n"
            f"      66%      {{ opacity: .95 }}\n"
            f"      78%,100% {{ transform: translateX({fill_w}px); opacity: 0 }}\n"
            f"    }}")


def clip(idx, pct, y):
    fill_w = max(3, round(BAR_W * pct / 100))
    return (f'    <clipPath id="clip{idx}">'
            f'<rect x="{PAD}" y="{y + 9}" width="{fill_w}" height="8" rx="4"/></clipPath>')


def build(d):
    rows = [
        ("MERGED UPSTREAM", d["merged"] / max(d["opened"], 1) * 100,
         f'{d["merged"]} merged / {d["opened"]} opened'),
        ("ISSUES RESOLVED", d["issues_closed"] / max(d["issues"], 1) * 100,
         f'{d["issues_closed"]} closed / {d["issues"]} filed'),
        ("REPOS LANDED IN", 100, f'{len(d["repos"])} upstream projects'),
    ]

    body, clips, gleams = [], [], []
    y = 68
    for idx, (label, pct, note) in enumerate(rows):
        clips.append(clip(idx, pct, y))
        gleams.append(gleam_keyframes(idx, pct))
        body.append(row(idx, label, note, pct, y))
        y += 42

    # repo chips, sized to the monospace advance so they never clip their text
    chips, x = [], PAD
    for i, (full, n) in enumerate(d["repos"][:4]):
        name = full.split("/")[-1]
        text = f"{name} {n}"
        w = round(len(text) * 6.0) + 22
        chips.append(
            f'    <g class="chip" style="animation-delay:{round(1.05 + i * 0.12, 2)}s">\n'
            f'      <rect class="chipbg" x="{x}" y="{H - 34}" width="{w}" height="21" rx="10.5"/>\n'
            f'      <text class="chiptx" x="{x + 11}" y="{H - 19}">{esc(name)} '
            f'<tspan class="chipn">{n}</tspan></text>\n'
            f'    </g>'
        )
        x += w + 8

    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")
    total = sum(n for _, n in d["repos"])

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img" aria-label="open source contribution stats: {d['merged']} pull requests merged into {len(d['repos'])} upstream projects">
  <style>
    .bg     {{ fill: #0d1117 }}
    .frame  {{ fill: none; stroke: #30363d; stroke-width: 1 }}
    .ttl    {{ font: 600 13px ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; fill: #f0f6fc; letter-spacing: 1.4px }}
    .hdr    {{ font: 400 11px ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; fill: #58a6ff }}
    .lbl    {{ font: 400 11px ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; fill: #8b949e; letter-spacing: 1px }}
    .val    {{ font: 400 11px ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; fill: #e6edf3 }}
    .foot   {{ font: 400 10px ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; fill: #6e7681 }}
    .track  {{ fill: #21262d }}
    .fill   {{ fill: #58a6ff }}
    .chipbg {{ fill: #161b22; stroke: #30363d; stroke-width: 1 }}
    .chiptx {{ font: 400 10px ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; fill: #8b949e }}
    .chipn  {{ fill: #58a6ff; font-weight: 600 }}
    .rule   {{ stroke: #21262d; stroke-width: 1 }}

    @media (prefers-color-scheme: light) {{
      .bg {{ fill: #ffffff }} .frame {{ stroke: #d0d7de }}
      .ttl {{ fill: #1f2328 }} .hdr {{ fill: #0969da }}
      .lbl {{ fill: #656d76 }} .val {{ fill: #1f2328 }}
      .foot {{ fill: #8c959f }} .track {{ fill: #eaeef2 }} .fill {{ fill: #0969da }}
      .chipbg {{ fill: #f6f8fa; stroke: #d0d7de }}
      .chiptx {{ fill: #656d76 }} .chipn {{ fill: #0969da }}
      .rule {{ stroke: #eaeef2 }}
      .gA, .gC {{ stop-color: #0969da }} .gB {{ stop-color: #218bff }}
    }}

    /* bars grow once, then a highlight keeps sliding along the filled part */
    .fill  {{ transform-box: fill-box; transform-origin: left center; transform: scaleX(0);
             animation: grow 1s cubic-bezier(.2,.85,.25,1) both }}
    @keyframes grow {{ to {{ transform: scaleX(1) }} }}

    .val   {{ opacity: 0; animation: rise .5s ease-out both }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(4px) }} to {{ opacity: 1; transform: translateY(0) }} }}

    .gleam {{ animation-duration: 3.6s; animation-timing-function: ease-in-out;
             animation-iteration-count: infinite }}
    .g0 {{ animation-name: gleam0 }} .g1 {{ animation-name: gleam1 }} .g2 {{ animation-name: gleam2 }}
{chr(10).join(gleams)}

    .chip  {{ opacity: 0; animation: rise .5s ease-out both }}

    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important }}
      .fill {{ transform: scaleX(1) }}
      .val, .chip {{ opacity: 1 }}
      .gleam {{ opacity: 0 }}
    }}
  </style>

  <defs>
    <linearGradient id="gleamGrad" x1="0" y1="0" x2="1" y2="0">
      <stop class="gA" offset="0"   stop-color="#58a6ff" stop-opacity="0"/>
      <stop class="gB" offset=".5"  stop-color="#c9e2ff" stop-opacity=".85"/>
      <stop class="gC" offset="1"   stop-color="#58a6ff" stop-opacity="0"/>
    </linearGradient>
{chr(10).join(clips)}
  </defs>

  <rect class="bg" width="{W}" height="{H}" rx="10"/>
  <rect class="frame" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10"/>

  <text class="ttl" x="{PAD}" y="32">OPEN SOURCE</text>
  <text class="hdr" x="{W - PAD}" y="32" text-anchor="end">{total} merged PRs, all upstream</text>
  <line class="rule" x1="{PAD}" y1="44" x2="{W - PAD}" y2="44"/>

{chr(10).join(body)}

{chr(10).join(chips)}
  <text class="foot" x="{W - PAD}" y="{H - 19}" text-anchor="end">updated {stamp}</text>
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
