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
  - **EOP** (end of posting): from that date the HO is no longer in any pool.
- [ ] 🔒 *Active = NO* removes the HO from the sheet *(DOCTORS)*.

## B. Nights and post-nights
- [ ] 🔒 Night shifts are **ETD ON, EMOT PM, MSW ON, FSW ON** *(RULES: Night shift codes)*.
- [ ] 🔒 **Every night is followed by PN**, and PN only ever comes after a night.
- [ ] 🔒 Night on **last Sunday** gives **PN on Monday**. Night on **this Sunday** puts **PN in column J**.
- [ ] 🔒 **No night the day before leave**, a course, or the HO's last day.
- [ ] ⭐ **Looks ahead to next Monday:** if an HO has a request on next Monday (leave, a night, an off…), they get **no night this Sunday**, which would make Monday PN.
- [ ] 🔒 **No nights** for *Nights allowed = NO* *(DOCTORS)*.
- [ ] 🔒 **Subspecialty HOs work AM only.**
  - If one **asks for an ON**, they get it, and a pool HO covers their unit that day, preferably one who has worked there before.
  - Otherwise ETD ON is covered from MSW or FSW, never from a subspecialty.
- [ ] 🔒 At most **Max nights** a week, default 2 *(DOCTORS: Max nights / RULES: Default max nights)*. Raised automatically if the HO asked for more nights that week.
  - Seniors (and juniors) may do **2 nights** so every pool keeps **at least 2 night doctors every day** (ETD ON, MSW ON, FSW ON min 2).
- [ ] ⭐ At least **Min nights** a week, default 1.
  - Only applies to HOs working 4+ days that week who are allowed nights that week, so not tagging HOs.
  - e.g. Min 3 / Max 3 for an HO who asked for exactly 3 nights a week.
- [ ] 👍 Avoid **night → PN → night**, also across the weekend *(RULES: Avoid night right after post-night)*.

## C. Off days
- [ ] 🔒 Exactly the right number of **OFF days**: default 1 *(DOCTORS: Off days per week / RULES: Default off days)*.
  - An HO with fewer than 2 working days that week gets none.
  - **OFF COUNT** requests override it for one week, e.g. 0 for an HO who works the whole week and claims the off later.
  - More OFF requests than the number means more offs that week.
- [ ] ⭐ **OFF (owe)**: an HO who worked last week with **no off day** gets **2 offs** this week. One is shown as **OFF (owe)** *(RULES: Give owed offs)*.
  - Old "*owe" notes in column K are **ignored**.
  - "Owe" requests in the leave form are dropped unless they sit between leave days, e.g. between PH and AL. In that case enter an OFF with *Show as* = `OFF (owe)`.
- [ ] 👍 **Subspecialty HOs** get their off on **Sat/Sun** if possible *(RULES: Subspecialty preferred off days)*.
- [ ] ⭐ **HPB team** off days fall on **Thu–Sun** *(RULES: HPB team off days)*.

## D. Leave and requests (REQUESTS tab)
- [ ] 🔒 **AL, MC, EL, PH, COURSE** appear on exactly those dates. A COURSE shows the *Show as* text, e.g. "Mass circumcision".
  - A COURSE counts as a **working day**, not off, PH or AL.
  - A course that should count as an off day (e.g. the NSX suturing workshop) is entered as **OFF**.
- [ ] 🔒 **Pre-booked MC** (an MC in REQUESTS) shows as a **dummy day shift**: SD for MSW/FSW HOs, ETD AM for ETD HOs, or the unit for subspecialty HOs. They apply MC on the day itself.
  - The HO is **not counted** in that day's staffing, so someone else covers.
  - *Show as* overrides the text (e.g. `MC`). It still counts towards the AL/MC limit warning.
- [ ] 🔒 **PH, MC and AL are never carried** into the next week.
- [ ] ⭐ **MUST** requests are met: OFF, NO NIGHT, WANT NIGHT, DAY SHIFT, FIXED SHIFT. One that is impossible (e.g. a night asked for on a PN day) is listed as `! REQUEST NOT MET`.
- [ ] 👍 **PREFER** requests are met if they fit.
- [ ] 🔒 **POOL** puts an HO in a set pool or subspecialty for those weeks, e.g. PJHUS for one week. They go back to their DOCTORS pool afterwards.
- [ ] 🔒 **ONLY SHIFT** limits an HO to the listed shifts on those dates.
- [ ] 🔒 Requests outside the week being made are ignored, so old rows can stay.
- [ ] 🔒 A night requested by a no-night HO is **skipped**, with a message.
- [ ] ⭐ Warnings only (they never block the week):
  - **AL** over 8 per posting (MC beyond 2 days counts as AL) *(RULES: Max AL per posting / MC days before they count as AL)*.
  - **PH** claimed without having worked one of the claimable public holidays, including PN *(RULES: Claimable public holidays)*. PH itself is unlimited.

