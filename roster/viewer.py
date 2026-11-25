"""Build the read-only viewer website from the timetable workbook.

Output is a folder with a single self-contained index.html (no external
files, works offline), plus files that ask search engines not to index it.
"""
import json
import os
import sys
from datetime import datetime

import openpyxl

from .common import SECTION_TO_POOL, norm_code
from .timetable import FIRST_DAY_COL, build_style_map, load_weeks

DEFAULT_NIGHTS = ["ETD ON", "EMOT PM", "MSW ON", "FSW ON"]
PRIVATE_LEAVE = {"MC", "EL"}      # shown as LEAVE when hiding leave reasons


def _template_path():
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = os.path.join(base, "roster", "viewer_template.html")
        if os.path.exists(p):
            return p
    return os.path.join(os.path.dirname(__file__), "viewer_template.html")


def _hex(color, default=None):
    """openpyxl Color -> '#RRGGBB' (only plain RGB colours; theme colours -> default)."""
    try:
        if color is not None and color.type == "rgb" and isinstance(color.rgb, str) and len(color.rgb) == 8:
            if color.rgb in ("00000000",):
                return default
            return "#" + color.rgb[2:]
    except Exception:
        pass
    return default


def _styles(style_map):
    out = {}
    for code, cell in style_map.items():
        bg = None
        if cell.fill is not None and cell.fill.fill_type == "solid":
            bg = _hex(cell.fill.fgColor)
        fg = _hex(cell.font.color, "#000000" if bg else None) if cell.font else None
        out[code] = {"bg": bg, "fg": fg}
    out["LEAVE"] = out.get("AL", {"bg": None, "fg": "#cc0000"})
    return out


def collect(wb, n_weeks=6, hide_leave=True, night_codes=None):
    weeks = load_weeks(wb, limit=n_weeks)
    style_map = build_style_map(weeks)
    data_weeks = []
    for w in weeks:
        sections = []
        for s in w.sections:
            pool = SECTION_TO_POOL.get(s.label.upper())
            rows = []
            for d in s.doctors:
                codes = []
                for i in range(7):
                    raw = w.ws.cell(d.row, FIRST_DAY_COL + i).value
                    text = "" if raw is None or isinstance(raw, datetime) else " ".join(str(raw).split())
                    if hide_leave and norm_code(text) in PRIVATE_LEAVE:
                        text = "LEAVE"
                    codes.append(text)
                if not any(codes):
                    continue
                rows.append({"name": " ".join(d.name.split()), "unit": d.label, "codes": codes})
            if rows:
                sections.append({"label": s.label, "pool": bool(pool), "rows": rows})
        data_weeks.append({"title": w.ws.title, "start": w.start.isoformat(), "sections": sections})
    return {
        "updated": datetime.now().strftime("%d %b %Y, %H:%M").lstrip("0"),
        "night_codes": [norm_code(c) for c in (night_codes or DEFAULT_NIGHTS)],
        "styles": _styles(style_map),
        "weeks": data_weeks,
    }


def build_site(timetable_path, out_dir, rd=None, log=print, wb=None):
    """Write out_dir/index.html. `rd` is the RosterData (optional, for settings)."""
    n_weeks, hide_leave, nights = 6, True, None
    if rd is not None:
        try:
            n_weeks = int(rd.rule("Viewer: weeks", 6))
        except (TypeError, ValueError):
            pass
        v = str(rd.rule("Viewer: show MC", "YES")).strip().upper()
        hide_leave = v not in ("NO", "N", "FALSE", "0")
        nights = sorted(rd.night_codes, key=lambda c: DEFAULT_NIGHTS.index(c) if c in DEFAULT_NIGHTS else 99)
    if wb is None:
        log("Reading timetable for the viewer...")
        wb = openpyxl.load_workbook(timetable_path)
    data = collect(wb, n_weeks, hide_leave, nights)
    if not data["weeks"]:
        raise ValueError("No week tabs found in the timetable.")
    with open(_template_path(), encoding="utf-8") as f:
        html = f.read()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("/*__DATA__*/", payload)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(out_dir, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nDisallow: /\n")
    with open(os.path.join(out_dir, "_headers"), "w", encoding="utf-8") as f:
        f.write("/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: no-cache\n")
    titles = ", ".join(w["title"] for w in data["weeks"])
    log(f"Viewer built with {len(data['weeks'])} week(s): {titles}")
    return os.path.join(out_dir, "index.html")


def main():
    import argparse
    from . import data as rdata
    ap = argparse.ArgumentParser(description="Build the viewer website folder")
    ap.add_argument("timetable")
    ap.add_argument("out_dir")
    ap.add_argument("--data", help="Roster Data.xlsx (for viewer settings)")
    a = ap.parse_args()
    rd = rdata.read_data_workbook(a.data) if a.data and os.path.exists(a.data) else None
    print(build_site(a.timetable, a.out_dir, rd))


if __name__ == "__main__":
    main()
