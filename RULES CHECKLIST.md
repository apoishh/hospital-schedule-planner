# HO Roster: rules checklist

This is every rule the app follows when it makes a week. Use it to check each new week, or after hand edits.

**How strict each rule is:**

| Label | Meaning |
|---|---|
| 🔒 **Always** | Never broken. |
| ⭐ **Must** | Broken only if there is no other way. Every break is listed in the app with `!` and red text. |
| 👍 **Tries** | Done when possible. Misses are listed in the app without `!`. |

**Where problems show up:**
1. The app's message box after **Make next week**.
2. Red cells in the TOTAL rows of the new tab.
3. **Check newest week**, which checks a tab again after you edit it by hand.

The settings that change a rule are in brackets, e.g. *(RULES: Default max nights)*. They're all in `Roster Data.xlsx`.

---

## A. Every HO, every day
- [ ] 🔒 Exactly **one shift per day** for every HO in ETD, MSW, FSW and the subspecialties.
- [ ] 🔒 A shift is only given on days listed for it in STAFFING, e.g. Clinic/Scope Mon–Wed, Minor OT Thursday.
- [ ] 🔒 Days before *Start date* or after *Last day (EOP)* are left **blank**, and the HO isn't counted on those days *(DOCTORS)*.
- [ ] 🔒 *Active = NO* removes the HO from the sheet *(DOCTORS)*.

## B. Nights and post-nights
- [ ] 🔒 Night shifts are **ETD ON, EMOT PM, MSW ON, FSW ON** *(RULES: Night shift codes)*.
- [ ] 🔒 **Every night is followed by PN**, and PN only ever comes after a night.
- [ ] 🔒 Night on **last Sunday** gives **PN on Monday**. Night on **this Sunday** puts **PN in column J**.
- [ ] 🔒 **No night the day before leave**, a course, or the HO's last day.
- [ ] ⭐ **Looks ahead to next Monday:** if an HO has a request on next Monday (leave, a night, an off…), they get **no night this Sunday**, which would make Monday PN.
- [ ] 🔒 **No nights** for *Nights allowed = NO* *(DOCTORS)*.
- [ ] 🔒 **No nights for subspecialty HOs.** ETD ON can be covered from MSW or FSW, never from a subspecialty.
- [ ] 🔒 At most **Max nights** a week, default 2 *(DOCTORS: Max nights / RULES: Default max nights)*. Raised automatically if the HO asked for more nights that week.
- [ ] ⭐ At least **Min nights** a week, default 1. Only applies to HOs working 4+ days that week who are allowed nights that week.
  - e.g. Min 3 / Max 3 for an HO who asked for exactly 3 nights a week.
- [ ] 👍 Avoid **night → PN → night**, also across the weekend *(RULES: Avoid night right after post-night)*.

## C. Off days
- [ ] 🔒 Exactly the right number of **OFF days**: default 1 *(DOCTORS: Off days per week / RULES: Default off days)*.
  - An HO with fewer than 2 working days that week gets none.
  - **OFF COUNT** requests override it for one week, e.g. 0 for an HO who works the whole week and claims the off later.
  - More OFF requests than the number means more offs that week.
- [ ] ⭐ **Owed offs**: column K "*owe 1 off" gives one extra off, shown as **OFF (owe)**; the note is then cleared *(RULES: Give owed offs)*.
- [ ] 👍 **Subspecialty HOs** get their off on **Sat/Sun** if possible *(RULES: Subspecialty preferred off days)*.
- [ ] ⭐ **HPB team** off days fall on **Thu–Sun** *(RULES: HPB team off days)*.

## D. Leave and requests (REQUESTS tab)
- [ ] 🔒 **AL, MC, EL, PH, COURSE** appear on exactly those dates. A COURSE shows the *Show as* text, e.g. "Stroke course".
- [ ] 🔒 **PH, MC and AL are never carried** into the next week.
- [ ] 🔒 **ONLY SHIFT** limits an HO to the listed shifts on those dates, e.g. new HOs on FSW LD / MSW LD only for their first 2 weeks.
- [ ] ⭐ **MUST** requests are met: OFF, NO NIGHT, WANT NIGHT, DAY SHIFT, FIXED SHIFT. One that is impossible (e.g. a night asked for on a PN day) is listed as `! REQUEST NOT MET`.
- [ ] 👍 **PREFER** requests are met if they fit.
- [ ] 🔒 Requests outside the week being made are ignored, so old rows can stay.
- [ ] 🔒 A night requested by a no-night or subspecialty HO is **skipped**, with a message.

## E. Juniors and seniors
- [ ] ⭐ A **Junior (1st posting)** on night always has a **senior on night in the same group**. Default groups: `ETD ON + EMOT PM` · `MSW ON` · `FSW ON` *(RULES: Juniors on night need a senior / Night groups)*. Breaks are listed as `! NOT PAIRED`.
- [ ] ⭐ / 👍 Extra pairings from the **PAIRS** tab, e.g. "this junior always with one of these two seniors on night" (MUST), or "these two want nights together" (PREFER).

