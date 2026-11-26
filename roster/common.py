"""Shared names, shift codes and small helpers."""
import re
from datetime import date, datetime, timedelta

DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

# Section label in the timetable -> pool key used everywhere else
SECTION_TO_POOL = {"ETD/EMOT": "ETD", "ETD": "ETD", "MSW": "MSW", "FSW": "FSW"}
POOL_TO_SECTION = {"ETD": "ETD/EMOT", "MSW": "MSW", "FSW": "FSW"}
POOLS = ["ETD", "MSW", "FSW"]

OFF = "OFF"
OFF_OWE = "OFF (owe)"
PN = "PN"
SPECIAL_CODES = {"SCOPE/CLINIC", "CLINIC", "SCOPE", "MINOR OT", "HPB"}
LEAVE_CODES = {"AL", "MC", "EL", "PH"}
# Codes written by hand that mean the same as a STAFFING code (used when counting)
ALIASES = {"CLINIC": "SCOPE/CLINIC", "SCOPE": "SCOPE/CLINIC"}


def with_tags(codes):
    """A ward's SD + LD total also counts its tagging HOs (MSW TAG / FSW TAG count as LD)."""
    return list(codes) + [f"{w} TAG" for w in ("MSW", "FSW")
                          if {f"{w} SD", f"{w} LD"} <= set(codes) and f"{w} TAG" not in codes]


def norm_code(v):
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return ""
    return re.sub(r"\s+", " ", str(v)).strip().upper()


def name_key(v):
    """Normalise a doctor's name so 'Dr Aisyah  Rahman ' == 'AISYAH RAHMAN'."""
    s = re.sub(r"\s+", " ", str(v or "")).strip().upper()
    s = re.sub(r"^DR\.?\s+", "", s)
    return s


def code_pool(code):
    """Which pool a shift code belongs to, or None for specials/leave."""
    c = norm_code(code)
    if c.startswith("ETD") or c.startswith("EMOT"):
        return "ETD"
    if c.startswith("MSW"):
        return "MSW"
    if c.startswith("FSW"):
        return "FSW"
    return None


def is_off(code):
    return norm_code(code) in ("OFF", "OFF (OWE)")


def parse_days(text):
    """'Mon-Sun', 'Mon-Wed', 'Thu', 'Mon, Wed' -> set of day indexes 0..6."""
    s = str(text or "Mon-Sun").upper().replace("THURS", "THU").replace("TUES", "TUE")
    s = re.sub(r"\s*-\s*", "-", s)
    out = set()
    for part in re.split(r"[,;/ ]+", s):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = [p.strip()[:3] for p in part.split("-", 1)]
            if a in DAY_NAMES and b in DAY_NAMES:
                i, j = DAY_NAMES.index(a), DAY_NAMES.index(b)
                k = i
                while True:
                    out.add(k)
                    if k == j:
                        break
                    k = (k + 1) % 7
        elif part[:3] in DAY_NAMES:
            out.add(DAY_NAMES.index(part[:3]))
    return out or set(range(7))


def to_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m"):
        try:
            d = datetime.strptime(s, fmt).date()
            if fmt == "%d/%m":
                d = d.replace(year=date.today().year)
            return d
        except ValueError:
            pass
    return None


def sheet_title(start):
    """23/11/26 -> '2311-291126', matching the existing tab names."""
    end = start + timedelta(days=6)
    first = f"{start.day}{start.month}" + (start.strftime("%y") if start.year != end.year else "")
    return f"{first}-{end.day}{end.month}{end.strftime('%y')}"


def owed_from_note(note):
    s = str(note or "").lower()
    if "owe" not in s:
        return 0
    m = re.search(r"owe\s*(\d+)", s)
    return int(m.group(1)) if m else 1


def yes(v, default=True):
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip().upper() in ("YES", "Y", "TRUE", "1")