## E. Juniors and seniors
- [ ] ⭐ A **Junior (1st posting)** on night always has a **senior on night in the same group**. Default groups: `ETD ON + EMOT PM` · `MSW ON` · `FSW ON` *(RULES: Juniors on night need a senior / Night groups)*. Breaks are listed as `! NOT PAIRED`.
- [ ] ⭐ / 👍 Extra pairings from the **PAIRS** tab, e.g. "this junior always with one of these two seniors on night" (MUST), or "these two want nights together" (PREFER).
- [ ] 👍 **SAME** pairs (PAIRS, *On these shifts* = `SAME`): the HOs get their **off days and nights on the same days** where possible.

## F. EMOT AM and EMOT AM TAG
- [ ] 🔒 **EMOT AM** is only for HOs with *EMOT AM trained = YES*.
- [ ] 🔒 **EMOT AM TAG** is only for HOs with *EMOT AM trained = NO*, and **only on a day that has an EMOT AM**.
- [ ] 🔒 EMOT AM and TAG come from **any pool (ETD, MSW, FSW), never a subspecialty** *(RULES: Shifts any pool can do)*.
- [ ] 👍 **At most one EMOT shift (AM, PM or TAG) per HO per week**, unless really needed.
- [ ] 👍 Each untrained HO gets **one EMOT AM TAG a week** if possible *(RULES: Give EMOT AM TAG to untrained HOs)*.
- [ ] Once someone has done enough TAGs, change them to *EMOT AM trained = YES* in DOCTORS. **The app does not do this for you.**

## G. New HOs (tagging)
- [ ] 🔒 An HO with a **Start date** in MSW/FSW **tags** for 14 working days: `MSW TAG 1`, `MSW TAG 2` … `MSW TAG 14` *(RULES: Tagging days for new HOs)*.
  - The number counts **working days**, so off days don't use a number.
  - It carries on from last week's sheet.
- [ ] 🔒 While tagging: **no nights**, no other shifts, and **1 off a week**.
- [ ] 🔒 An **OFF TAG** request ends tagging early from that date. After that the HO works normally (SD, nights…).
- [ ] 🔒 Tagging HOs **count as LD**: they are included in the ward's SD + LD total (min / max 9) and in the MSW:FSW 1:1 balance.
  - The *MSW LD / FSW LD* row itself still means real LDs (only 1 on days with a tagging HO).

## H. Subspecialties
- [ ] ⭐ **HPB has 4 HOs every day** *(STAFFING: HPB Mon–Sun, Min 4)*. When an HPB team HO is off, a pool HO covers HPB that day.
- [ ] 👍 **Other subspecialties on weekdays**: if a unit HO is on MC/AL/PH (or a requested ON), a pool HO covers, **only if the pools can spare one**. The app tries not to sub in too often, so the team stays familiar.
- [ ] 👍 The **same pool HO** covers all the HPB cover days of the week if possible *(RULES: HPB: same pool doctor)*.
- [ ] 🔒 Subspecialty HOs (HPB, VAS, PLASTIC, PERI, PJHUS, NEURO, PAEDS, UGI) only work **their unit** or are OFF, on leave, or on a requested ON.
- [ ] 👍 **Subspecialty rotation** *(RULES: Pool rotation = YES, Subspecialty rotation weeks = `PERI 1, OTHERS 3`)*:
  - After **3 weeks** (PERI: **1 week**), the HO swaps with a pool HO who has **never been to that unit**. It starts on the Monday.
  - The incoming HO has done 2+ weeks in their pool, isn't tagging, isn't leaving soon and has no shift requests that week.
  - **HPB**: all 4 swap together when they're all due.
  - A place left by **EOP** is filled from the pools.
  - **Never** put in a subspecialty: *RULES: Never in subspecialty* (names, comma-separated).
  - *Not done yet:* the new HO overlapping with the old team on the weekend before a rotation.

