#!/usr/bin/env python3
"""
Generate the animated section headings in assets/h-*.svg.

They are generated rather than hand-written because each one needs its own
textLength and its own wipe distance baked in: the reveal is a clip rect
animated to the exact pixel width of the text, and guessing that per file is
how headings end up clipped mid-word on a machine whose monospace font has a
different advance.

Usage: python scripts/gen_headers.py
"""

import os

W, H = 900, 48
FS = 20                 # heading font size
ADV = FS * 0.6          # monospace advance at that size
OUT = "assets"

SECTIONS = [
    ("h-quiet",  'What "fails quietly" looks like'),
    ("h-oss",    "Open source"),
    ("h-built",  "Things I've built"),
    ("h-stack",  "Stack"),
    ("h-lately", "Lately"),
]


def esc(s):
    # the quote escape matters: this string is interpolated into aria-label="..."
    # as well as into text content, and a raw " there ends the attribute early
    # and makes the whole file unparseable.
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def build(text):
    w = round(len(text) * ADV)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     role="img" aria-label="{esc(text)}">
  <style>
    .txt  {{ font: 600 {FS}px ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
            fill: #f0f6fc; letter-spacing: .4px }}
    .bar  {{ fill: #58a6ff }}
    .rule {{ stroke: #21262d; stroke-width: 1 }}
    .lead {{ fill: url(#hg) }}

    @media (prefers-color-scheme: light) {{
      .txt  {{ fill: #1f2328 }}
      .bar  {{ fill: #0969da }}
      .rule {{ stroke: #eaeef2 }}
      .hA, .hC {{ stop-color: #0969da }} .hB {{ stop-color: #218bff }}
    }}

    /* the heading types itself in once, then stays put */
    .wipe {{ animation: wipe .65s steps({len(text)}, end) both }}
    @keyframes wipe {{ from {{ width: 0 }} to {{ width: {w}px }} }}

    /* accent bar drops in, then breathes */
    .mark {{ transform-box: fill-box; transform-origin: center;
            animation: drop .5s cubic-bezier(.2,.9,.3,1) both, breathe 3.2s ease-in-out 1s infinite }}
    @keyframes drop   {{ from {{ transform: scaleY(0); opacity: 0 }} to {{ transform: scaleY(1); opacity: 1 }} }}
    @keyframes breathe {{ 0%,100% {{ opacity: 1 }} 50% {{ opacity: .45 }} }}

    /* a light keeps running along the underline */
    .run {{ animation: run 7s cubic-bezier(.45,0,.55,1) infinite }}
    @keyframes run {{
      0%   {{ transform: translateX(-190px); opacity: 0 }}
      12%  {{ opacity: 1 }}
      86%  {{ opacity: 1 }}
      100% {{ transform: translateX({W}px); opacity: 0 }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important }}
      .wipe {{ width: {w}px }}
      .run  {{ display: none }}
    }}
  </style>
  <defs>
    <clipPath id="c"><rect class="wipe" x="18" y="6" height="30" width="0"/></clipPath>
    <linearGradient id="hg" x1="0" y1="0" x2="1" y2="0">
      <stop class="hA" offset="0"  stop-color="#58a6ff" stop-opacity="0"/>
      <stop class="hB" offset=".8" stop-color="#58a6ff" stop-opacity=".9"/>
      <stop class="hC" offset="1"  stop-color="#79c0ff" stop-opacity="1"/>
    </linearGradient>
  </defs>

  <rect class="bar mark" x="0" y="9" width="3.5" height="24" rx="1.75"/>
  <g clip-path="url(#c)">
    <text class="txt" x="18" y="29" textLength="{w}" lengthAdjust="spacingAndGlyphs">{esc(text)}</text>
  </g>
  <line class="rule" x1="0" y1="43" x2="{W}" y2="43"/>
  <g class="run"><rect class="lead" x="0" y="42.2" width="180" height="1.6" rx=".8"/></g>
</svg>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for slug, text in SECTIONS:
        path = os.path.join(OUT, f"{slug}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build(text))
        print(f"wrote {path}  ({len(text)} ch, {round(len(text) * ADV)}px)")


if __name__ == "__main__":
    main()
