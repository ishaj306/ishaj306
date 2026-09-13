#!/usr/bin/env python3
"""
Regenerate assets/activity.svg from live GitHub data.

Design language mirrors the rest of the profile (wine / gold / cream / rose).
No third-party dependencies — standard library only. Uses GITHUB_TOKEN when
present (higher rate limit); works unauthenticated for public data too.

Run:  python scripts/generate_activity.py
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = "ishaj306"
# Repos never shown / never counted for language share.
EXCLUDE = {USER}            # the profile repo itself
EXCLUDE_FROM_LIST = {"T.Y.CS"}  # coursework dump — real code, but not "work"

# Short, curated context lines for known repos; falls back to language + topics.
TECH_HINTS = {
    "HastaMudra": "Python · Computer Vision",
    "SkillScope": "TypeScript · Next.js",
    "AcadFlow": "Java · Spring Boot · OR-Tools",
    "aura": "Python · LangChain · LangGraph",
    "live-meeting-notes": "Python · Whisper · Ollama",
}

BAR_X, BAR_W, BAR_Y, BAR_H = 80, 1040, 162, 26
# rank-ordered palette for the language segments; "other" is the last colour
RAMP = ["#c9a84c", "#e8c97a", "#ff4d6d", "#c4a882", "#f5edd8"]
OTHER_COLOR = "#7a5a63"
CHAR_W = 7.8  # approx Verdana 14px advance, for legend layout


def gh(url):
    headers = {"User-Agent": "activity-gen", "Accept": "application/vnd.github+json"}
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def collect():
    repos = [r for r in gh(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed")
             if not r["fork"]]
    lang_bytes = {}
    for r in repos:
        if r["name"] in EXCLUDE:
            continue
        try:
            for k, v in gh(r["languages_url"]).items():
                lang_bytes[k] = lang_bytes.get(k, 0) + v
        except Exception as e:  # noqa: BLE001
            print(f"  ! languages for {r['name']}: {e}", file=sys.stderr)

    recent = [r for r in repos
              if r["name"] not in EXCLUDE and r["name"] not in EXCLUDE_FROM_LIST][:5]
    return lang_bytes, recent


def language_segments(lang_bytes):
    total = sum(lang_bytes.values()) or 1
    top = sorted(lang_bytes.items(), key=lambda kv: -kv[1])[:5]
    top_sum = sum(v for _, v in top)
    segs = []  # (name, pct_int, width_px, color)
    x = BAR_X
    acc_pct = 0
    for i, (name, byts) in enumerate(top):
        w = round(BAR_W * byts / total)
        pct = round(100 * byts / total)
        acc_pct += pct
        segs.append([name, pct, x, w, RAMP[i]])
        x += w
    other_w = BAR_X + BAR_W - x
    other_pct = max(0, 100 - acc_pct)
    if other_w > 1:
        segs.append(["Other", other_pct, x, other_w, OTHER_COLOR])
    return segs


def build_svg(segs, recent):
    now = datetime.now(timezone.utc)

    seg_rects = []
    for i, (name, pct, x, w, color) in enumerate(segs):
        begin = 0.5 + i * 0.15
        seg_rects.append(
            f'      <rect x="{x}" y="{BAR_Y}" width="0" height="{BAR_H}" fill="{color}">'
            f'<animate attributeName="width" values="0;{w}" dur="0.9s" begin="{begin:.2f}s" fill="freeze"/></rect>'
        )

    # legend, laid out left to right with measured spacing
    legend = []
    cursor = BAR_X
    for name, pct, x, w, color in segs:
        label, pctlabel = name, f"{pct}%"
        legend.append(
            f'      <circle cx="{cursor + 6}" cy="214" r="5" fill="{color}"/>'
            f'<text x="{cursor + 16}" y="219" fill="#f5edd8">{esc(label)}</text>'
            f'<text x="{cursor + 16 + int(len(label) * CHAR_W) + 8}" y="219" fill="#c4a882">{pctlabel}</text>'
        )
        cursor += 16 + int(len(label) * CHAR_W) + 8 + int(len(pctlabel) * CHAR_W) + 30

    rows = []
    for i, r in enumerate(recent):
        cy = 304 + i * 36
        detail = TECH_HINTS.get(r["name"]) or (r.get("language") or "—")
        pushed = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        when = pushed.strftime("updated %b %Y")
        begin = 1.5 + i * 0.15
        rule = ("" if i == len(recent) - 1 else
                f'<line x1="80" y1="{cy + 18}" x2="1120" y2="{cy + 18}" stroke="#c9a84c" stroke-width="1" opacity="0.1"/>')
        rows.append(
            f'      <g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.7s" begin="{begin:.2f}s" fill="freeze"/>'
            f'<circle cx="88" cy="{cy}" r="3.5" fill="#e8c97a"/>'
            f'<text x="104" y="{cy + 5}" fill="#f5edd8" font-size="15">{esc(r["name"])}</text>'
            f'<text x="470" y="{cy + 5}" fill="#c4a882" font-size="14">{esc(detail)}</text>'
            f'<text x="1120" y="{cy + 5}" text-anchor="end" fill="#c4a882" font-size="14">{when}</text>'
            f'{rule}</g>'
        )

    desc_langs = ", ".join(f"{n} {p}%" for n, p, *_ in segs)
    desc_recent = ", ".join(r["name"] for r in recent)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 476" width="1200" height="476" role="img" aria-labelledby="at ad">
  <title id="at">The work, in motion</title>
  <desc id="ad">Language distribution &#8212; {esc(desc_langs)}. Recently active: {esc(desc_recent)}. Generated {now:%Y-%m-%d}.</desc>
  <defs>
    <radialGradient id="abg" cx="50%" cy="0%" r="120%">
      <stop offset="0%" stop-color="#3d0020"/>
      <stop offset="60%" stop-color="#2d0014"/>
      <stop offset="100%" stop-color="#180009"/>
    </radialGradient>
    <clipPath id="barclip"><rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_W}" height="{BAR_H}" rx="8"/></clipPath>
  </defs>
  <rect width="1200" height="476" fill="url(#abg)"/>

  <g opacity="0">
    <animate attributeName="opacity" values="0;1" dur="1s" begin="0.1s" fill="freeze"/>
    <text x="600" y="60" text-anchor="middle" fill="#c9a84c" font-size="22" letter-spacing="8" font-family="Verdana, Geneva, sans-serif">THE WORK, IN MOTION</text>
    <text x="600" y="92" text-anchor="middle" fill="#c4a882" font-size="17" font-style="italic" font-family="Georgia, 'Times New Roman', serif">A snapshot of what I've been building lately.</text>
    <line x1="520" y1="112" x2="680" y2="112" stroke="#c9a84c" stroke-width="1" opacity="0.5"/>
  </g>

  <g font-family="Verdana, Geneva, sans-serif">
    <text x="80" y="150" fill="#c9a84c" font-size="13" letter-spacing="3">LANGUAGE DISTRIBUTION</text>
    <g clip-path="url(#barclip)">
      <rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_W}" height="{BAR_H}" fill="#231018"/>
{chr(10).join(seg_rects)}
    </g>

    <g opacity="0" font-size="14">
      <animate attributeName="opacity" values="0;1" dur="0.8s" begin="1.3s" fill="freeze"/>
{chr(10).join(legend)}
    </g>

    <text x="80" y="278" fill="#c9a84c" font-size="13" letter-spacing="3">RECENTLY ACTIVE</text>
    <g>
{chr(10).join(rows)}
    </g>
  </g>
</svg>
'''


def main():
    lang_bytes, recent = collect()
    if not lang_bytes or not recent:
        print("No data fetched; leaving activity.svg untouched.", file=sys.stderr)
        return 1
    svg = build_svg(language_segments(lang_bytes), recent)
    out = Path(__file__).resolve().parent.parent / "assets" / "activity.svg"
    out.write_text(svg, encoding="utf-8")
    print(f"Wrote {out} ({len(svg)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
