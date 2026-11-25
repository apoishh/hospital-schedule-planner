"""Builds the week with Google OR-Tools CP-SAT.

Hard rules (never broken):
  - one shift per doctor per day
  - every night shift is followed by PN; PN only ever follows a night
  - a night on Sunday of last week gives PN on Monday
  - no nights for doctors with Nights allowed = NO, at most Max nights
  - exactly the required number of OFF days (+ owed offs that get given)
  - leave / courses / days outside the posting are fixed
  - EMOT AM only for trained HOs, EMOT AM TAG only for untrained HOs,
    and never a TAG without an EMOT AM the same day
  - subspecialty HOs only work their unit (no nights, no other shifts)
  - ONLY SHIFT requests (e.g. new HOs on LD only)

Everything else is a weighted goal, so a schedule is always produced; anything
that couldn't be met is reported instead of failing. See RULES CHECKLIST.md.
"""
import random
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .common import DAY_NAMES, OFF, PN, code_pool

# Penalty weights (bigger = more important)
W_MUST = 2000            # a MUST request not met
W_BELOW_MIN = 1000       # one HO short of the minimum for a shift
W_PAIR_MUST = 900        # junior on night without a senior / MUST pair not together
W_HPB_OFF_DAY = 500      # HPB team HO off outside the HPB off days
W_MIN_NIGHTS = 400
W_BORROW = 250           # > what a borrowed night frees up: only borrow to fill real gaps
W_OWED_OFF = 150
W_ABOVE_MAX = 120
W_BELOW_TARGET = 60
W_ON_PN_ON = 45
W_PREFER = 40
W_PAIR_PREFER = 40
W_TAG_WEEK = 30          # untrained HO gets no EMOT AM TAG this week
W_HPB_CHANGE = 30
W_SPECIAL_REPEAT = 25
W_SUB_OFF_PREF = 20      # subspecialty HO off on a weekday
W_SAME_NIGHT_DAY = 20
W_SAME_OFF_DAY = 15
W_SAME_CODE = 3

SPECIALS = ("SCOPE/CLINIC", "CLINIC", "SCOPE", "MINOR OT", "HPB")


@dataclass
class Person:
    name: str
    key: str
    pool: str                 # ETD / MSW / FSW, or a subspecialty unit (HPB, VAS...)
    nights_ok: bool
    min_nights: int
    max_nights: int
    off_days: int
    is_unit: bool = False
    junior: bool = False
    trained: bool = True      # EMOT AM trained
    owed: int = 0
    fixed: dict = field(default_factory=dict)        # day -> display text (leave, course, outside posting)
    only: dict = field(default_factory=dict)         # day -> set of allowed codes (ONLY SHIFT)
    must_code: dict = field(default_factory=dict)    # day -> code
    must_off: set = field(default_factory=set)
    must_no_night: set = field(default_factory=set)
    must_night: set = field(default_factory=set)
    must_day: set = field(default_factory=set)       # DAY SHIFT
    prefer: list = field(default_factory=list)       # (day, kind, code)
    off_allowed: set = None   # e.g. HPB team: {3,4,5,6}
    off_pref: set = None      # e.g. subspecialty: {5,6}
    carry_pn: bool = False
    last_codes: list = field(default_factory=lambda: [""] * 7)
    hist: dict = field(default_factory=dict)


@dataclass
class PairRule:
    person: str               # key
    partners: list            # keys; empty = any senior (or any trained HO for TAG)
    shifts: list              # codes; empty = all night codes
    must: bool
    label: str


@dataclass
class Result:
    grid: dict
    sunday_night: set
    owed_given: dict
    issues: list
    status: str
    counts: dict


