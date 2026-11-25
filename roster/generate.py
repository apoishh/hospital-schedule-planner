"""Make next week's sheet: python -m roster.generate TIMETABLE.xlsx ROSTERDATA.xlsx [--week dd/mm/yyyy]"""
import argparse
import os
import shutil
from datetime import datetime, timedelta

import openpyxl

from . import data as rdata
from . import rotation
from .common import (DAY_NAMES, LEAVE_CODES, POOLS, SECTION_TO_POOL, SPECIAL_CODES,
                     name_key, norm_code, parse_days, sheet_title, to_date, yes)
from .solver import PairRule, Person, solve
from .timetable import COUNTER_COLS, OutRow, OutSection, build_style_map, load_weeks, write_week


class RosterError(Exception):
    pass


class SheetExists(RosterError):
    pass


POOL_COUNTER = {"ETD": "EMOT/ETD", "MSW": "MSW", "FSW": "FSW"}


def _match(key, keys):
    """Exact name, else a unique doctor whose name contains what was typed."""
    if key in keys:
        return key
    hits = [k for k in keys if key in k]
    return hits[0] if len(hits) == 1 else None


def _history(weeks, night_codes):
    h = {}
    for w in weeks:
        for s, d in w.all_doctors():
            e = h.setdefault(d.key, dict(nights=0, weekend_nights=0, special=0, ld=0, weekend_offs=0))
            if not SECTION_TO_POOL.get(s.label.upper()):
                continue
            for i, c in enumerate(d.codes):
                if c in night_codes:
                    e["nights"] += 1
                    if i >= 4:
                        e["weekend_nights"] += 1
                if c in SPECIAL_CODES:
                    e["special"] += 1
                if c.endswith(" LD"):
                    e["ld"] += 1
                if c.startswith("OFF") and i >= 5:
                    e["weekend_offs"] += 1
    return h


def _unit_of(sec, row):
    """Pool (ETD/MSW/FSW) or subspecialty unit a row belongs to."""
    return SECTION_TO_POOL.get(sec.label.upper()) or row.label.upper().strip()


def _counters(base, sec, row, labels):
    """Last week's M-W counters + 1 in the column of last week's ward."""
    vals = [base.ws.cell(row.row, c).value for c in COUNTER_COLS]
    unit = _unit_of(sec, row)
    col_label = POOL_COUNTER.get(unit, unit)
    if col_label in labels:
        i = labels.index(col_label)
        v = vals[i]
        try:
            vals[i] = int(float(v or 0)) + 1
        except (TypeError, ValueError):
            pass   # e.g. '2+1' written by hand - leave it
    return [v if v is not None else 0 for v in vals]


def _weeks_in(counters, labels, pool):
    lab = POOL_COUNTER.get(pool, pool)
    if lab not in labels:
        return 0
    try:
        return int(float(counters[labels.index(lab)] or 0))
    except (TypeError, ValueError):
        return 0


