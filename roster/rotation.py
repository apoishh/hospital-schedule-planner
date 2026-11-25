"""Pool rotation: who is due to change pool, and where they should go.

An HO is "due" after N weeks in a row in the same pool (RULES: Weeks in a pool
before rotating). Due HOs swap places so every pool keeps the same number of
HOs, and each due HO goes preferably to a pool they have never been to
(counters in columns M-W of the timetable), else the one they've had least.
"""
from ortools.sat.python import cp_model

POOLS = ("ETD", "MSW", "FSW")


def consecutive_weeks(key, weeks, pool_of_section):
    """How many weeks in a row (newest first) the HO was in the same pool."""
    n, cur = 0, None
    for w in weeks:
        sec, row = w.find(key)
        if not row:
            break
        pool = pool_of_section(sec, row)
        if cur is None:
            cur = pool
        if pool != cur:
            break
        n += 1
    return cur, n


def plan(cands):
    """cands: [(key, current_pool, {pool: weeks_ever})] -> {key: new_pool}"""
    if len(cands) < 2:
        return {}
    m = cp_model.CpModel()
    y = {}
    for i, (k, cur, wk) in enumerate(cands):
        for p in POOLS:
            y[i, p] = m.NewBoolVar("")
        m.AddExactlyOne(y[i, p] for p in POOLS)
    for p in POOLS:
        m.Add(sum(y[i, p] for i in range(len(cands))) == sum(1 for _, cur, _ in cands if cur == p))
    cost = []
    for i, (k, cur, wk) in enumerate(cands):
        for p in POOLS:
            if p == cur:
                cost.append(1000 * y[i, p])
            else:
                w = int(wk.get(p, 0) or 0)
                cost.append((10 * w - (300 if w == 0 else 0)) * y[i, p])
    m.Minimize(sum(cost))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = 5
    if s.Solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {}
    out = {}
    for i, (k, cur, wk) in enumerate(cands):
        for p in POOLS:
            if s.Value(y[i, p]) and p != cur:
                out[k] = p
    return out
