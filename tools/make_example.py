"""Build examples/Roster Data EXAMPLE.xlsx - a filled-in Roster Data with MADE-UP names.

Shows exactly how each tab is filled in. Safe to share (no real people).

    python tools/make_example.py
"""
import os
import sys
from datetime import date

import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from roster import data as rdata  # noqa: E402

OUT = os.path.join(ROOT, "examples", "Roster Data EXAMPLE.xlsx")
NOTE_FILL = PatternFill("solid", fgColor="FFFFF4CE")


def D(d, m, y=2026):
    return date(y, m, d)


# Name, Pool, Nights allowed, Min, Max, Off, Junior, EMOT trained, Start, Last day, Active, Notes
DOCTORS = [
    ("AISYAH BINTI RAHMAN", "ETD", "YES", None, None, None, "NO", "YES", None, None, "YES", "normal senior: everything blank = defaults"),
    ("DANIEL TAN WEI MING", "ETD", "YES", None, None, None, "YES", "YES", None, None, "YES", "1st posting -> always with a senior on night"),
    ("PRIYA A/P KUMARAN", "ETD", "YES", None, None, None, "NO", "NO", None, None, "YES", "not EMOT AM trained yet -> gets EMOT AM TAG"),
    ("KEVIN ANAK PETER", "ETD", "NO", 0, 0, None, "NO", "YES", None, None, "YES", "cannot do nights"),
    ("NADIA HUDA BINTI KAMAL", "MSW", "YES", 3, 3, None, "NO", "YES", None, None, "YES", "asked for exactly 3 nights a week"),
    ("JASON LAU KAH HO", "MSW", "YES", None, None, None, "YES", "YES", None, D(16, 12), "YES", "end of posting 16/12 - not scheduled after"),
    ("FARAH NADIA BINTI OMAR", "MSW", "YES", None, None, None, "NO", "NO", D(30, 11), None, "YES", "new HO starting 30/11"),
    ("MICHAEL OOI JIA LE", "FSW", "YES", None, None, None, "NO", "YES", None, None, "YES", ""),
    ("SITI AMINAH BINTI YUSOF", "FSW", "YES", None, None, 2, "NO", "YES", None, None, "YES", "2 off days a week"),
    ("RAJESH A/L MURUGAN", "FSW", "YES", None, None, None, "YES", "YES", None, None, "NO", "Active = NO -> left, not shown"),
    ("HANNAH LEE SHU YI", "HPB", "NO", 0, 0, None, "NO", "YES", None, None, "YES", "subspecialty: HPB only, off on Thu-Sun"),
    ("AHMAD FAIZ BIN HASSAN", "VAS", "NO", 0, 0, None, "NO", "YES", None, None, "YES", "subspecialty: VAS only, off at weekend"),
]

# Name, From, To, Type, Show as, Must/Prefer, Notes
REQUESTS = [
    ("AISYAH", D(2, 12), D(6, 12), "AL", None, None, "annual leave 2-6 Dec"),
    ("DANIEL", D(25, 12), None, "PH", None, None, "public holiday replacement (worked 10/10)"),
    ("PRIYA", D(5, 12), None, "COURSE", "Stroke course", None, "Show as = what appears in the cell"),
    ("KEVIN", D(8, 12), None, "MC", None, None, "MC / EL are shown as LEAVE on the website"),
    ("NADIA HUDA", D(30, 11), None, "WANT NIGHT", None, "MUST", "the next day becomes PN automatically"),
    ("MICHAEL", D(5, 12), None, "OFF", None, "MUST", "a specific day off (counts as the weekly off)"),
    ("SITI AMINAH", D(4, 12), D(6, 12), "NO NIGHT", None, "PREFER", "PREFER = only if it fits"),
    ("JASON", D(1, 12), None, "DAY SHIFT", None, "MUST", "must work a day shift (AM/SD/LD) - not off, not night"),
    ("MICHAEL", D(3, 12), None, "FIXED SHIFT", "MINOR OT", "MUST", "a specific shift"),
    ("FARAH", D(30, 11), D(13, 12), "ONLY SHIFT", "MSW LD", None, "new HO: MSW LD only for 2 weeks"),
    ("NADIA HUDA", D(7, 12), D(13, 12), "OFF COUNT", "0", None, "no off day that week (e.g. to claim later)"),
    ("HANNAH", D(10, 12), None, "AL", None, None, "subspecialty HOs can have leave too"),
]

# Person, Together with, On these shifts, Must/Prefer, Notes
PAIRS = [
    ("DANIEL", "AISYAH, MICHAEL", "ETD ON, EMOT PM", "MUST", "junior always with one of these two on night"),
    ("PRIYA", "", "EMOT AM TAG", "MUST", "blank partner = any senior; TAG partner = an EMOT AM that day"),
    ("NADIA HUDA", "JASON", "MSW ON", "PREFER", "friends who want nights together"),
]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rdata.create_data_workbook(OUT, None)
    wb = openpyxl.load_workbook(OUT)

    ws = wb["DOCTORS"]
    for row in DOCTORS:
        ws.append(list(row))
    rq = wb["REQUESTS"]
    for i, row in enumerate(REQUESTS, 2):
        for c, v in enumerate(row, 1):
            rq.cell(i, c).value = v
    pr = wb["PAIRS"]
    for i, row in enumerate(PAIRS, 2):
        for c, v in enumerate(row, 1):
            pr.cell(i, c).value = v

    # highlight the Notes column so it is obvious it is only an explanation
    for sheet, col in ((ws, 12), (rq, 7), (pr, 5)):
        for r in range(2, sheet.max_row + 1):
            if sheet.cell(r, col).value:
                sheet.cell(r, col).fill = NOTE_FILL
        sheet.cell(1, 1).comment = Comment("EXAMPLE with made-up names. Yellow Notes cells explain each row.", "HO Roster")

    how = wb["HOW TO USE"]
    how.insert_rows(1, 2)
    how.cell(1, 1).value = "THIS IS AN EXAMPLE with made-up names - copy the way the rows are filled in, not the names."
    how.cell(1, 1).font = openpyxl.styles.Font(name="Consolas", b=True, sz=12, color="FFC00000")
    wb.save(OUT)
    print("written:", OUT)


if __name__ == "__main__":
    main()
