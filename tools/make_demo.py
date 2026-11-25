"""Build the public DEMO viewer page (docs/index.html) with every name replaced by a DC / Marvel character.

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

# Stand-in names: DC and Marvel characters (their everyday names)
HEROES = [
    # DC
    "BRUCE WAYNE", "CLARK KENT", "DIANA PRINCE", "BARRY ALLEN", "HAL JORDAN", "ARTHUR CURRY", "VICTOR STONE",
    "OLIVER QUEEN", "DINAH LANCE", "BILLY BATSON", "KARA DANVERS", "JOHN STEWART", "SELINA KYLE",
    "HARLEEN QUINZEL", "PAMELA ISLEY", "DICK GRAYSON", "BARBARA GORDON", "JASON TODD", "TIM DRAKE",
    "DAMIAN WAYNE", "LOIS LANE", "JIMMY OLSEN", "ALFRED PENNYWORTH", "LUCIUS FOX", "KATE KANE",
    "ZATANNA ZATARA", "JOHN CONSTANTINE", "RAY PALMER", "CARTER HALL", "WALLY WEST", "TED KORD",
    "JAIME REYES", "CASSANDRA CAIN", "STEPHANIE BROWN", "CONNER KENT", "RACHEL ROTH", "GARFIELD LOGAN",
    "KORI ANDERS", "SLADE WILSON", "EDWARD NYGMA",
    # Marvel
    "PETER PARKER", "TONY STARK", "STEVE ROGERS", "NATASHA ROMANOFF", "BRUCE BANNER", "THOR ODINSON",
    "CLINT BARTON", "WANDA MAXIMOFF", "SAM WILSON", "BUCKY BARNES", "CAROL DANVERS", "STEPHEN STRANGE",
    "SCOTT LANG", "HOPE VAN DYNE", "MATT MURDOCK", "JESSICA JONES", "LUKE CAGE", "DANNY RAND",
    "FRANK CASTLE", "WADE WILSON", "LOGAN HOWLETT", "JEAN GREY", "SCOTT SUMMERS", "ORORO MUNROE",
    "CHARLES XAVIER", "KURT WAGNER", "KITTY PRYDE", "REED RICHARDS", "SUE STORM", "JOHNNY STORM",
    "BEN GRIMM", "KAMALA KHAN", "MILES MORALES", "GWEN STACY", "MARY JANE WATSON", "MONICA RAMBEAU",
    "PEGGY CARTER", "NICK FURY", "MARIA HILL", "PHIL COULSON", "YELENA BELOVA", "KATE BISHOP",
    "AMERICA CHAVEZ", "RIRI WILLIAMS", "MARC SPECTOR", "JENNIFER WALTERS",
]


def fake_names(n, seed=7, avoid=()):
    """n different character names, in a fixed shuffled order, skipping any that share a word with `avoid`."""
    pool = [h for h in HEROES if not any(t in avoid for t in re.split(r"[\s\-]+", h))]
    random.Random(seed).shuffle(pool)
    if len(pool) < n:
        raise SystemExit(f"Need {n} names but only {len(pool)} usable - add more to HEROES.")
    return pool[:n]


def main(timetable, out_dir=os.path.join(ROOT, "docs")):
    wb = openpyxl.load_workbook(timetable)
    weeks = load_weeks(wb, limit=6)
    real = []
    for w in weeks:
        for s, d in w.all_doctors():
            if d.key not in real:
                real.append(d.key)
    real_words = {t for k in real for t in re.split(r"[\s/'\-]+", k) if len(t) >= 4}
    fake = dict(zip(real, fake_names(len(real), avoid=real_words)))
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
                        '<h1>Surgical HO Roster <span class="badge">DEMO · names from DC &amp; Marvel</span></h1>')
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
