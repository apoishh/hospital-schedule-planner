"""The 'Roster Data.xlsx' workbook: doctors, requests, pairs, staffing and rules.

This is the small "database" the roster maker edits. The big timetable
workbook stays the official record; this file only says who is working, what
they asked for and how the week should be built.

Columns are found by their header text, so they can be re-ordered and older
files (with fewer columns) still work.
"""
from dataclasses import dataclass, field

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .common import SECTION_TO_POOL, name_key, norm_code, parse_days, to_date, yes

# Names that start as "Nights allowed = NO" when a brand-new Roster Data is made.
# Kept empty in the code (no personal names in the repo) - set it in DOCTORS instead.
NO_NIGHT_DEFAULT = set()
# Name colours in the timetable legend that mean "1st posting"
JUNIOR_COLOURS = {"FFF4CCCC", "FFFCE5CD", "FFF9CB9C", "FF674EA7"}

SUBSPEC_UNITS = ["HPB", "VAS", "PLASTIC", "PERI", "PJHUS", "NEURO", "PAEDS", "UGI"]

DOCTOR_COLS = ["Name", "Pool", "Nights allowed", "Min nights", "Max nights", "Off days per week",
               "Junior (1st posting)", "EMOT AM trained", "Start date", "Last day (EOP)", "Active", "Notes"]
REQUEST_COLS = ["Name", "From", "To", "Type", "Show as", "Must or Prefer", "Notes"]
REQUEST_TYPES = ["AL", "MC", "EL", "PH", "COURSE", "OFF", "NO NIGHT", "WANT NIGHT", "DAY SHIFT",
                 "FIXED SHIFT", "ONLY SHIFT", "OFF COUNT"]
PAIR_COLS = ["Person", "Together with (names, comma - blank = any senior)",
             "On these shifts (blank = any night)", "Must or Prefer", "Notes"]
STAFF_COLS = ["Shift (use + to add shifts together)", "Days", "Min", "Target", "Max", "Notes"]

DEFAULT_STAFFING = [
    ("ETD AM", "Mon-Sun", 2, 3, 3, "ETD morning"),
    ("EMOT AM", "Mon-Sun", 1, 1, 2, "Emergency OT morning - only HOs with EMOT AM trained = YES"),
    ("EMOT AM TAG", "Mon-Sun", 0, 0, 1, "HO learning EMOT AM, always with an EMOT AM the same day"),
    ("ETD ON", "Mon-Sun", 2, 2, 3, "ETD night"),
    ("EMOT PM", "Mon-Sun", 1, 1, 1, "EMOT night (followed by PN)"),
    ("MSW SD + MSW LD", "Mon-Sun", 5, 6, 12, "MSW day doctors in total"),
    ("MSW LD", "Mon-Sun", 1, 1, 6, "how many of them do long day"),
    ("MSW ON", "Mon-Sun", 2, 2, 2, "MSW night"),
    ("FSW SD + FSW LD", "Mon-Sun", 4, 5, 12, "FSW day doctors in total"),
    ("FSW LD", "Mon-Sun", 1, 1, 6, "how many of them do long day"),
    ("FSW ON", "Mon-Sun", 2, 2, 2, "FSW night"),
    ("SCOPE/CLINIC", "Mon-Wed", 1, 2, 2, "from any pool"),
    ("MINOR OT", "Thu", 1, 1, 1, "from any pool"),
    ("HPB", "Mon-Sun", 4, 4, 4, "HPB team + a pool HO covering when an HPB HO is off"),
]

