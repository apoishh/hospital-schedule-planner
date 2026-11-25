"""Read week sheets from the timetable workbook and write a new week sheet.

A week sheet looks like:
    row 1          MON .. SUN headers
    header row     A='ETD/EMOT' (merged A:B), C..I = dates, M..W = counter headers
    doctor rows    A=section label, B=name, C..I = Mon..Sun codes, J = PN carried
                   into next week, K = note (e.g. '*owe 1 off'), L..W = counters
    TOTAL rows     B starts with 'TOTAL'
    ... repeated for MSW, FSW, SUBSPEC, EOP, then a colour legend.
"""
from copy import copy
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .common import norm_code, name_key, owed_from_note

FIRST_DAY_COL = 3      # C
CARRY_COL = 10         # J
NOTE_COL = 11          # K
LAST_COL = 23          # W
COUNTER_COLS = list(range(13, 24))   # M..W: weeks spent in MSW, FSW, EMOT/ETD, HPB, ...
HIGHLIGHT = "FFEA9999"               # pink fill marking the current ward in M..W


@dataclass
class DoctorRow:
    row: int
    label: str
    name: str
    codes: list          # 7 normalised codes (Mon..Sun)
    raw: list            # 7 raw cell values
    carry: str           # column J
    note: str            # column K

    @property
    def key(self):
        return name_key(self.name)

    @property
    def owed(self):
        return owed_from_note(self.note)


@dataclass
class Section:
    label: str
    header_row: int
    doctors: list = field(default_factory=list)
    total_rows: list = field(default_factory=list)   # (row, label)
    last_row: int = 0


@dataclass
class Week:
    ws: object
    start: date
    sections: list
    legend_start: int

    def section(self, label):
        for s in self.sections:
            if s.label.upper() == label.upper():
                return s
        return None

    def all_doctors(self):
        for s in self.sections:
            for d in s.doctors:
                yield s, d

    def find(self, key):
        for s, d in self.all_doctors():
            if d.key == key:
                return s, d
        return None, None


def _as_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def parse_week(ws):
    """Return a Week, or None if the sheet doesn't look like a week sheet."""
    sections = []
    cur = None
    max_row = min(ws.max_row, 400)
    last_content = 0
    for r in range(1, max_row + 1):
        a = ws.cell(r, 1).value
        b = ws.cell(r, 2).value
        c = ws.cell(r, 3).value
        if a and not b and _as_date(c):
            cur = Section(label=str(a).strip(), header_row=r, last_row=r)
            sections.append(cur)
            last_content = r
            continue
        if cur is None:
            continue
        if isinstance(b, str) and b.strip():
            if b.strip().upper().startswith("TOTAL"):
                cur.total_rows.append((r, b))
            else:
                raw = [ws.cell(r, FIRST_DAY_COL + i).value for i in range(7)]
                cur.doctors.append(DoctorRow(
                    row=r,
                    label=str(a or cur.label).strip(),
                    name=b,
                    codes=[norm_code(v) for v in raw],
                    raw=raw,
                    carry=norm_code(ws.cell(r, CARRY_COL).value),
                    note=str(ws.cell(r, NOTE_COL).value or "").strip(),
                ))
            cur.last_row = r
            last_content = r
    if not sections or not any(s.doctors for s in sections):
        return None
    start = _as_date(ws.cell(sections[0].header_row, FIRST_DAY_COL).value)
    if start is None:
        return None
    # legend = first non-empty row after the last section
    legend_start = None
    for r in range(last_content + 1, ws.max_row + 1):
        if any(ws.cell(r, c).value not in (None, "") for c in range(1, LAST_COL + 1)):
            legend_start = r
            break
    return Week(ws=ws, start=start, sections=sections, legend_start=legend_start)


def load_weeks(wb, limit=15):
    """Parse the newest `limit` week sheets, newest first."""
    weeks = []
    for ws in wb.worksheets[: limit * 2]:
        try:
            w = parse_week(ws)
        except Exception:
            w = None
        if w:
            weeks.append(w)
    weeks.sort(key=lambda w: w.start, reverse=True)
    # one sheet per start date (ignore "Copy of ..." duplicates)
    seen, out = set(), []
    for w in weeks:
        if w.start not in seen:
            seen.add(w.start)
            out.append(w)
    return out[:limit]


# --------------------------------------------------------------------------
# Styles


def build_style_map(weeks):
    """code -> a cell that already shows that code (so we can copy its look)."""
    m = {}
    for w in weeks:
        for s, d in w.all_doctors():
            for i, code in enumerate(d.codes):
                if code and code not in m:
                    m[code] = w.ws.cell(d.row, FIRST_DAY_COL + i)
            if d.carry and d.carry not in m:
                m[d.carry] = w.ws.cell(d.row, CARRY_COL)
    return m


def _copy_cell(src, dst, value=True):
    if value:
        dst.value = src.value
    if src.has_style:
        dst._style = copy(src._style)


# --------------------------------------------------------------------------
# Writing


@dataclass
class OutRow:
    label: str
    name: str
    codes: list               # 7 display values
    carry: str = ""
    note: str = ""
    src: tuple = None         # (ws, row) to copy A/B/L..W styles + counters from
    new: bool = False
    counters: list = None     # values for M..W (None = copy from src)
    highlight: int = None     # index into COUNTER_COLS of the current ward