def solve(people, staffing, night_codes, rules, seed=0, time_limit=30, log=print,
          open_codes=(), night_groups=(), pairs=()):
    m = cp_model.CpModel()
    rnd = random.Random(seed)
    borrow = rules.get("borrow", True)
    open_codes = set(open_codes)
    D = range(7)
    by_key = {p.key: p for p in people}

    day_codes = {d: set() for d in D}
    for sr in staffing:
        for d in sr.days:
            day_codes[d].update(sr.codes)
    group_of = {}
    for g in night_groups:
        for c in g:
            group_of[c] = set(g)

    def allowed(p, d):
        if p.is_unit:
            return [p.pool]
        out = []
        for c in sorted(day_codes[d]):
            pool = code_pool(c)
            if c in night_codes and (not p.nights_ok or p.max_nights == 0):
                continue
            if c == "EMOT AM" and not p.trained:
                continue
            if c == "EMOT AM TAG" and p.trained:
                continue
            if pool is None and c not in open_codes:
                continue          # e.g. a subspecialty unit code
            if pool and pool != p.pool and c not in open_codes and not borrow:
                continue
            out.append(c)
        if d in p.only:
            out = [c for c in out if c in p.only[d]]
        return out

    x, night, pn, off = {}, {}, {}, {}
    objective = []
    must_checks = []     # (person, day, kind, code) for reporting

    def nexpr(p, d):
        return night.get((p.key, d), 0)

    for p in people:
        free = [d for d in D if d not in p.fixed]
        for d in D:
            if d in p.fixed:
                night[p.key, d] = 0
                continue
            codes = allowed(p, d) + [OFF, PN]
            vs = []
            for c in codes:
                v = m.NewBoolVar(f"x[{p.key},{d},{c}]")
                x[p.key, d, c] = v
                vs.append(v)
            m.AddExactlyOne(vs)
            night[p.key, d] = sum(x[p.key, d, c] for c in codes if c in night_codes)
            pn[p.key, d] = x[p.key, d, PN]
            off[p.key, d] = x[p.key, d, OFF]

        # PN exactly after a night
        for d in D:
            if d in p.fixed:
                if d > 0 and not isinstance(night[p.key, d - 1], int):
                    m.Add(night[p.key, d - 1] == 0)   # no night right before leave
                continue
            prev = (1 if p.carry_pn else 0) if d == 0 else night[p.key, d - 1]
            m.Add(pn[p.key, d] == prev)

        # nights
        total_n = sum(night[p.key, d] for d in D)
        night_days = [d for d in free if any(c in night_codes for c in allowed(p, d))]
        if not isinstance(total_n, int):
            if not p.nights_ok:
                m.Add(total_n == 0)
            else:
                m.Add(total_n <= p.max_nights)
                want = min(p.min_nights, len(night_days)) if len(free) >= 4 else 0
                if want > 0:
                    short = m.NewIntVar(0, want, f"nshort[{p.key}]")
                    m.Add(total_n + short >= want)
                    objective.append(W_MIN_NIGHTS * short)

        # offs
        off_req = p.off_days if len(free) >= 2 else 0
        off_req = min(max(off_req, len(p.must_off & set(free))), len(free))
        owed = min(p.owed, max(0, len(free) - off_req - 3)) if rules.get("owed", True) else 0
        g = m.NewIntVar(0, owed, f"owed[{p.key}]")
        m.Add(sum(off[p.key, d] for d in free) == off_req + g)
        objective.append(W_OWED_OFF * (owed - g))
        p._owed_var = g
        for d in free:
            if p.off_allowed is not None and d not in p.off_allowed:
                objective.append(W_HPB_OFF_DAY * off[p.key, d])
            if p.off_pref is not None and d not in p.off_pref:
                objective.append(W_SUB_OFF_PREF * off[p.key, d])

        # MUST requests (very strong goals, reported when impossible)
        for d in sorted(p.must_off & set(free)):
            objective.append(W_MUST * (1 - off[p.key, d]))
            must_checks.append((p, d, "OFF", ""))
        for d in sorted(p.must_no_night & set(free)):
            objective.append(W_MUST * nexpr(p, d))
            must_checks.append((p, d, "NO NIGHT", ""))
        for d in sorted(p.must_night & set(free)):
            objective.append(W_MUST * (1 - nexpr(p, d)))
            must_checks.append((p, d, "WANT NIGHT", ""))
        for d in sorted(p.must_day & set(free)):
            objective.append(W_MUST * (off[p.key, d] + pn[p.key, d] + nexpr(p, d)))
            must_checks.append((p, d, "DAY SHIFT", ""))
        for d, c in p.must_code.items():
            if d in free:
                v = x.get((p.key, d, c))
                objective.append(W_MUST * (1 - v) if v is not None else W_MUST)
                must_checks.append((p, d, "CODE", c))

        # PREFER requests
        for d, kind, c in p.prefer:
            if d not in free:
                continue
            if kind == "OFF":
                objective.append(W_PREFER * (1 - off[p.key, d]))
            elif kind == "NO NIGHT":
                objective.append(W_PREFER * nexpr(p, d))
            elif kind == "WANT NIGHT":
                objective.append(W_PREFER * (1 - nexpr(p, d)))
            elif kind == "DAY SHIFT":
                objective.append(W_PREFER * (off[p.key, d] + pn[p.key, d] + nexpr(p, d)))
            elif kind == "CODE" and (p.key, d, c) in x:
                objective.append(W_PREFER * (1 - x[p.key, d, c]))

        # ON, PN, ON
        if rules.get("avoid_on_pn_on", True):
            seq = [1 if p.last_codes[5] in night_codes else 0, 1 if p.last_codes[6] in night_codes else 0]
            seq += [nexpr(p, d) for d in D]
            for i in range(2, len(seq)):
                a, b = seq[i - 2], seq[i]
                if isinstance(b, int) and b == 0:
                    continue
                if isinstance(a, int):
                    if a == 1:
                        objective.append(W_ON_PN_ON * b)
                    continue
                v = m.NewBoolVar("")
                m.Add(v >= a + b - 1)
                objective.append(W_ON_PN_ON * v)

        # different from last week + fairness + a little randomness
        h = p.hist
        for (k, d, c), v in [(k, v) for k, v in x.items() if k[0] == p.key]:
            cost = rnd.randint(0, 3)
            last = p.last_codes[d]
            if rules.get("different", True) and not p.is_unit:
                if c in night_codes and last in night_codes:
                    cost += W_SAME_NIGHT_DAY
                if c == OFF and last in ("OFF", "OFF (OWE)"):
                    cost += W_SAME_OFF_DAY
                if c == last and c != PN:
                    cost += W_SAME_CODE
            pool = code_pool(c)
            if pool and pool != p.pool and c not in open_codes and not p.is_unit:
                cost += W_BORROW
            if c in night_codes:
                cost += 2 * h.get("nights", 0)
                if d >= 4:
                    cost += 4 + 4 * h.get("weekend_nights", 0)
            if c in SPECIALS and not p.is_unit:
                cost += 4 + 6 * h.get("special", 0)
            if c.endswith(" LD"):
                cost += 1 + 2 * h.get("ld", 0)
            if c == OFF and d >= 5 and not p.is_unit:
                cost += 2 * h.get("weekend_offs", 0)
            if cost:
                objective.append(cost * v)

    # EMOT AM TAG only next to an EMOT AM (hard), and untrained HOs get a TAG each week (goal)
    for d in D:
        tags = [v for (k, dd, c), v in x.items() if dd == d and c == "EMOT AM TAG"]
        if tags:
            ams = [v for (k, dd, c), v in x.items() if dd == d and c == "EMOT AM"]
            m.Add(sum(tags) <= sum(ams))
    if rules.get("tag_week", True):
        for p in people:
            tags = [x[p.key, d, "EMOT AM TAG"] for d in D if (p.key, d, "EMOT AM TAG") in x]
            if tags:
                has = m.NewBoolVar("")
                m.Add(has <= sum(tags))
                objective.append(W_TAG_WEEK * (1 - has))

    # juniors on night need a senior in the same night group
    pair_checks = []
    if rules.get("junior_senior", True):
        for d in D:
            for gcodes in night_groups:
                sen = [x[p.key, d, c] for p in people if not p.junior for c in gcodes if (p.key, d, c) in x]
                for p in people:
                    if not p.junior:
                        continue
                    jv = [x[p.key, d, c] for c in gcodes if (p.key, d, c) in x]
                    if not jv:
                        continue
                    s = m.NewIntVar(0, 1, "")
                    m.Add(sum(jv) <= sum(sen) + s)
                    objective.append(W_PAIR_MUST * s)
                    pair_checks.append((p, d, set(gcodes), None, True, "junior needs a senior on night"))

    # PAIRS tab
    for pr in pairs:
        p = by_key.get(pr.person)
        if not p:
            continue
        shifts = pr.shifts or sorted(night_codes)
        for d in D:
            for s in shifts:
                v = x.get((p.key, d, s))
                if v is None:
                    continue
                if s in night_codes:
                    pcodes = group_of.get(s, {s})
                elif s == "EMOT AM TAG":
                    pcodes = {"EMOT AM"}
                else:
                    pcodes = {s}
                if pr.partners:
                    cand = [by_key[k] for k in pr.partners if k in by_key and k != p.key]
                else:
                    cand = [q for q in people if q.key != p.key and not q.junior]
                ps = [x[q.key, d, c] for q in cand for c in pcodes if (q.key, d, c) in x]
                sl = m.NewIntVar(0, 1, "")
                m.Add(v <= sum(ps) + sl)
                objective.append((W_PAIR_MUST if pr.must else W_PAIR_PREFER) * sl)
                pair_checks.append((p, d, {s}, (cand, pcodes), pr.must, pr.label))

    # HPB continuity for pool HOs covering HPB
    if rules.get("hpb_same", True):
        hpb_days = sorted(d for d in D if "HPB" in day_codes[d])
        for p in people:
            if p.is_unit:
                continue
            for a, b in zip(hpb_days, hpb_days[1:]):
                va, vb = x.get((p.key, a, "HPB")), x.get((p.key, b, "HPB"))
                if va is None and vb is None:
                    continue
                va = va if va is not None else 0
                vb = vb if vb is not None else 0
                ch = m.NewBoolVar("")
                m.Add(ch >= va - vb)
                m.Add(ch >= vb - va)
                objective.append(W_HPB_CHANGE * ch)

    # spread clinic / minor OT across different doctors
    for p in people:
        for c in {c for (k, d, c) in x if k == p.key and c in ("SCOPE/CLINIC", "CLINIC", "SCOPE", "MINOR OT")}:
            vs = [x[p.key, d, c] for d in D if (p.key, d, c) in x]
            if len(vs) > 1:
                extra = m.NewIntVar(0, len(vs), "")
                m.Add(extra >= sum(vs) - 1)
                objective.append(W_SPECIAL_REPEAT * extra)

    # staffing
    slack = []
    for sr in staffing:
        for d in sorted(sr.days):
            terms = [x[p.key, d, c] for p in people for c in sr.codes if (p.key, d, c) in x]
            cnt = sum(terms)
            lo = m.NewIntVar(0, sr.min, "")
            tg = m.NewIntVar(0, sr.target, "")
            hi = m.NewIntVar(0, 60, "")
            m.Add(cnt + lo >= sr.min)
            m.Add(cnt + tg >= sr.target)
            m.Add(cnt - hi <= sr.max)
            objective += [W_BELOW_MIN * lo, W_BELOW_TARGET * tg, W_ABOVE_MAX * hi]
            slack.append((sr, d, terms))

    m.Minimize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_workers = 8
    solver.parameters.random_seed = seed % 1000
    status = solver.Solve(m)
    sname = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return Result(grid={}, sunday_night=set(), owed_given={}, status=sname, counts={},
                      issues=["No schedule possible - the fixed leave / days outside the posting leave no room. "
                              "Check REQUESTS and DOCTORS start / last days."])

    grid, owed_given, sunday = {}, {}, set()
    for p in people:
        row = []
        for d in D:
            if d in p.fixed:
                row.append(p.fixed[d])
                continue
            for c in allowed(p, d) + [OFF, PN]:
                if solver.Value(x[p.key, d, c]):
                    row.append(c)
                    break
        g = solver.Value(p._owed_var)
        owed_given[p.key] = g
        if g:
            idx = [i for i, c in enumerate(row) if c == OFF][-g:]
            for i in idx:
                row[i] = "OFF (owe)"
        grid[p.key] = row
        if row[6] in night_codes:
            sunday.add(p.key)

    # ---- report
    counts, issues = {}, []
    for sr, d, terms in slack:
        n = sum(solver.Value(t) for t in terms)
        counts[sr.label, d] = n
        if n < sr.min:
            issues.append(f"SHORT: {sr.label} on {DAY_NAMES[d]} has {n}, needs at least {sr.min}.")
        elif n < sr.target:
            issues.append(f"below ideal: {sr.label} on {DAY_NAMES[d]} has {n} (ideal {sr.target}).")
        if n > sr.max:
            issues.append(f"extra: {sr.label} on {DAY_NAMES[d]} has {n} (max {sr.max}).")

    def is_night(c):
        return c in night_codes

    for p, d, kind, c in must_checks:
        got = grid[p.key][d]
        ok = {"OFF": got.startswith("OFF"), "NO NIGHT": not is_night(got), "WANT NIGHT": is_night(got),
              "DAY SHIFT": got not in ("PN",) and not got.startswith("OFF") and not is_night(got),
              "CODE": got == c}[kind]
        if not ok:
            want = c if kind == "CODE" else kind.lower()
            issues.append(f"REQUEST NOT MET: {p.name} asked for {want} on {DAY_NAMES[d]} - got {got}.")
    seen = set()
    for p, d, shifts, partner, must, label in pair_checks:
        got = grid[p.key][d]
        if got not in shifts:
            continue
        if partner is None:   # junior/senior
            ok = any(grid[q.key][d] in shifts for q in people if not q.junior)
        else:
            cand, pcodes = partner
            ok = any(grid[q.key][d] in pcodes for q in cand)
        if not ok and (p.key, d, label) not in seen:
            seen.add((p.key, d, label))
            tag = "NOT PAIRED" if must else "pair not possible"
            issues.append(f"{tag}: {p.name} on {got} {DAY_NAMES[d]} - {label}.")
    for p in people:
        row = grid[p.key]
        n = sum(1 for c in row if is_night(c))
        free = [d for d in D if d not in p.fixed]
        if p.nights_ok and not p.is_unit and len(free) >= 4 and n < p.min_nights and not p.only:
            issues.append(f"{p.name}: only {n} night(s) (min {p.min_nights}).")
        for d, c in enumerate(row):
            pool = code_pool(c)
            if pool and pool != p.pool and c not in open_codes and not p.is_unit:
                issues.append(f"borrowed: {p.name} ({p.pool}) covers {c} on {DAY_NAMES[d]}.")
            if p.off_allowed is not None and c.startswith("OFF") and d not in p.off_allowed:
                issues.append(f"{p.name}: off on {DAY_NAMES[d]} (HPB team offs are normally "
                              f"{', '.join(DAY_NAMES[i] for i in sorted(p.off_allowed))}).")
        for i in range(2, 7):
            if is_night(row[i]) and is_night(row[i - 2]):
                issues.append(f"{p.name}: night again right after PN on {DAY_NAMES[i]}.")
        if p.owed and owed_given[p.key] < p.owed:
            issues.append(f"{p.name}: owed off not given this week (still owes {p.owed - owed_given[p.key]}).")
        for d, kind, c in p.prefer:
            if d in p.fixed:
                continue
            got = row[d]
            ok = ((kind == "OFF" and got.startswith("OFF")) or (kind == "NO NIGHT" and not is_night(got))
                  or (kind == "WANT NIGHT" and is_night(got)) or (kind == "CODE" and got == c)
                  or (kind == "DAY SHIFT" and got != "PN" and not got.startswith("OFF") and not is_night(got)))
            if not ok:
                issues.append(f"prefer not met: {p.name} {kind.lower()} {c or ''} on {DAY_NAMES[d]} (got {got}).")
    return Result(grid=grid, sunday_night=sunday, owed_given=owed_given, issues=issues,
                  status=sname, counts=counts)