def generate(timetable_path, data_path, week_start=None, save=True, log=print, overwrite=True,
             output_path=None):
    log(f"Opening timetable: {os.path.basename(timetable_path)} (this can take a minute)...")
    wb = openpyxl.load_workbook(timetable_path)
    weeks = load_weeks(wb, limit=15)
    if not weeks:
        if {"DOCTORS", "REQUESTS"} <= {n.upper() for n in wb.sheetnames}:
            raise RosterError(f"'{os.path.basename(timetable_path)}' is the Roster Data file, not the timetable. "
                              "Choose the big workbook with one tab per week in the Timetable box.")
        raise RosterError(f"No week tabs found in '{os.path.basename(timetable_path)}' - "
                          "is the Timetable box pointing at the right file?")

    week_start = to_date(week_start) if week_start else weeks[0].start + timedelta(days=7)
    if week_start.weekday() != 0:
        raise RosterError(f"{week_start:%d/%m/%Y} is not a Monday.")
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    title = sheet_title(week_start)
    if title in wb.sheetnames and not overwrite:
        raise SheetExists(title)
    prev = [w for w in weeks if w.start < week_start]
    if not prev:
        raise RosterError("No earlier week found to start from.")
    base = prev[0]
    if base.start != week_start - timedelta(days=7):
        log(f"Note: last week found is {base.start:%d/%m/%Y}, not the week just before.")
    log(f"Last week: {base.ws.title}  ->  making: {title} ({week_start:%d/%m} - {week_days[-1]:%d/%m/%Y})")
    labels = [str(base.ws.cell(base.sections[0].header_row, c).value or "").strip().upper() for c in COUNTER_COLS]

    # ---- Roster data
    if not os.path.exists(data_path):
        rdata.create_data_workbook(data_path, base)
        log(f"Created {os.path.basename(data_path)} from last week's names. Check DOCTORS before next time.")
    rd = rdata.read_data_workbook(data_path)
    for p in rd.problems:
        log("! " + p)
    night_codes = rd.night_codes
    units = rd.units
    rules = dict(
        borrow=yes(rd.rule("Borrow"), True),
        avoid_on_pn_on=yes(rd.rule("Avoid night"), True),
        different=yes(rd.rule("Make each week"), True),
        hpb_same=yes(rd.rule("HPB:"), True),
        owed=yes(rd.rule("Give owed"), True),
        junior_senior=yes(rd.rule("Juniors on night"), True),
        tag_week=yes(rd.rule("Give EMOT AM TAG"), True),
    )
    def_min = int(rd.rule("Default min nights", 1))
    def_max = int(rd.rule("Default max nights", 2))
    def_off = int(rd.rule("Default off days", 1))
    hist_weeks = int(rd.rule("Weeks of history", 6))
    time_limit = int(rd.rule("Max seconds", 30))
    sub_pref = parse_days(rd.rule("Subspecialty preferred off days", "Sat, Sun"))
    hpb_off = parse_days(rd.rule("HPB team off days", "Thu-Sun"))

    # names in last week's pools / subspecialty that DOCTORS doesn't know -> add them
    known = {d.key for d in rd.doctors}
    missing = []
    for sec in base.sections:
        for d in sec.doctors:
            unit = _unit_of(sec, d)
            if (unit in POOLS or unit in units) and d.key not in known:
                missing.append((d.name.strip(), unit))
    if missing:
        ok = rdata.add_doctors(data_path, missing)
        log(("Added to DOCTORS: " if ok else "Not in DOCTORS (close Roster Data to auto-add): ")
            + ", ".join(n for n, _ in missing))
        for n, unit in missing:
            rd.doctors.append(rdata.Doctor(name=n, pool=unit, nights_ok=unit in POOLS))

    # ---- Pool rotation
    mode = norm_code(rd.rule("Pool rotation", "SUGGEST"))
    if mode in ("SUGGEST", "YES"):
        due_after = int(rd.rule("Weeks in a pool before", 4))
        min_weeks = int(rd.rule("Minimum weeks in a pool", 2))
        cands = []
        for d in rd.doctors:
            if not d.active or d.pool not in POOLS:
                continue
            sec, row = base.find(d.key)
            if not row or _unit_of(sec, row) != d.pool:
                continue      # new, or already moved by hand
            if d.end and d.end <= week_days[-1] + timedelta(days=7):
                continue      # leaving soon
            cur, n = rotation.consecutive_weeks(d.key, prev, _unit_of)
            if n >= max(due_after, min_weeks):
                ctr = _counters(base, sec, row, labels)
                cands.append((d.key, cur, {p: _weeks_in(ctr, labels, p) for p in POOLS}, n, d.name))
        moves = rotation.plan([(k, c, w) for k, c, w, _, _ in cands])
        if cands:
            log("")
            log(f"Pool rotation ({mode}): {len(cands)} HO(s) have done {due_after}+ weeks in the same pool.")
            for k, cur, wk, n, name in cands:
                if k in moves:
                    new = moves[k]
                    never = " (never been there)" if wk.get(new, 0) == 0 else f" ({wk.get(new, 0)} week(s) there before)"
                    log(f"  {'MOVED' if mode == 'YES' else 'suggest'}: {name}: {cur} ({n} weeks) -> {new}{never}")
                else:
                    log(f"  {name}: {cur} ({n} weeks) - no swap available this week")
        if mode == "YES" and moves:
            for d in rd.doctors:
                if d.key in moves:
                    d.pool = moves[d.key]
            if not rdata.set_pools(data_path, moves):
                log("! Could not update Pool in Roster Data (file open?) - moves used for this week only.")

    hist = _history(prev[:hist_weeks], night_codes)
    schedulable = {}
    for sr in rd.staffing:
        for c in sr.codes:
            schedulable.setdefault(c, set()).update(sr.days)

    # ---- People
    people = []
    for d in rd.doctors:
        if not d.active:
            continue
        is_unit = d.pool in units
        if d.pool not in POOLS and not is_unit:
            log(f"! DOCTORS row {d.row}: {d.name} has unknown Pool '{d.pool}' - skipped.")
            continue
        outside = {i for i, day in enumerate(week_days)
                   if (d.start and day < d.start) or (d.end and day > d.end)}
        if len(outside) == 7:
            continue
        nights_ok = d.nights_ok and not is_unit and (d.max_nights is None or d.max_nights > 0)
        p = Person(
            name=d.name, key=d.key, pool=d.pool, is_unit=is_unit,
            nights_ok=nights_ok,
            min_nights=(d.min_nights if d.min_nights is not None else def_min) if nights_ok else 0,
            max_nights=(d.max_nights if d.max_nights is not None else def_max) if nights_ok else 0,
            off_days=d.off_days if d.off_days is not None else def_off,
            junior=d.junior, trained=d.emot_trained,
            fixed={i: "" for i in outside},
        )
        if is_unit:
            if d.pool == "HPB":
                p.off_allowed = hpb_off
            else:
                p.off_pref = sub_pref
        sec, row = base.find(d.key)
        if row:
            p.last_codes = row.codes
            p.owed = row.owed
            p.carry_pn = row.carry == "PN" or row.codes[6] in night_codes
        p.hist = hist.get(d.key, {})
        people.append(p)
    by_key = {p.key: p for p in people}

    # ---- Requests
    all_keys = list(by_key)
    for rq in rd.requests:
        days = [(rq.start + timedelta(days=i) - week_start).days
                for i in range((rq.end - rq.start).days + 1)]
        days = [d for d in days if 0 <= d < 7]
        if not days:
            continue          # request is for another week
        k = _match(name_key(rq.name), all_keys)
        if not k:
            log(f"! REQUESTS row {rq.row}: '{rq.name}' is not working this week (or name matches more than one HO) - skipped.")
            continue
        p = by_key[k]
        span = f"{rq.start:%d/%m}" + (f"-{rq.end:%d/%m}" if rq.end != rq.start else "")
        if rq.type == "OFF COUNT":
            try:
                p.off_days = int(float(rq.show_as or 0))
            except ValueError:
                log(f"! REQUESTS row {rq.row}: OFF COUNT needs a number in 'Show as' - skipped.")
        for d in days:
            if d in p.fixed and p.fixed[d] == "":
                continue      # outside the posting
            if rq.type in LEAVE_CODES or rq.type == "COURSE":
                p.fixed[d] = rq.type if rq.type in LEAVE_CODES else (rq.show_as or "COURSE")
            elif rq.type == "OFF":
                (p.must_off.add(d) if rq.must else p.prefer.append((d, "OFF", "")))
            elif rq.type == "NO NIGHT":
                (p.must_no_night.add(d) if rq.must else p.prefer.append((d, "NO NIGHT", "")))
            elif rq.type == "WANT NIGHT":
                if not p.nights_ok:
                    why = "subspecialty HOs do no nights" if p.is_unit else "Nights allowed = NO"
                    log(f"! {p.name} asked for a night on {DAY_NAMES[d]} but {why} - skipped.")
                    continue
                (p.must_night.add(d) if rq.must else p.prefer.append((d, "WANT NIGHT", "")))
            elif rq.type == "DAY SHIFT":
                (p.must_day.add(d) if rq.must else p.prefer.append((d, "DAY SHIFT", "")))
            elif rq.type == "FIXED SHIFT":
                code = norm_code(rq.show_as)
                if d in schedulable.get(code, set()):
                    (p.must_code.__setitem__(d, code) if rq.must else p.prefer.append((d, "CODE", code)))
                else:
                    p.fixed[d] = rq.show_as or code
            elif rq.type == "ONLY SHIFT":
                p.only[d] = {norm_code(c) for c in rq.show_as.split(",") if c.strip()}
        log(f"Request: {rq.name} {rq.type} {span}" + (f" ({rq.show_as})" if rq.show_as else "")
            + ("" if rq.must else " (prefer)"))
    # look ahead: a request on next Monday means no night this Sunday (it would make Monday PN)
    next_mon = week_start + timedelta(days=7)
    for rq in rd.requests:
        if rq.start <= next_mon <= rq.end and rq.type not in ("NO NIGHT", "ONLY SHIFT", "OFF COUNT"):
            k = _match(name_key(rq.name), all_keys)
            if k and 6 not in by_key[k].fixed and by_key[k].nights_ok:
                by_key[k].must_no_night.add(6)
                log(f"Note: {by_key[k].name} has {rq.type} on Mon {next_mon:%d/%m} - no night this Sunday.")
    for p in people:
        if p.carry_pn and 0 in p.fixed and p.fixed[0]:
            log(f"! {p.name}: had a night last Sunday but has {p.fixed[0]} on Monday - PN dropped.")
            p.carry_pn = False
        if p.carry_pn and 0 in p.must_night:
            log(f"! {p.name}: asked for a night on MON but was on night last Sunday (PN) - request can't be met.")
        if len(p.must_night) > p.max_nights and p.nights_ok:
            log(f"Note: {p.name} asked for {len(p.must_night)} nights this week - max raised from {p.max_nights}.")
            p.max_nights = len(p.must_night)

    # ---- Pairs
    pair_rules = []
    for pr in rd.pairs:
        k = _match(name_key(pr.person), all_keys)
        if not k:
            continue
        partners = []
        for n in pr.partners:
            q = _match(name_key(n), all_keys)
            if q:
                partners.append(q)
        if pr.partners and not partners:
            continue
        label = (f"with {', '.join(by_key[q].name.split()[0] for q in partners)}" if partners else "with a senior")
        pair_rules.append(PairRule(person=k, partners=partners, shifts=pr.shifts, must=pr.must,
                                   label=f"PAIRS row {pr.row}: {label}"))

    # ---- Solve
    log(f"Scheduling {len(people)} HOs (up to {time_limit}s)...")
    res = solve(people, rd.staffing, night_codes, rules, seed=week_start.toordinal(), time_limit=time_limit,
                log=log, open_codes=rd.open_codes, night_groups=rd.night_groups, pairs=pair_rules)
    log(f"Solver: {res.status}")
    if not res.grid:
        for i in res.issues:
            log("! " + i)
        raise RosterError(res.issues[0])

    # ---- Build output sections
    style_map = build_style_map(prev[:6])
    out = []
    placed = set()
    sections = list(base.sections)
    if not any(s.label.upper() == "SUBSPEC" for s in sections) and any(p.is_unit for p in people):
        sections.insert(3, None)    # make a SUBSPEC section from a pool header
    pool_header = (base.ws, base.sections[0].header_row)
    for sec in sections:
        label = sec.label if sec else "SUBSPEC"
        pool = SECTION_TO_POOL.get(label.upper())
        rows = []
        if pool or label.upper() == "SUBSPEC":
            members = [p for p in people if (p.pool == pool if pool else p.is_unit)]
            row_label = (sec.doctors[0].label if sec and sec.doctors else label) if pool else None
            for p in members:
                psec, src_row = base.find(p.key)
                note = src_row.note if src_row else ""
                if src_row and p.owed:
                    left = p.owed - res.owed_given.get(p.key, 0)
                    note = f"*owe {left} off" if left else ""
                counters = _counters(base, psec, src_row, labels) if src_row else [0] * len(COUNTER_COLS)
                hl = POOL_COUNTER.get(p.pool, p.pool)
                rows.append(OutRow(
                    label=row_label or p.pool,
                    name=src_row.name if src_row else p.name,
                    codes=res.grid[p.key], carry="PN" if p.key in res.sunday_night else "", note=note,
                    src=(base.ws, src_row.row) if src_row else None, new=src_row is None,
                    counters=counters, highlight=labels.index(hl) if hl in labels else None))
                placed.add(p.key)
            totals = _totals(sec, pool, res, rd.staffing, base) if pool and sec else []
        else:
            totals = []
            for d in sec.doctors:
                if d.key in by_key or d.key in {x.key for x in rd.doctors}:
                    continue
                rows.append(OutRow(label=d.label, name=d.name, codes=[""] * 7, note=d.note,
                                   src=(base.ws, d.row)))
        out.append(OutSection(label=label, src_header=(base.ws, sec.header_row) if sec else pool_header,
                              rows=rows, totals=totals))

    # ---- Report
    new_people = [p.name for p in people if not base.find(p.key)[1]]
    if new_people:
        log("New this week: " + ", ".join(new_people) + " (name colour left blank)")
    gone = [d.name.strip() for s, d in base.all_doctors()
            if (_unit_of(s, d) in POOLS or _unit_of(s, d) in units) and d.key not in by_key]
    if gone:
        log("Not working this week (left / inactive / outside posting dates): " + ", ".join(gone))
    order = ("SHORT", "REQUEST NOT MET", "NOT PAIRED")
    issues = sorted(res.issues, key=lambda i: next((n for n, o in enumerate(order) if i.startswith(o)), 9))
    gaps = [i for i in issues if i.startswith(order)]
    log("")
    log("RESULT: " + ("all minimum staffing, MUST requests and junior/senior pairs met." if not gaps
                      else f"{len(gaps)} problem(s) to look at (marked !)."))
    for i in issues:
        log(("  ! " if i.startswith(order) else "  - ") + i)

    if save:
        write_week(wb, base, title, week_start, out, style_map)
        target = output_path or timetable_path
        if target == timetable_path:
            bdir = os.path.join(os.path.dirname(os.path.abspath(timetable_path)), "Roster backups")
            os.makedirs(bdir, exist_ok=True)
            stem = os.path.splitext(os.path.basename(timetable_path))[0]
            bpath = os.path.join(bdir, f"{stem} - before {title} - {datetime.now():%Y%m%d-%H%M%S}.xlsx")
            shutil.copy2(timetable_path, bpath)
            log(f"Backup saved: {bpath}")
        log("Saving timetable...")
        try:
            wb.save(target)
        except PermissionError:
            raise RosterError(f"Could not save - please close '{os.path.basename(target)}' in Excel and try again.")
        log(f"Done. New tab '{title}' is the first sheet in {os.path.basename(target)}.")
    return res, people, out