DEFAULT_RULES = [
    ("Night shift codes", "ETD ON, EMOT PM, MSW ON, FSW ON",
     "Shifts that count as a night. The day after each one is PN."),
    ("Default min nights per week", 1, "Used when a doctor's Min nights is blank."),
    ("Default max nights per week", 2, "Used when a doctor's Max nights is blank."),
    ("Default off days per week", 1, "Used when a doctor's Off days per week is blank."),
    ("Shifts any pool can do", "EMOT AM, EMOT AM TAG, SCOPE/CLINIC, MINOR OT, HPB",
     "These can be given to ETD, MSW or FSW HOs freely (never to subspecialty HOs)."),
    ("Borrow doctors from other pools when short", "YES",
     "YES = e.g. an FSW HO may cover ETD ON if ETD is short. Never subspecialty HOs."),
    ("Juniors on night need a senior", "YES",
     "A Junior (1st posting) on night must have a senior on night in the same group (see next rule)."),
    ("Night groups for junior/senior", "ETD ON + EMOT PM; MSW ON; FSW ON",
     "Groups separated by ';'. A junior on any shift in a group needs a senior on a shift in the same group."),
    ("Give EMOT AM TAG to untrained HOs", "YES",
     "Tries to give each HO with EMOT AM trained = NO one EMOT AM TAG a week."),
    ("Subspecialty units", ", ".join(SUBSPEC_UNITS), "Pool values that mean a subspecialty posting."),
    ("Subspecialty preferred off days", "Sat, Sun", "Subspecialty HOs get their off day on these days if possible."),
    ("HPB team off days", "Thu-Sun", "HPB subspecialty HOs take their off day on these days; a pool HO covers HPB that day."),
    ("Avoid night right after post-night (ON, PN, ON)", "YES", "Tries hard not to, but allows it if there is no other way."),
    ("Make each week different from last week", "YES", "Avoids the same night day / off day as last week."),
    ("HPB: same pool doctor for all HPB days", "YES", "Prefer one pool HO for the HPB cover days of the week."),
    ("Give owed offs", "YES", "Reads '*owe 1 off' notes in column K and tries to give the extra off."),
    ("Pool rotation", "SUGGEST",
     "NO = never. SUGGEST = list who is due to move and where. YES = move them automatically (Pool in DOCTORS is updated)."),
    ("Weeks in a pool before rotating", 4, "An HO becomes due to move after this many weeks in a row in the same pool."),
    ("Minimum weeks in a pool", 2, "Never move an HO who has been in their pool fewer weeks than this."),
    ("Weeks of history for fairness", 6, "Spreads weekend nights, clinics, HPB and LD fairly over this many past weeks."),
    ("Max seconds to search", 30, "Longer = slightly better schedule."),
    ("Viewer: weeks to show", 6, "How many of the newest week tabs the viewer website shows."),
    ("Viewer: show MC/EL as LEAVE", "YES", "YES = the website says LEAVE instead of MC or EL (privacy). AL/PH still shown."),
]

HEAD_FILL = PatternFill("solid", fgColor="FF1F4E78")
HEAD_FONT = Font(b=True, color="FFFFFFFF")
EXAMPLE_FONT = Font(i=True, color="FF7F7F7F")


@dataclass
class Doctor:
    name: str
    pool: str
    nights_ok: bool = True
    min_nights: int = None
    max_nights: int = None
    off_days: int = None
    junior: bool = False
    emot_trained: bool = True
    start: object = None
    end: object = None
    active: bool = True
    notes: str = ""
    row: int = 0

    @property
    def key(self):
        return name_key(self.name)


@dataclass
class Request:
    row: int
    name: str
    start: object
    end: object
    type: str
    show_as: str
    must: bool
    notes: str = ""


@dataclass
class Pair:
    row: int
    person: str
    partners: list          # names; empty = any senior
    shifts: list            # codes; empty = any night
    must: bool
    notes: str = ""


@dataclass
class StaffRule:
    codes: list
    days: set
    min: int
    target: int
    max: int
    label: str


@dataclass
class RosterData:
    doctors: list
    requests: list
    staffing: list
    rules: dict
    pairs: list = field(default_factory=list)
    path: str = ""
    problems: list = field(default_factory=list)

    def rule(self, key, default=None):
        for k, v in self.rules.items():
            if k.lower().startswith(key.lower()):
                return v if v not in (None, "") else default
        return default

    def rule_list(self, key, default, sep=","):
        return [norm_code(c) for c in str(self.rule(key, default)).split(sep) if c.strip()]

    @property
    def night_codes(self):
        return set(self.rule_list("Night shift codes", "ETD ON, EMOT PM, MSW ON, FSW ON"))

    @property
    def units(self):
        return set(self.rule_list("Subspecialty units", ", ".join(SUBSPEC_UNITS)))

    @property
    def open_codes(self):
        return set(self.rule_list("Shifts any pool can do", "EMOT AM, EMOT AM TAG, SCOPE/CLINIC, MINOR OT, HPB"))

    @property
    def night_groups(self):
        txt = self.rule("Night groups", "ETD ON + EMOT PM; MSW ON; FSW ON")
        groups = []
        for g in str(txt).split(";"):
            codes = [norm_code(c) for c in g.split("+") if c.strip()]
            if codes:
                groups.append(codes)
        return groups


# --------------------------------------------------------------------------- creating