## I. Staffing per day (STAFFING tab)
| Shift | Days | Min ⭐ | Ideal 👍 | Max 👍 |
|---|---|---|---|---|
| ETD AM | Mon–Sun | 2 | 3 | 5 |
| ETD AM + EMOT AM | Mon–Sun | – | – | 7 |
| EMOT AM | Mon–Sun | 1 | 1 | 2 |
| EMOT AM TAG | Mon–Sun | 0 | 0 | 1 |
| ETD ON | Mon–Sun | 2 | 2 | 3 |
| EMOT PM | Mon–Sun | 1 | 1 | 1 |
| MSW SD + MSW LD (+ tagging HOs) | Mon–Sun | 5 | 6 | 9 |
| MSW LD | Mon–Sun | 1 | 1 | 2 (**1 on days with a tagging HO**) |
| MSW ON | Mon–Sun | 2 | 2 | 2 |
| FSW SD + FSW LD (+ tagging HOs) | Mon–Sun | 4 | 5 | 9 |
| FSW LD | Mon–Sun | 1 | 1 | 2 (**1 on days with a tagging HO**) |
| FSW ON | Mon–Sun | 2 | 2 | 2 |
| SCOPE/CLINIC | Mon–Wed | 1 | 2 | 2 |
| MINOR OT | Thu | 1 | 1 | 1 |
| HPB | Mon–Sun | 4 | 4 | 4 |

- [ ] ⭐ **Min** is met. A miss is listed as `! SHORT` and the TOTAL cell turns red.
- [ ] 👍 **Ideal** is reached (a miss is listed as "below ideal"), and **Max** isn't passed (listed as "extra").
- [ ] ⭐ **No more than 9 day doctors in MSW or in FSW at one time.** Extra HOs go to ETD AM (max 5) or EMOT AM instead. Going over any Max is now worse than borrowing.
- [ ] ⭐ **MSW and FSW have the same number of day doctors (SD + LD + tagging) every day, 1:1** *(RULES: Balance MSW and FSW day doctors 1:1)*. To balance them, MSW and FSW HOs work each other's day shifts freely.
- [ ] 🔒 **Ward day shifts (MSW/FSW SD and LD) only come from MSW and FSW HOs**, never from ETD or a subspecialty.
- [ ] ⭐ **Other borrowing** (e.g. an FSW HO on ETD ON) only happens to fill a gap, never just to reach the ideal *(RULES: Borrow doctors from other pools)*.

## J. Fairness and variety
- [ ] 👍 **Not the same as last week**: no night or off day on the same weekday, few identical shifts *(RULES: Make each week different)*.
- [ ] 👍 Over the last 6 weeks, HOs who've had fewer of these get them next: **nights, weekend nights (Fri–Sun), Clinic/OT/HPB, LD**. HOs who've had fewer **weekend offs** get them *(RULES: Weeks of history for fairness)*.
- [ ] 👍 **Clinic/Scope and Minor OT** go to different HOs on different days.

## K. Pool rotation and ward counters
- [ ] 🔒 **Columns M–W** (weeks in MSW, FSW, EMOT/ETD, HPB, …): +1 in the column of the ward the HO was in **last week**. The **pink cell** marks the current ward. New HOs start at 0.
- [ ] 👍 **Pool rotation** *(RULES: Pool rotation = YES)* moves some HOs every week. An HO is due when they've done:
  - **4+ weeks in a row** in one pool, or
  - **3+ weeks more** in their pool than in another one (balancing).
- [ ] 👍 Due HOs swap so each pool keeps the same number of HOs. Each goes to the pool they've **spent least time in**, a never-been pool first. **YES** updates *Pool* in DOCTORS (**SUGGEST** only lists the moves).
- [ ] 🔒 Nobody is moved:
  - before **2 weeks** in a pool *(RULES: Minimum weeks in a pool)*;
  - if they're **leaving within 3 weeks**;
  - if they're a new HO;
  - if they have a **POOL** request;
  - if they were moved by hand in DOCTORS.

## L. The sheet
- [ ] 🔒 The new tab goes **first**, with the same layout, colours, legend and name colours.
- [ ] 🔒 **TOTAL rows** are recalculated.
- [ ] 🔒 **EOP section**: names kept, days left empty.
- [ ] 🔒 A **backup** of the timetable is saved before every change, in `Roster backups\` next to the timetable.