@dataclass
class OutSection:
    label: str
    src_header: tuple         # (ws, row)
    rows: list
    totals: list = field(default_factory=list)  # (src(ws,row) or None, label, [7 str], [7 bool short])


def write_week(wb, base, title, start, out_sections, style_map, red_cells=()):
    """Create sheet `title` as the first tab. Returns the worksheet."""
    if title in wb.sheetnames:
        del wb[title]
    ws = wb.create_sheet(title, 0)
    src = base.ws

    # sheet-level look
    for k, dim in src.column_dimensions.items():
        ws.column_dimensions[k].width = dim.width
        ws.column_dimensions[k].hidden = dim.hidden
    if src.sheet_properties.tabColor is not None:
        ws.sheet_properties.tabColor = copy(src.sheet_properties.tabColor)
    ws.sheet_format = copy(src.sheet_format)

    for c in range(1, LAST_COL + 1):
        _copy_cell(src.cell(1, c), ws.cell(1, c))

    any_day_cell, any_row = None, None
    for s in base.sections:
        if s.doctors:
            any_day_cell = src.cell(s.doctors[0].row, FIRST_DAY_COL)
            any_row = (src, s.doctors[0].row)
            break

    def day_style(cell, code):
        tpl = style_map.get(norm_code(code))
        if tpl is not None:
            cell._style = copy(tpl._style)
        elif any_day_cell is not None:
            cell._style = copy(any_day_cell._style)
            cell.fill = PatternFill(fill_type=None)
            cell.font = Font(name=any_day_cell.font.name, sz=any_day_cell.font.sz, b=True)

    red = PatternFill("solid", fgColor="FFFF7F7F")
    red_set = set(red_cells)
    r = 2
    for sec in out_sections:
        hws, hrow = sec.src_header
        for c in range(1, LAST_COL + 1):
            _copy_cell(hws.cell(hrow, c), ws.cell(r, c))
        for i in range(7):
            ws.cell(r, FIRST_DAY_COL + i).value = datetime.combine(start + timedelta(days=i), datetime.min.time())
        ws.cell(r, 1).value = sec.label
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        r += 1
        tpl = next((x.src for x in sec.rows if x.src), None) or any_row
        for row in sec.rows:
            if row.src:
                sws, srow = row.src
                for c in (1, 2) + tuple(range(12, LAST_COL + 1)):
                    _copy_cell(sws.cell(srow, c), ws.cell(r, c))
                _copy_cell(sws.cell(srow, NOTE_COL), ws.cell(r, NOTE_COL), value=False)
            elif tpl:
                sws, srow = tpl
                for c in (1, 2) + tuple(COUNTER_COLS):
                    _copy_cell(sws.cell(srow, c), ws.cell(r, c), value=False)
                ws.cell(r, 2).fill = PatternFill(fill_type=None)
            if row.counters is not None:
                for i, c in enumerate(COUNTER_COLS):
                    cell = ws.cell(r, c)
                    cell.value = row.counters[i] if i < len(row.counters) else None
                    f = cell.fill
                    if f is not None and f.fill_type == "solid" and f.fgColor.type == "rgb" and f.fgColor.rgb == HIGHLIGHT:
                        cell.fill = PatternFill(fill_type=None)
                if row.highlight is not None:
                    ws.cell(r, COUNTER_COLS[row.highlight]).fill = PatternFill("solid", fgColor=HIGHLIGHT)
            ws.cell(r, 1).value = row.label
            ws.cell(r, 2).value = row.name
            for i, code in enumerate(row.codes):
                cell = ws.cell(r, FIRST_DAY_COL + i)
                cell.value = code if code else None
                if code:
                    day_style(cell, code)
                if (sec.label, row.name, i) in red_set:
                    cell.fill = red
            cj = ws.cell(r, CARRY_COL)
            cj.value = row.carry or None
            if row.carry:
                day_style(cj, row.carry)
            ws.cell(r, NOTE_COL).value = row.note or None
            r += 1
        for tsrc, tlabel, vals, short in sec.totals:
            if tsrc:
                tws, trow = tsrc
                for c in range(1, 10):
                    _copy_cell(tws.cell(trow, c), ws.cell(r, c), value=False)
            ws.cell(r, 2).value = tlabel
            for i in range(7):
                cell = ws.cell(r, FIRST_DAY_COL + i)
                cell.value = vals[i]
                if short[i]:
                    cell.fill = red
            r += 1
        r += 1

    # colour legend
    if base.legend_start:
        r += 1
        offset = r - base.legend_start
        for sr in range(base.legend_start, src.max_row + 1):
            for c in range(1, LAST_COL + 1):
                s = src.cell(sr, c)
                if s.value is not None or s.has_style:
                    _copy_cell(s, ws.cell(sr + offset, c))
        for mr in src.merged_cells.ranges:
            if mr.min_row >= base.legend_start:
                ws.merge_cells(start_row=mr.min_row + offset, start_column=mr.min_col,
                               end_row=mr.max_row + offset, end_column=mr.max_col)

    # make the new tab the one that opens, and only that one selected
    for other in wb.worksheets:
        other.sheet_view.tabSelected = False
    ws.sheet_view.tabSelected = True
    wb.active = 0
    return ws