def _style_header(ws, ncols, widths):
    for c in range(1, ncols + 1):
        cell = ws.cell(1, c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"


def _dropdown(ws, col, options, last_row=1000):
    dv = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col}2:{col}{last_row}")


HOW_TO = [
    ("ROSTER DATA - the file you edit. Then run the HO Roster app.", "title"),
    ("", None),
    ("TAB          WHAT IT IS FOR                                   WHEN TO EDIT", "head"),
    ("DOCTORS      every HO: pool, nights yes/no, junior, EMOT AM    when someone joins, leaves, changes pool", None),
    ("REQUESTS     leave and requests with dates                     every week, before making the week", None),
    ("PAIRS        who must / should work together                   when needed", None),
    ("STAFFING     how many HOs each shift needs per day             rarely", None),
    ("RULES        general rules (change the Value column only)      rarely", None),
    ("", None),
    ("EXAMPLES - DOCTORS", "head"),
    ("  New HO joining MSW on 30/11:     Name = FARAH NADIA BINTI OMAR, Pool = MSW, Start date = 30/11/2026", None),
    ("  HO leaving on 16/12:             Last day (EOP) = 16/12/2026   (or Active = NO to remove now)", None),
    ("  Moving to MSW next week:         change Pool to MSW", None),
    ("  Going to HPB subspecialty:       Pool = HPB", None),
    ("  Cannot do nights:                Nights allowed = NO", None),
    ("  Wants exactly 3 nights a week:   Min nights = 3, Max nights = 3", None),
    ("  1st posting HO:                  Junior (1st posting) = YES  -> always has a senior on the same night", None),
    ("  Has not done EMOT AM yet:        EMOT AM trained = NO        -> gets EMOT AM TAG next to an EMOT AM", None),
    ("", None),
    ("EXAMPLES - REQUESTS  (Name can be any unique part of the name, e.g. AISYAH)", "head"),
    ("  Annual leave 2-6 Dec:            AISYAH | 02/12/2026 | 06/12/2026 | AL", None),
    ("  Public holiday replacement:      DANIEL | 25/12/2026 |           | PH", None),
    ("  Course:                          PRIYA | 05/12/2026 |            | COURSE | Show as = Stroke course", None),
    ("  Wants a night:                   NADIA HUDA | 30/11/2026 |       | WANT NIGHT | MUST", None),
    ("  Day off:                         MICHAEL | 05/12/2026 |          | OFF | MUST", None),
    ("  Would like no night:             SITI AMINAH | 04/12/2026 | 06/12/2026 | NO NIGHT | PREFER", None),
    ("  Must work a day shift (AM/SD):   JASON | 01/12/2026 |            | DAY SHIFT", None),
    ("  A specific shift:                MICHAEL | 03/12/2026 |          | FIXED SHIFT | Show as = MINOR OT", None),
    ("  Only certain shifts for a while: FARAH | 30/11/2026 | 13/12/2026 | ONLY SHIFT | Show as = MSW LD", None),
    ("  No off day that week:            NADIA HUDA | 07/12/2026 | 13/12/2026 | OFF COUNT | Show as = 0", None),
    ("  MUST = always done unless impossible (then listed in red). PREFER = done if it fits.", None),
    ("  PN after a night is automatic - no need to write PN. Old rows can stay.", None),
    ("", None),
    ("EXAMPLES - PAIRS", "head"),
    ("  Junior always with a named senior on night:  DANIEL | AISYAH, MICHAEL | ETD ON, EMOT PM | MUST", None),
    ("  Two friends want nights together:            NADIA HUDA | JASON | MSW ON | PREFER", None),
    ("  (Juniors already always get a senior on night - PAIRS is only for extra, specific pairings.)", None),
]


