#!/usr/bin/env python3
"""
Render the Field Notes feed from data/activity.json.

Writes two things, no dependencies, no network:
  - the block between <!-- FIELD-NOTES:START --> and <!-- FIELD-NOTES:END -->
    in README.md  (Now + the most recent months)
  - ACTIVITY.md   (the full archive, grouped by month, newest first)

To add an activity: append one object to data/activity.json and run this
(or just push — CI runs it for you). The layout takes care of itself.

Entry shape:
  { "date": "2026-09-13", "title": "...", "description": "...",
    "category": "...", "status": "LIVE", "link": "https://..." }   # link optional

Status vocabulary (anything else is coerced to COMPLETED with a warning):
  LIVE · BUILDING · EXPLORING · UPCOMING · COMPLETED
"""
import json
import re
import sys
from datetime import datetime
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "activity.json"
README = ROOT / "README.md"
ARCHIVE = ROOT / "ACTIVITY.md"

VOCAB = {"LIVE", "BUILDING", "EXPLORING", "UPCOMING", "COMPLETED"}
NOW_STATUSES = ("LIVE", "UPCOMING")   # pinned to the top, out of chronological order
README_RECENT = 5                      # dated (non-Now) items kept in the README
START = "<!-- FIELD-NOTES:START -->"
END = "<!-- FIELD-NOTES:END -->"


def parse_date(s):
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise SystemExit(f"activity.json: unparseable date {s!r} (use YYYY-MM-DD)")


def link_label(url):
    if not url:
        return None
    if "github.com" in url:
        return "repo"
    if "isha-gold.vercel.app" in url:
        return "story"
    return "live"


def line(e):
    parts = [f"`{e['status']}` &nbsp;**{e['title']}** — {e['description'].rstrip('.')}."]
    tail = []
    if e.get("category"):
        tail.append(f"_{e['category']}_")
    label = link_label(e.get("link"))
    if label:
        tail.append(f"[{label} ↗]({e['link']})")
    if tail:
        parts.append(" · ".join(tail))
    return "- " + "  \n  ".join(parts)


def load():
    entries = json.loads(DATA.read_text(encoding="utf-8"))
    for e in entries:
        st = str(e.get("status", "")).upper()
        if st not in VOCAB:
            print(f"  ! unknown status {e.get('status')!r} on {e.get('title')!r}"
                  f" — using COMPLETED", file=sys.stderr)
            st = "COMPLETED"
        e["status"] = st
        e["_d"] = parse_date(e["date"])
    return entries


def readme_block(entries):
    now = [e for e in entries if e["status"] in NOW_STATUSES]
    now.sort(key=lambda e: (e["status"] != "LIVE", e["_d"]), reverse=False)
    now.sort(key=lambda e: e["_d"], reverse=True)
    now.sort(key=lambda e: e["status"] != "LIVE")  # LIVE first, then UPCOMING

    dated = sorted((e for e in entries if e["status"] not in NOW_STATUSES),
                   key=lambda e: e["_d"], reverse=True)[:README_RECENT]

    out = []
    if now:
        out.append("**&#9670;&nbsp; Now**\n")
        out += [line(e) for e in now]
        out.append("")
    for month, grp in groupby(dated, key=lambda e: e["_d"].strftime("%B %Y")):
        out.append(f"**{month}**\n")
        out += [line(e) for e in grp]
        out.append("")
    return "\n".join(out).rstrip()


def archive(entries):
    ordered = sorted(entries, key=lambda e: e["_d"], reverse=True)
    out = ["# Field Notes — the full archive", "",
           "<sub>The living log behind my [profile](https://github.com/ishaj306)."
           " Newest first. Edited by hand in "
           "[`data/activity.json`](data/activity.json).</sub>", ""]
    for month, grp in groupby(ordered, key=lambda e: e["_d"].strftime("%B %Y")):
        out.append(f"## {month}\n")
        out += [line(e) for e in grp]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    entries = load()
    block = readme_block(entries)

    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("README.md is missing the FIELD-NOTES markers")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END),
                 f"{START}\n\n{block}\n\n{END}", text, flags=re.S)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("Updated README.md field-notes block")
    else:
        print("README.md field-notes block unchanged")

    arch = archive(entries)
    if not ARCHIVE.exists() or ARCHIVE.read_text(encoding="utf-8") != arch:
        ARCHIVE.write_text(arch, encoding="utf-8")
        print("Wrote ACTIVITY.md")
    else:
        print("ACTIVITY.md unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
