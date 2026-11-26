"""Check a week sheet against the rules - for generated weeks and hand edits.

python -m roster.check TIMETABLE.xlsx ROSTERDATA.xlsx [--sheet 3011-61226]
"""
import argparse
import re
from datetime import timedelta

import openpyxl

from . import data as rdata
from .common import ALIASES, DAY_NAMES, SECTION_TO_POOL, name_key, with_tags
from .timetable import load_weeks, parse_week


def check_week(week, prev_week, rd):
    night = rd.night_codes
    units = rd.units
    docs = {d.key: d for d in rd.doctors}
    def_off = int(rd.rule("Default off days", 1))
    def_max = int(rd.rule("Default max nights", 2))
    issues = []
    counts = {}
    on_day = {}   # (code, day) -> [DoctorRow]
    week_end = week.start + timedelta(days=6)
    off_count = {}   # OFF COUNT requests overlapping this week
    asked_nights = {}  # MUST WANT NIGHT days this week (can raise max nights)
    night_days = set()  # (doctor key, day index) with a WANT NIGHT request
    dummy = set()  # (doctor key, day index) with a pre-booked MC: shown as a day shift, not counted
    for rq in rd.requests:
        if rq.type == "MC" and rq.start <= week_end and rq.end >= week.start:
            hits = [k for k in docs if name_key(rq.name) in k]
            if len(hits) == 1:
                dummy |= {(hits[0], i) for i in range(7)
                          if rq.start <= week.start + timedelta(days=i) <= rq.end}
        if rq.type == "WANT NIGHT" and rq.must and week.start <= rq.start <= week_end:
            hits = [k for k in docs if name_key(rq.name) in k]
            if len(hits) == 1:
                asked_nights[hits[0]] = asked_nights.get(hits[0], 0) + 1
                night_days.add((hits[0], (rq.start - week.start).days))
        if rq.type == "OFF COUNT" and rq.start <= week_end and rq.end >= week.start:
            hits = [k for k in docs if name_key(rq.name) in k]
            if len(hits) == 1:
                try:
                    off_count[hits[0]] = int(float(rq.show_as or 0))
                except ValueError:
                    pass
    for sec, d in week.all_doctors():
        pool = SECTION_TO_POOL.get(sec.label.upper())
        unit = d.label.upper().strip()
        if not pool and unit not in units:
            continue    # EOP etc.
        doc = docs.get(d.key)
        c = d.codes
        dates = [week.start + timedelta(days=i) for i in range(7)]
        outside = {i for i in range(7) if doc and ((doc.start and dates[i] < doc.start) or (doc.end and dates[i] > doc.end))}
        n = sum(1 for x in c if x in night)
        offs = sum(1 for x in c if x.startswith("OFF"))
        prev = prev_week.find(d.key)[1] if prev_week else None
        carry = prev and (prev.carry == "PN" or prev.codes[6] in night)
        asked = sum(1 for i, x in enumerate(c) if x in night and (d.key, i) in night_days)
        if not pool and n > asked:
            issues.append(f"{d.name}: subspecialty HO ({unit}) has {n - asked} night(s) they did not ask for")
        if doc and not doc.nights_ok and n:
            issues.append(f"{d.name}: has {n} night(s) but Nights allowed = NO")
        mx = doc.max_nights if doc and doc.max_nights is not None else def_max
        mx = max(mx, asked_nights.get(d.key, 0))
        if pool and n > mx:
            issues.append(f"{d.name}: {n} nights (max {mx})")
        want_off = doc.off_days if doc and doc.off_days is not None else def_off
        want_off = off_count.get(d.key, want_off)
        if offs < want_off and not outside and not any(x in ("AL", "MC", "EL") for x in c):
            issues.append(f"{d.name}: {offs} OFF day(s) (needs {want_off})")
        for i in range(7):
            before = (c[i - 1] in night) if i else carry
            if before and c[i] != "PN":
                issues.append(f"{d.name}: {DAY_NAMES[i]} should be PN after a night, is '{c[i] or 'blank'}'")
            if c[i] == "PN" and not before:
                issues.append(f"{d.name}: PN on {DAY_NAMES[i]} without a night before")
            if not c[i] and i not in outside:
                issues.append(f"{d.name}: {DAY_NAMES[i]} is blank")
            if doc and not doc.emot_trained and c[i] == "EMOT AM":
                issues.append(f"{d.name}: EMOT AM on {DAY_NAMES[i]} but not EMOT AM trained (should be EMOT AM TAG)")
            if not pool and c[i].startswith("EMOT") and (d.key, i) not in night_days:
                issues.append(f"{d.name}: subspecialty HO on {c[i]} ({DAY_NAMES[i]})")
        if c[6] in night and d.carry != "PN":
            issues.append(f"{d.name}: night on Sunday - column J should say PN")
        for i, x in enumerate(c):
            if (d.key, i) in dummy:
                continue
            x = ALIASES.get(x, re.sub(r" TAG \d+$", " TAG", x))   # MSW TAG 3 -> MSW TAG
            counts[(x, i)] = counts.get((x, i), 0) + 1
            on_day.setdefault((x, i), []).append(d)
    # EMOT AM TAG always next to an EMOT AM
    for i in range(7):
        if counts.get(("EMOT AM TAG", i), 0) and not counts.get(("EMOT AM", i), 0):
            issues.append(f"EMOT AM TAG on {DAY_NAMES[i]} without an EMOT AM that day")
    # juniors on night need a senior in the same group
    for g in rd.night_groups:
        for i in range(7):
            people = [d for code in g for d in on_day.get((code, i), [])]
            jun = [d for d in people if docs.get(d.key) and docs[d.key].junior]
            sen = [d for d in people if not (docs.get(d.key) and docs[d.key].junior)]
            if jun and not sen:
                issues.append(f"NOT PAIRED: {', '.join(x.name.strip() for x in jun)} on {' / '.join(g)} "
                              f"{DAY_NAMES[i]} without a senior")
    for sr in rd.staffing:
        for d in sorted(sr.days):
            n = sum(counts.get((code, d), 0) for code in with_tags(sr.codes))
            if n < sr.min:
                issues.append(f"SHORT: {sr.label} on {DAY_NAMES[d]}: {n} (min {sr.min})")
            elif n > sr.max:
                issues.append(f"extra: {sr.label} on {DAY_NAMES[d]}: {n} (max {sr.max})")
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timetable")
    ap.add_argument("data")
    ap.add_argument("--sheet")
    a = ap.parse_args()
    wb = openpyxl.load_workbook(a.timetable)
    weeks = load_weeks(wb)
    w = parse_week(wb[a.sheet]) if a.sheet else weeks[0]
    prev = next((x for x in weeks if x.start < w.start), None)
    rd = rdata.read_data_workbook(a.data)
    issues = check_week(w, prev, rd)
    print(f"Checked {w.ws.title}: {len(issues)} issue(s)")
    for i in issues:
        print(" -", i)


if __name__ == "__main__":
    main()