def create_data_workbook(path, latest_week):
    """Make a fresh Roster Data.xlsx from the newest week sheet."""
    wb = openpyxl.Workbook()
    how = wb.active
    how.title = "HOW TO USE"
    for i, (t, kind) in enumerate(HOW_TO, 1):
        c = how.cell(i, 1)
        c.value = t
        c.font = Font(name="Consolas", b=kind in ("title", "head"), sz=14 if kind == "title" else 10)
    how.column_dimensions["A"].width = 130

    ws = wb.create_sheet("DOCTORS")
    ws.append(DOCTOR_COLS)
    src = latest_week.ws if latest_week else None
    for sec in (latest_week.sections if latest_week else []):
        pool = SECTION_TO_POOL.get(sec.label.upper())
        for d in sec.doctors:
            unit = d.label.upper().strip()
            p = pool or (unit if unit in SUBSPEC_UNITS else None)
            if not p:
                continue
            f = src.cell(d.row, 2).fill
            colour = f.fgColor.rgb if f is not None and f.fill_type == "solid" and f.fgColor.type == "rgb" else None
            no_night = d.key in NO_NIGHT_DEFAULT or not pool
            ws.append([d.name.strip(), p, "NO" if no_night else "YES",
                       0 if no_night else None, 0 if no_night else None, None,
                       "YES" if colour in JUNIOR_COLOURS else "NO", "YES", None, None, "YES", None])
    _style_header(ws, len(DOCTOR_COLS), [42, 9, 9, 8, 8, 9, 11, 10, 12, 12, 8, 40])
    for col in "IJ":
        for r in range(2, 501):
            ws[f"{col}{r}"].number_format = "dd/mm/yyyy"
    _dropdown(ws, "B", "ETD,MSW,FSW," + ",".join(SUBSPEC_UNITS), 500)
    for col in "CGHK":
        _dropdown(ws, col, "YES,NO", 500)

    rq = wb.create_sheet("REQUESTS")
    rq.append(REQUEST_COLS)
    _style_header(rq, len(REQUEST_COLS), [36, 12, 12, 13, 22, 10, 50])
    _dropdown(rq, "D", ",".join(REQUEST_TYPES))
    _dropdown(rq, "F", "MUST,PREFER")
    for col in "BC":
        for r in range(2, 1001):
            rq[f"{col}{r}"].number_format = "dd/mm/yyyy"

    pr = wb.create_sheet("PAIRS")
    pr.append(PAIR_COLS)
    _style_header(pr, len(PAIR_COLS), [36, 44, 34, 10, 50])
    _dropdown(pr, "D", "MUST,PREFER", 300)

    st = wb.create_sheet("STAFFING")
    st.append(STAFF_COLS)
    for row in DEFAULT_STAFFING:
        st.append(list(row))
    _style_header(st, len(STAFF_COLS), [34, 12, 7, 8, 7, 60])

    ru = wb.create_sheet("RULES")
    ru.append(["Rule", "Value", "What it means"])
    for row in DEFAULT_RULES:
        ru.append(list(row))
    _style_header(ru, 3, [48, 40, 100])

    wb.active = 1
    wb.save(path)
    return path


# --------------------------------------------------------------------------- reading


def _int(v, default=None):
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _columns(ws, wanted):
    """wanted: {field: [header prefixes]} -> {field: column index}"""
    heads = {c: str(ws.cell(1, c).value or "").strip().lower() for c in range(1, ws.max_column + 1)}
    out = {}
    for fld, prefixes in wanted.items():
        for c, h in heads.items():
            if any(h.startswith(p) for p in prefixes):
                out[fld] = c
                break
    return out


def _rows(ws, cols):
    for r in range(2, ws.max_row + 1):
        yield r, {f: ws.cell(r, c).value for f, c in cols.items()}