## F. EMOT AM and EMOT AM TAG
- [ ] 🔒 **EMOT AM** is only for HOs with *EMOT AM trained = YES*.
- [ ] 🔒 **EMOT AM TAG** is only for HOs with *EMOT AM trained = NO*, and **only on a day that has an EMOT AM**.
- [ ] 🔒 EMOT AM and TAG come from **any pool (ETD, MSW, FSW), never a subspecialty** *(RULES: Shifts any pool can do)*.
- [ ] 👍 Each untrained HO gets **one EMOT AM TAG a week** if possible *(RULES: Give EMOT AM TAG to untrained HOs)*.
- [ ] Once someone has done enough TAGs, change them to *EMOT AM trained = YES* in DOCTORS. **The app does not do this for you.**

## G. HPB and subspecialty
- [ ] ⭐ **HPB has 4 HOs every day** *(STAFFING: HPB Mon–Sun, Min 4)*. When an HPB team HO is off, a pool HO covers HPB that day.
- [ ] 👍 The **same pool HO** covers all the HPB cover days of the week if possible *(RULES: HPB: same pool doctor)*.
- [ ] 🔒 Subspecialty HOs (HPB, VAS, PLASTIC, PERI, PJHUS, NEURO, PAEDS, UGI) only work **their unit** or are OFF, on leave, etc.

## H. Staffing per day (STAFFING tab)
| Shift | Days | Min ⭐ | Ideal 👍 | Max 👍 |
|---|---|---|---|---|
| ETD AM | Mon–Sun | 2 | 3 | 3 |
| EMOT AM | Mon–Sun | 1 | 1 | 2 |
| EMOT AM TAG | Mon–Sun | 0 | 0 | 1 |
| ETD ON | Mon–Sun | 2 | 2 | 3 |
| EMOT PM | Mon–Sun | 1 | 1 | 1 |
| MSW SD + MSW LD | Mon–Sun | 5 | 6 | 12 |
| MSW LD | Mon–Sun | 1 | 1 | 6 |
| MSW ON | Mon–Sun | 2 | 2 | 2 |
| FSW SD + FSW LD | Mon–Sun | 4 | 5 | 12 |
| FSW LD | Mon–Sun | 1 | 1 | 6 |
| FSW ON | Mon–Sun | 2 | 2 | 2 |
| SCOPE/CLINIC | Mon–Wed | 1 | 2 | 2 |
| MINOR OT | Thu | 1 | 1 | 1 |
| HPB | Mon–Sun | 4 | 4 | 4 |

- [ ] ⭐ **Min** is met. A miss is listed as `! SHORT` and the TOTAL cell turns red.
- [ ] 👍 **Ideal** is reached (a miss is listed as "below ideal"), and **Max** isn't passed (listed as "extra").
- [ ] ⭐ **Borrowing** between ETD, MSW and FSW only happens to fill a gap, never just to reach the ideal *(RULES: Borrow doctors from other pools)*.

## I. Fairness and variety
- [ ] 👍 **Not the same as last week**: no night or off day on the same weekday, few identical shifts *(RULES: Make each week different)*.
- [ ] 👍 Over the last 6 weeks, HOs who've had fewer of these get them next: **nights, weekend nights (Fri–Sun), Clinic/OT/HPB, LD**. HOs who've had fewer **weekend offs** get them *(RULES: Weeks of history for fairness)*.
- [ ] 👍 **Clinic/Scope and Minor OT** go to different HOs on different days.

## J. Pool rotation and ward counters
- [ ] 🔒 **Columns M–W** (weeks in MSW, FSW, EMOT/ETD, HPB, …): +1 in the column of the ward the HO was in **last week**. The **pink cell** marks the current ward. New HOs start at 0.
- [ ] 👍 **Rotation** *(RULES: Pool rotation = NO / SUGGEST / YES)*:
  - An HO who has done **4+ weeks in a row** in one pool is **due to move**.
  - They swap with other due HOs, so each pool keeps the same number of HOs.
  - Each goes to a pool they've **never been to** if possible, otherwise the one they've had least.
  - **SUGGEST** (the default) lists the moves; **YES** makes them and updates *Pool* in DOCTORS.
- [ ] 🔒 Nobody is moved before **2 weeks** in a pool *(RULES: Minimum weeks in a pool)*. New HOs, and HOs moved by hand in DOCTORS, aren't moved.

## K. The sheet
- [ ] 🔒 The new tab goes **first**, with the same layout, colours, legend and name colours.
- [ ] 🔒 **TOTAL rows** are recalculated.
- [ ] 🔒 **EOP section**: names kept, days left empty.
- [ ] 🔒 A **backup** of the timetable is saved before every change, in `Roster backups\` next to the timetable.
