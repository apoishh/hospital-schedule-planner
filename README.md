# HO Roster

**A tool that makes the weekly Surgical House Officer (HO) timetable: ETD/EMOT, MSW, FSW and subspecialties. It adds the week as a new tab in the existing Excel timetable and can publish a read-only web page so every HO can see it.**

**Live demo of the viewer page** (made-up names): https://apoishh.github.io/hospital-schedule-planner/ · **Download the app:** [latest release](https://github.com/apoishh/hospital-schedule-planner/releases/latest)

## Objective

Turn a 2–3 hour weekly job (arranging about 55 HOs by hand) into a few minutes:
1. Type in this week's leave and requests.
2. Press one button.
3. Check what the app flags.

The result must follow every department rule and be fair over time.

## Summary

| | |
|---|---|
| **Input** | The existing timetable workbook, plus a small **Roster Data.xlsx**: who is working, their traits, requests and rules |
| **Output** | Next week's tab, added at the front of the timetable in the same layout and colours. Optionally, a web page with the latest weeks |
| **Who runs it** | The roster maker. They double-click **HO Roster.exe**, with no Python or setup needed |
| **Who sees it** | Everyone, in the Excel file as now, or through the viewer link on their phone |
| **Rules** | Listed one by one in **[RULES CHECKLIST.md](RULES%20CHECKLIST.md)** |
| **How to use** | **[How to use HO Roster.txt](release-files/How%20to%20use%20HO%20Roster.txt)**, with step-by-step instructions and examples |

## Why it exists

Doing the roster by hand means keeping many rules in mind at once:
- 1 off day and 1–2 nights each, with PN after every night;
- no nights for some HOs;
- juniors never alone on night;
- EMOT AM TAG next to an EMOT AM;
- HPB at 4 every day;
- leave, courses and individual requests;
- not repeating last week, and fair weekend nights.

It's easy to miss one, and hard to be fair over months. The app checks every rule every time and explains what it couldn't do. Excel stays the official record, so nothing changes for the rest of the department.

## How it works

```
 Timetable.xlsx (last week's tab)  ─┐
 Roster Data.xlsx                   ├──►  HO Roster.exe  ──►  new tab in Timetable.xlsx
   DOCTORS · REQUESTS · PAIRS       │      (solver)           + backup in "Roster backups\"
   STAFFING · RULES                 ┘                          + message list of anything to check
                                                                     │
                                                    "Publish online" ▼
                                                    viewer web page (read-only link)
```

1. **Reads last week** from the newest tab:
   - who was where;
   - who was on night on Sunday, so they get PN on Monday;
   - owed offs (column K);
   - weeks in each ward (columns M–W).
2. **Reads Roster Data.xlsx:**
   - **DOCTORS:** pool, nights allowed, junior, EMOT AM trained, start and last day.
   - **REQUESTS:** leave, offs, nights, courses.
   - **PAIRS:** extra pairings.
   - **STAFFING:** HOs needed per shift per day.
   - **RULES:** general settings.
3. **Builds the week** with a scheduling solver (Google OR-Tools).
   - Rules marked *Always* are never broken.
   - Everything else is weighted, so it always produces a week and lists what it couldn't meet.
4. **Writes the new tab:** same layout and colours, totals recalculated, ward counters +1, and a backup saved first.
5. **Check newest week** checks a tab again after hand edits.
6. **Preview / Publish** turns the newest weeks into one web page:
   - colour-coded;
   - "who's on call tonight";
   - search by name;
   - works on phones.

## Where everything is

| What | Where |
|---|---|
| The app, for the roster maker | `release/HO Roster.zip`. Unzip anywhere and run `HO Roster.exe` |
| Weekly how-to | [release-files/How to use HO Roster.txt](release-files/How%20to%20use%20HO%20Roster.txt) (also inside the zip) |
| Rules checklist | [RULES CHECKLIST.md](RULES%20CHECKLIST.md) (also inside the zip) |
| Live demo page | [docs/index.html](docs/index.html), served by GitHub Pages. It's built with `tools/make_demo.py`, which swaps every real name for a made-up one and refuses to write the page if any real name is left |
| Input example | [examples/Roster Data EXAMPLE.xlsx](examples/Roster%20Data%20EXAMPLE.xlsx): every tab filled in with made-up names, one row per request type, each row explained. Also in the zip. Rebuild with `tools/make_example.py` |
| Roster Data.xlsx | Next to the timetable. The app's **Open Roster Data** button opens it |
| Backups | `Roster backups\`, next to the timetable |
| Viewer page | `HO Roster viewer\index.html`, next to the timetable |
| Test copies | [preview/](preview/): `Timetable PREVIEW 30-11 week.xlsx` (your timetable plus the 30/11–6/12 week) and `Roster Data - December.xlsx` (56 HOs, 198 December requests) |

## Code

| File | What it does |
|---|---|
| [roster/timetable.py](roster/timetable.py) | Reads week tabs (finds sections by their header rows) and writes the new tab, copying styles and counters |
| [roster/data.py](roster/data.py) | Creates and reads Roster Data.xlsx (columns found by header name) |
| [roster/solver.py](roster/solver.py) | The schedule model: hard rules plus weighted goals. Weights are at the top |
| [roster/generate.py](roster/generate.py) | Glue: last week, Roster Data and history in → solver → new tab. Has a CLI |
| [roster/rotation.py](roster/rotation.py) | Pool rotation: who is due to move and to which pool |
| [roster/check.py](roster/check.py) | Checks any week tab against the rules (for hand edits) |
| [roster/viewer.py](roster/viewer.py) + [viewer_template.html](roster/viewer_template.html) | Builds the read-only web page |
| [roster/publish.py](roster/publish.py) | Uploads the web page to Netlify |
| [app.py](app.py) | The window used for the .exe |

## Developer notes

Use the project's own Python environment, not your global Python:

```powershell
& "$env:USERPROFILE\.venvs\hospital-roster\Scripts\python.exe" app.py
```

To run the generator and checker from the command line:

```powershell
& "$env:USERPROFILE\.venvs\hospital-roster\Scripts\python.exe" -m roster.generate "Timetable.xlsx" "Roster Data.xlsx" --week 07/12/2026 --out test.xlsx
```

```powershell
& "$env:USERPROFILE\.venvs\hospital-roster\Scripts\python.exe" -m roster.check test.xlsx "Roster Data.xlsx"
```

To build the viewer page by hand:

```powershell
& "$env:USERPROFILE\.venvs\hospital-roster\Scripts\python.exe" -m roster.viewer "Timetable.xlsx" site --data "Roster Data.xlsx"
```

To rebuild the .exe and `release/HO Roster.zip`:

```powershell
.\build.ps1
```

### Viewer website
- **One file:** the page is a single self-contained `index.html`, with no server or database. It opens straight from disk.
- **On your phone:** to see it on a phone on the same Wi-Fi, run `python -m http.server 8765 --directory "<folder>\HO Roster viewer"`, then go to `http://<this PC's IP>:8765`.
- **Publishing:** **Publish online** uploads the folder to Netlify. The token and site ID are saved on that PC only, in `%APPDATA%\HO Roster\settings.json`.
- **Privacy:**
  - the page asks search engines not to list it, but anyone with the link can open it;
  - MC and EL show as LEAVE (RULES: Viewer: show MC/EL as LEAVE).