def _totals(sec, pool, res, staffing, base):
    """Totals rows in the same style as the sheet."""
    def cnt(label, d):
        return res.counts.get((label, d))

    def rule(label):
        for sr in staffing:
            if sr.label == label:
                return sr
        return None

    rows = []
    src = [(base.ws, r) for r, _ in sec.total_rows]
    if pool == "ETD":
        specs = [("TOTAL AM HO (ETD) / PM HO (ETD)", "ETD AM", "ETD ON"),
                 ("TOTAL AM HO (EMOT) / PM HO (EMOT)", "EMOT AM", "EMOT PM")]
        for i, (label, a, b) in enumerate(specs):
            vals, short = [], []
            for d in range(7):
                va, vb = cnt(a, d), cnt(b, d)
                vals.append(f"{va if va is not None else '-'} / {vb if vb is not None else '-'}")
                ra, rb = rule(a), rule(b)
                short.append(bool((ra and va is not None and va < ra.min) or (rb and vb is not None and vb < rb.min)))
            rows.append((src[i] if i < len(src) else None, label, vals, short))
    else:
        for i, (label, key) in enumerate([("TOTAL AM HO", f"{pool} SD + {pool} LD"), ("TOTAL ON HO", f"{pool} ON")]):
            r = rule(key)
            vals = [cnt(key, d) for d in range(7)]
            short = [bool(r and v is not None and v < r.min) for v in vals]
            rows.append((src[i] if i < len(src) else None, label, [v if v is not None else "-" for v in vals], short))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("timetable")
    ap.add_argument("data")
    ap.add_argument("--week", help="Monday of the week to make, dd/mm/yyyy (default: week after the newest sheet)")
    ap.add_argument("--out", help="save to this file instead of updating the timetable")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        generate(a.timetable, a.data, a.week, save=not a.dry_run, output_path=a.out)
    except RosterError as e:
        print("ERROR:", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
