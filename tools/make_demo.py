"""Build the public DEMO viewer page (docs/index.html) with every name replaced by a made-up one.

    python tools/make_demo.py "path/to/real timetable.xlsx"

The real timetable is only read; nothing in it is uploaded. Each real name is
swapped for a fictional one (the same fake name in every week), so the page
shows real-looking shift patterns without identifying anyone. Notes (column K)
are not used by the viewer. Run the name scan below before committing.
"""
import os
import random
import re
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from roster.timetable import load_weeks  # noqa: E402
from roster.viewer import build_site  # noqa: E402

FIRST = ["AISYAH", "DANIEL", "PRIYA", "KEVIN", "NADIA", "JASON", "FARAH", "MICHAEL", "SITI AMINAH", "RAJESH",
         "HANNAH", "FAIZ", "MEI LING", "ARJUN", "SOFIA", "HAZIM", "CHLOE", "IMRAN", "KAVITHA", "LUCAS",
         "ZARA", "ADAM", "NAOMI", "VIKRAM", "ELISE", "IRFAN", "JOANNE", "SURESH", "AMELIA", "HAFIZ",
         "GRACE", "ROHAN", "LAILA", "SAMUEL", "YASMIN", "VICTOR", "DEEPA", "AINA", "MARCUS",
         "SHANTI", "OWEN", "RANIA", "BENJAMIN", "MALINI", "ISAAC", "QISTINA", "THOMAS", "ANJALI", "RYAN",
         "SALMA", "GABRIEL", "NUR IMAN", "PETER", "REENA", "DYLAN", "HUSNA", "OSCAR", "VANITHA", "LEON"]
LAST = ["RAHMAN", "TAN", "KUMARAN", "PETER", "KAMAL", "LAU", "OMAR", "OOI", "YUSOF", "MURUGAN",
        "LEE", "HASSAN", "CHEW", "PILLAI", "NG", "AZMI", "GOH", "SAMY", "LOW", "DAUD",
        "KOH", "TEO", "SALLEH", "PANG", "RAJU", "FOO", "HARUN", "SIM", "GANESAN"]


def fake_names(n, seed=7):
    rnd = random.Random(seed)
    out, seen = [], set()
    while len(out) < n:
        name = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def main(timetable, out_dir=os.path.join(ROOT, "docs")):
    wb = openpyxl.load_workbook(timetable)
    weeks = load_weeks(wb, limit=6)
    real = []
    for w in weeks:
        for s, d in w.all_doctors():
            if d.key not in real:
                real.append(d.key)
    fake = dict(zip(real, fake_names(len(real))))
    real_words = {t for k in real for t in re.split(r"[\s/'\-]+", k) if len(t) >= 4}
    clash = {f for f in fake.values() for t in f.split() if t in real_words}
    if clash:
        raise SystemExit(f"Fake names share words with real names - change FIRST/LAST lists: {sorted(clash)}")
    for w in weeks:
        for s, d in w.all_doctors():
            w.ws.cell(d.row, 2).value = fake[d.key]
            w.ws.cell(d.row, 11).value = None          # notes column (e.g. owed offs) - not needed
    os.makedirs(out_dir, exist_ok=True)
    index = build_site(timetable, out_dir, None, log=print, wb=wb)
    html = open(index, encoding="utf-8").read()
    html = html.replace("<title>Surgical HO Roster</title>", "<title>Surgical HO Roster (demo)</title>")
    html = html.replace("<h1>Surgical HO Roster</h1>",
                        '<h1>Surgical HO Roster <span class="badge">DEMO · made-up names</span></h1>')
    open(index, "w", encoding="utf-8").write(html)
    # GitHub Pages: serve the folder as-is
    open(os.path.join(out_dir, ".nojekyll"), "w").close()
    for extra in ("_headers",):
        p = os.path.join(out_dir, extra)
        if os.path.exists(p):
            os.remove(p)
    leaked = sorted(t for t in real_words if re.search(r"\b" + re.escape(t) + r"\b", html.upper()))
    print("real name words found in page:", leaked or "NONE")
    if leaked:
        raise SystemExit("Not safe to publish - real name words found.")
    print("demo written:", index)


if __name__ == "__main__":
    main(sys.argv[1])