def read_data_workbook(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    problems = []

    doctors = []
    ws = wb["DOCTORS"]
    cols = _columns(ws, {
        "name": ["name"], "pool": ["pool"], "nights": ["nights allowed"], "min": ["min night"],
        "max": ["max night"], "off": ["off day"], "junior": ["junior"], "emot": ["emot am"],
        "start": ["start"], "end": ["last day", "eop", "end"], "active": ["active"], "notes": ["note"],
    })
    for r, v in _rows(ws, cols):
        if not v.get("name") or not str(v["name"]).strip():
            continue
        pool = norm_code(v.get("pool")) or "?"
        if pool == "ETD/EMOT":
            pool = "ETD"
        doctors.append(Doctor(
            name=str(v["name"]).strip(), pool=pool,
            nights_ok=yes(v.get("nights"), True),
            min_nights=_int(v.get("min")), max_nights=_int(v.get("max")), off_days=_int(v.get("off")),
            junior=yes(v.get("junior"), False), emot_trained=yes(v.get("emot"), True),
            start=to_date(v.get("start")), end=to_date(v.get("end")),
            active=yes(v.get("active"), True), notes=str(v.get("notes") or ""), row=r,
        ))

    requests = []
    ws = wb["REQUESTS"]
    cols = _columns(ws, {"name": ["name"], "from": ["from"], "to": ["to"], "type": ["type"],
                         "show": ["show"], "must": ["must"], "notes": ["note"]})
    for r, v in _rows(ws, cols):
        if not v.get("name") or not str(v["name"]).strip():
            continue
        start = to_date(v.get("from"))
        end = to_date(v.get("to")) or start
        typ = norm_code(v.get("type"))
        if not start or not typ:
            problems.append(f"REQUESTS row {r}: needs at least Name, From and Type - skipped.")
            continue
        if typ not in REQUEST_TYPES:
            problems.append(f"REQUESTS row {r}: unknown Type '{v.get('type')}' - skipped.")
            continue
        must = norm_code(v.get("must")) != "PREFER" or typ in ("AL", "MC", "EL", "PH", "COURSE", "ONLY SHIFT", "OFF COUNT")
        requests.append(Request(row=r, name=str(v["name"]).strip(), start=start, end=end, type=typ,
                                show_as=str(v.get("show") or "").strip(), must=must, notes=str(v.get("notes") or "")))

    pairs = []
    if "PAIRS" in wb.sheetnames:
        ws = wb["PAIRS"]
        cols = _columns(ws, {"person": ["person"], "with": ["together", "with", "partner"],
                             "shifts": ["on these", "shift"], "must": ["must"], "notes": ["note"]})
        for r, v in _rows(ws, cols):
            if not v.get("person") or not str(v["person"]).strip():
                continue
            pairs.append(Pair(
                row=r, person=str(v["person"]).strip(),
                partners=[p.strip() for p in str(v.get("with") or "").split(",") if p.strip()],
                shifts=[norm_code(s) for s in str(v.get("shifts") or "").split(",") if s.strip()],
                must=norm_code(v.get("must")) != "PREFER", notes=str(v.get("notes") or "")))

    staffing = []
    ws = wb["STAFFING"]
    for r in range(2, ws.max_row + 1):
        vals = [ws.cell(r, c).value for c in range(1, 6)]
        if not vals[0]:
            continue
        codes = [norm_code(c) for c in str(vals[0]).split("+") if c.strip()]
        mn = _int(vals[2], 0)
        tg = _int(vals[3], mn)
        mx = _int(vals[4], max(mn, tg))
        staffing.append(StaffRule(codes=codes, days=parse_days(vals[1]), min=mn,
                                  target=max(tg, mn), max=max(mx, tg, mn), label=" + ".join(codes)))

    rules = {}
    ws = wb["RULES"]
    for r in range(2, ws.max_row + 1):
        k = ws.cell(r, 1).value
        if k:
            rules[str(k).strip()] = ws.cell(r, 2).value

    return RosterData(doctors=doctors, requests=requests, staffing=staffing, rules=rules, pairs=pairs,
                      path=path, problems=problems)


# --------------------------------------------------------------------------- writing back


def add_doctors(path, rows):
    """Append [(name, pool)] to DOCTORS. Returns False if the file is locked."""
    wb = openpyxl.load_workbook(path)
    ws = wb["DOCTORS"]
    cols = _columns(ws, {"name": ["name"], "pool": ["pool"], "nights": ["nights allowed"],
                        "active": ["active"], "notes": ["note"], "emot": ["emot am"], "junior": ["junior"]})
    r = ws.max_row + 1
    while r > 2 and not ws.cell(r - 1, cols.get("name", 1)).value:
        r -= 1
    for name, pool in rows:
        ws.cell(r, cols.get("name", 1)).value = name
        ws.cell(r, cols.get("pool", 2)).value = pool
        if "nights" in cols:
            ws.cell(r, cols["nights"]).value = "YES" if pool in ("ETD", "MSW", "FSW") else "NO"
        if "active" in cols:
            ws.cell(r, cols["active"]).value = "YES"
        if "notes" in cols:
            ws.cell(r, cols["notes"]).value = "added automatically from timetable - check Junior / EMOT AM"
        r += 1
    try:
        wb.save(path)
        return True
    except PermissionError:
        return False


def set_pools(path, moves):
    """moves: {doctor key: new pool}. Updates Pool in DOCTORS. False if locked."""
    wb = openpyxl.load_workbook(path)
    ws = wb["DOCTORS"]
    cols = _columns(ws, {"name": ["name"], "pool": ["pool"]})
    for r in range(2, ws.max_row + 1):
        k = name_key(ws.cell(r, cols["name"]).value)
        if k in moves:
            ws.cell(r, cols["pool"]).value = moves[k]
    try:
        wb.save(path)
        return True
    except PermissionError:
        return False
