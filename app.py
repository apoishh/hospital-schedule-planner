"""HO Roster - small window around the generator, for double-click use."""
import json
import os
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import openpyxl

try:
    import sv_ttk          # Windows 11 style theme
except ImportError:        # still works without it, just plainer
    sv_ttk = None

from roster import data as rdata
from roster.check import check_week
from roster.generate import RosterError, SheetExists, generate
from roster.publish import PublishError, create_site, deploy
from roster.timetable import load_weeks
from roster.viewer import build_site

SETTINGS = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HO Roster", "settings.json")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(s):
    try:
        os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except Exception:
        pass


def resource(*parts):
    """A file shipped next to the .exe, or in the project when run from source."""
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(base, *parts), os.path.join(base, "release-files", *parts)):
        if os.path.exists(p):
            return p
    return None


LOG_COLOURS = {
    "light": dict(bg="#ffffff", fg="#1c1c1c", muted="#6b6b6b", bad="#c42b1c", good="#0f7b0f", head="#005fb8", rule="#e5e5e5"),
    "dark": dict(bg="#1f1f1f", fg="#e6e6e6", muted="#9a9a9a", bad="#ff8a80", good="#6ccb5f", head="#60cdff", rule="#3a3a3a"),
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HO Roster")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.q = queue.Queue()
        self.busy = False
        s = load_settings()
        self.theme = s.get("theme", "light")
        if sv_ttk:
            sv_ttk.set_theme(self.theme)
        self._fonts()

        # ---- header
        head = ttk.Frame(self, padding=(20, 16, 20, 8))
        head.pack(fill="x")
        ttk.Label(head, text="HO Roster", style="Title.TLabel").pack(side="left")
        ttk.Label(head, text="   Surgical HO weekly timetable", style="Sub.TLabel").pack(side="left", pady=(8, 0))
        self.theme_btn = ttk.Button(head, width=11, command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=(6, 0))
        ttk.Button(head, text="Rules", command=lambda: self.open_doc("RULES CHECKLIST.md")).pack(side="right", padx=(6, 0))
        ttk.Button(head, text="Help", command=lambda: self.open_doc("How to use HO Roster.txt")).pack(side="right")

        body = ttk.Frame(self, padding=(20, 4, 20, 8))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=430)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        # ---- card 1: files
        c1 = self._card(left, "1", "Files", "Your timetable and the Roster Data you edit")
        self.tt = tk.StringVar(value=s.get("timetable", ""))
        self.rd = tk.StringVar(value=s.get("data", ""))
        self._file_row(c1, 0, "Timetable", self.tt, self.pick_tt)
        self._file_row(c1, 1, "Roster Data", self.rd, self.pick_rd)
        links = ttk.Frame(c1)
        links.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(links, text="Open Roster Data", command=self.open_rd).pack(side="left")
        ttk.Button(links, text="Open Timetable", command=lambda: self.open_file(self.tt.get())).pack(side="left", padx=6)
        ttk.Button(links, text="Open folder", command=self.open_folder).pack(side="left")

        # ---- card 2: make the week
        c2 = self._card(left, "2", "Make the week", "Uses the requests in Roster Data right now")
        wk = ttk.Frame(c2)
        wk.grid(row=0, column=0, columnspan=3, sticky="ew")
        ttk.Label(wk, text="Week starting").pack(side="left")
        self.week = tk.StringVar(value="")
        ttk.Entry(wk, textvariable=self.week, width=12).pack(side="left", padx=8)
        ttk.Label(wk, text="dd/mm/yyyy · blank = next week", style="Muted.TLabel").pack(side="left")
        self.b_make = ttk.Button(c2, text="Make next week", style="Accent.TButton", command=self.make)
        self.b_make.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(12, 6), ipady=6)
        self.b_check = ttk.Button(c2, text="Check newest week (after hand edits)", command=self.check)
        self.b_check.grid(row=2, column=0, columnspan=3, sticky="ew")
        c2.columnconfigure(0, weight=1)

        # ---- card 3: share
        c3 = self._card(left, "3", "Share with everyone", "Read-only web page with the newest weeks")
        row = ttk.Frame(c3)
        row.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.b_preview = ttk.Button(row, text="Preview", command=self.preview_viewer)
        self.b_preview.pack(side="left")
        self.b_publish = ttk.Button(row, text="Publish online", command=self.publish_viewer)
        self.b_publish.pack(side="left", padx=6)
        ttk.Button(row, text="Settings…", command=self.web_settings).pack(side="left")
        lk = ttk.Frame(c3)
        lk.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        lk.columnconfigure(0, weight=1)
        self.url = tk.StringVar(value=s.get("netlify_url", "") or "not published yet")
        ttk.Entry(lk, textvariable=self.url, state="readonly").grid(row=0, column=0, sticky="ew")
        ttk.Button(lk, text="Copy link", command=self.copy_link).grid(row=0, column=1, padx=(6, 0))
        c3.columnconfigure(0, weight=1)

        # ---- messages
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        bar = ttk.Frame(right)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(bar, text="Messages", style="Card.TLabel").pack(side="left")
        ttk.Button(bar, text="Clear", command=lambda: self.log_box.delete("1.0", "end")).pack(side="right")
        ttk.Button(bar, text="Copy all", command=self.copy_log).pack(side="right", padx=6)
        box = ttk.Frame(right, style="Card.TFrame", padding=1)
        box.grid(row=1, column=0, sticky="nsew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self.log_box = tk.Text(box, wrap="word", font=self.f_log, relief="flat", borderwidth=0,
                               padx=14, pady=12, spacing1=2, spacing3=2, highlightthickness=0)
        sb = ttk.Scrollbar(box, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=sb.set)
        self.log_box.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self._style_log()

        # ---- status bar
        status = ttk.Frame(self, padding=(20, 6, 20, 12))
        status.pack(fill="x")
        self.status = tk.StringVar(value="Ready")
        ttk.Label(status, textvariable=self.status, style="Muted.TLabel").pack(side="left")
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=180)   # shown only while working

        self.log("How it works", "head")
        self.log("1.  Put this week's leave and requests in Roster Data (REQUESTS tab). Save and close it.", "muted")
        self.log("2.  Close the timetable in Excel, then press Make next week. A backup is saved first.", "muted")
        self.log("3.  Open the timetable: the new week is the first tab. Edit anything by hand, then Check newest week.", "muted")
        self.log("4.  When it's final, Publish online so everyone sees it.", "muted")
        self.after(10, self._apply_chrome)
        self.after(100, self.pump)

    # ---------------------------------------------------------------- look
    def _fonts(self):
        fam = "Segoe UI"
        self.f_log = ("Consolas", 10)
        st = ttk.Style(self)
        st.configure("Title.TLabel", font=(fam + " Semibold", 20))
        st.configure("Sub.TLabel", font=(fam, 11), foreground="#7a7a7a")
        st.configure("Card.TLabel", font=(fam + " Semibold", 12))
        st.configure("Step.TLabel", font=(fam + " Semibold", 11), foreground="#ffffff", background="#005fb8",
                     anchor="center", width=2)
        st.configure("Muted.TLabel", font=(fam, 9), foreground="#7a7a7a")
        st.configure("Accent.TButton", font=(fam + " Semibold", 11))

    def _card(self, parent, num, title, sub):
        outer = ttk.LabelFrame(parent, padding=(14, 10, 14, 14))
        outer.pack(fill="x", pady=(0, 12))
        hd = ttk.Frame(outer)
        hd.pack(fill="x", pady=(0, 10))
        tk.Label(hd, text=num, bg="#005fb8", fg="#ffffff", font=("Segoe UI Semibold", 10),
                 width=2, padx=2, pady=0).pack(side="left")
        ttk.Label(hd, text=title, style="Card.TLabel").pack(side="left", padx=(8, 0))
        ttk.Label(hd, text=sub, style="Muted.TLabel").pack(side="left", padx=(10, 0), pady=(3, 0))
        inner = ttk.Frame(outer)
        inner.pack(fill="x")
        return inner

    def _file_row(self, parent, r, label, var, cmd):
        ttk.Label(parent, text=label, width=11).grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=var).grid(row=r, column=1, sticky="ew", pady=3, padx=(0, 6))
        ttk.Button(parent, text="Browse…", command=cmd).grid(row=r, column=2, pady=3)
        parent.columnconfigure(1, weight=1)

    def _style_log(self):
        c = LOG_COLOURS["dark" if self.theme == "dark" else "light"]
        self.log_box.configure(background=c["bg"], foreground=c["fg"], insertbackground=c["fg"],
                               selectbackground=c["head"])
        self.log_box.tag_config("bad", foreground=c["bad"], font=("Consolas", 10, "bold"))
        self.log_box.tag_config("good", foreground=c["good"], font=("Consolas", 10, "bold"))
        self.log_box.tag_config("muted", foreground=c["muted"])
        self.log_box.tag_config("head", foreground=c["head"], font=("Segoe UI Semibold", 11), spacing1=10)

    def _apply_chrome(self):
        """Theme button text + dark Windows title bar in dark mode."""
        self.theme_btn.config(text="Light mode" if self.theme == "dark" else "Dark mode")
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            val = ctypes.c_int(1 if self.theme == "dark" else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
            self.withdraw(); self.deiconify()     # repaint the title bar
        except Exception:
            pass

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        if sv_ttk:
            sv_ttk.set_theme(self.theme)
        self._fonts()
        self._style_log()
        self._apply_chrome()
        self.remember(theme=self.theme)

    def open_doc(self, name):
        p = resource(name)
        if p:
            os.startfile(p)
        else:
            messagebox.showinfo("Not found", f"'{name}' should be in the same folder as HO Roster.exe.")

    def copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_box.get("1.0", "end"))
        self.status.set("Messages copied")

    # ---------------------------------------------------------------- helpers
    def log(self, text, tag=None):
        t = str(text)
        if tag is None:
            if "SHORT" in t or t.startswith("! ") or "ERROR" in t or t.startswith("  ! "):
                tag = "bad"
            elif t.startswith("RESULT: all") or t.startswith("Done.") or " 0 issue" in t:
                tag = "good"
            elif t.startswith("RESULT") or t.startswith("Pool rotation") or t.startswith("Checked"):
                tag = "head"
            elif t.startswith("  - ") or t.startswith("Request:") or t.startswith("Note:"):
                tag = "muted"
        self.log_box.insert("end", t + "\n", tag)
        self.log_box.see("end")

    def section(self, title):
        self.log(f"{title}  ·  {datetime.now():%d %b %H:%M}", "head")

    def pump(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "done":
                    self.set_busy(False)
                elif kind == "remember":
                    self.remember(**payload)
                    if payload.get("netlify_url"):
                        self.url.set(payload["netlify_url"])
                elif kind == "ask_replace":
                    if messagebox.askyesno("Week already exists",
                                           f"The tab '{payload}' already exists.\n\nReplace it with a new one?\n"
                                           "(Any hand edits on that tab will be lost - a backup is kept.)"):
                        self.run(lambda: self._make(overwrite=True), "Making the week")
                    else:
                        self.log("Cancelled.")
        except queue.Empty:
            pass
        self.after(100, self.pump)

    def set_busy(self, busy, what="Working"):
        self.busy = busy
        state = "disabled" if busy else "normal"
        for b in (self.b_make, self.b_check, self.b_preview, self.b_publish):
            b.config(state=state)
        self.config(cursor="watch" if busy else "")
        if busy:
            self.status.set(f"{what}… this can take about a minute")
            self.progress.pack(side="right")
            self.progress.start(12)
        else:
            self.status.set("Ready")
            self.progress.stop()
            self.progress.pack_forget()

    def run(self, fn, what="Working"):
        self.set_busy(True, what)

        def work():
            try:
                fn()
            except SheetExists as e:
                self.q.put(("ask_replace", str(e)))
            except (RosterError, PublishError) as e:
                self.q.put(("log", f"ERROR: {e}"))
            except PermissionError as e:
                name = os.path.basename(getattr(e, "filename", "") or "") or "a file"
                self.q.put(("log", f"ERROR: '{name}' is open in Excel (or locked by OneDrive) - close it and try again."))
            except Exception as e:  # show anything unexpected instead of crashing
                self.q.put(("log", f"ERROR: {type(e).__name__}: {e}"))
            finally:
                self.q.put(("done", None))
        threading.Thread(target=work, daemon=True).start()

    def remember(self, **extra):
        s = load_settings()
        s.update({"timetable": self.tt.get(), "data": self.rd.get()}, **extra)
        save_settings(s)

    def pick_tt(self):
        p = filedialog.askopenfilename(title="Choose the timetable", filetypes=[("Excel", "*.xlsx")])
        if p:
            self.tt.set(p)
            if not self.rd.get():
                self.rd.set(os.path.join(os.path.dirname(p), "Roster Data.xlsx"))
            self.remember()
            problem = self.timetable_problem(p)
            if problem:
                messagebox.showwarning("Timetable", problem)

    def pick_rd(self):
        p = filedialog.asksaveasfilename(title="Choose (or name a new) Roster Data file",
                                         defaultextension=".xlsx", confirmoverwrite=False,
                                         initialfile="Roster Data.xlsx", filetypes=[("Excel", "*.xlsx")])
        if p:
            self.rd.set(p)
            self.remember()

    def open_file(self, p):
        if p and os.path.exists(p):
            os.startfile(p)
        else:
            messagebox.showinfo("Not found", "Choose the file first.")

    def open_folder(self):
        p = self.tt.get()
        folder = os.path.dirname(os.path.abspath(p)) if p else ""
        if folder and os.path.isdir(folder):
            os.startfile(folder)
        else:
            messagebox.showinfo("Not found", "Choose the timetable first.")

    def open_rd(self):
        p = self.rd.get()
        if p and not os.path.exists(p) and self.tt.get():
            self.log("Creating Roster Data from the newest week in the timetable...")
            def mk():
                wb = openpyxl.load_workbook(self.tt.get())
                rdata.create_data_workbook(p, load_weeks(wb, 2)[0])
                self.q.put(("log", f"Created {p}"))
                os.startfile(p)
            self.run(mk, "Creating Roster Data")
            return
        self.open_file(p)

    def timetable_problem(self, path):
        """Quick look at the chosen timetable; returns a message if it's the wrong file."""
        if not os.path.exists(path):
            return "Choose the timetable file first."
        if self.rd.get() and os.path.abspath(path).lower() == os.path.abspath(self.rd.get()).lower():
            return ("The Timetable and Roster Data boxes point to the same file.\n\n"
                    "Timetable = the big workbook with one tab per week.\n"
                    "Roster Data = the small file with DOCTORS / REQUESTS tabs.")
        try:
            wb = openpyxl.load_workbook(path, read_only=True)
            names = {n.upper() for n in wb.sheetnames}
            wb.close()
        except PermissionError:
            return f"'{os.path.basename(path)}' is open in Excel or locked - close it and try again."
        except Exception as e:
            return f"Could not open '{os.path.basename(path)}' as an Excel file ({e})."
        if {"DOCTORS", "REQUESTS"} <= names:
            return (f"'{os.path.basename(path)}' is the Roster Data file, not the timetable.\n\n"
                    "In the Timetable box, choose the big workbook with one tab per week "
                    "(e.g. '2311-291126'). Put Roster Data.xlsx in the Roster Data box.")
        return None

    def ok_paths(self):
        problem = self.timetable_problem(self.tt.get())
        if problem:
            messagebox.showwarning("Timetable", problem)
            return False
        if not self.rd.get():
            self.rd.set(os.path.join(os.path.dirname(self.tt.get()), "Roster Data.xlsx"))
        self.remember()
        return True

    # ---------------------------------------------------------------- actions
    def make(self):
        if self.busy or not self.ok_paths():
            return
        self.section("Make next week")
        self.run(lambda: self._make(overwrite=False), "Making the week")

    def _make(self, overwrite):
        generate(self.tt.get(), self.rd.get(), self.week.get().strip() or None,
                 log=lambda t: self.q.put(("log", t)), overwrite=overwrite)
        self.q.put(("log", "When the week looks right, click 'Publish online' to update the viewer website."))

    # ---------------------------------------------------------------- viewer website
    def site_dir(self):
        return os.path.join(os.path.dirname(os.path.abspath(self.tt.get())), "HO Roster viewer")

    def _build_site(self):
        log = lambda t: self.q.put(("log", t))
        rd = rdata.read_data_workbook(self.rd.get()) if os.path.exists(self.rd.get()) else None
        return build_site(self.tt.get(), self.site_dir(), rd, log=log)

    def preview_viewer(self):
        if self.busy or not self.ok_paths():
            return
        self.section("Preview viewer")

        def work():
            index = self._build_site()
            self.q.put(("log", f"Opening preview in your browser: {index}"))
            os.startfile(index)
        self.run(work, "Building the page")

    def publish_viewer(self):
        if self.busy or not self.ok_paths():
            return
        s = load_settings()
        if not s.get("netlify_token"):
            messagebox.showinfo("Website settings needed",
                                "Publishing needs a free Netlify account and an access token.\n\n"
                                "Click 'Website settings...' to set it up (one time only).")
            return
        self.section("Publish online")

        def work():
            folder = os.path.dirname(self._build_site())
            site_id = s.get("netlify_site_id")
            if not site_id:
                self.q.put(("log", "Creating the website on Netlify (first time only)..."))
                site_id, url = create_site(s["netlify_token"], s.get("netlify_name", ""))
                self.q.put(("remember", {"netlify_site_id": site_id, "netlify_url": url}))
            self.q.put(("log", "Uploading..."))
            url = deploy(folder, s["netlify_token"], site_id)
            self.q.put(("remember", {"netlify_url": url}))
            self.q.put(("log", f"Done. Viewer updated: {url}"))
            self.q.put(("log", "Share this link with the HOs - it always shows the latest published version."))
        self.run(work, "Publishing")

    def web_settings(self):
        s = load_settings()
        win = tk.Toplevel(self)
        win.title("Website settings")
        win.transient(self)
        win.resizable(False, False)
        f = ttk.Frame(win, padding=14)
        f.pack(fill="both", expand=True)
        steps = ("One-time setup (free):\n"
                 "1. Make an account at netlify.com (use a shared/department email if possible).\n"
                 "2. In Netlify: avatar (top right) > User settings > Applications >\n"
                 "    Personal access tokens > New access token. Copy it.\n"
                 "3. Paste it below and press Save. Then press 'Publish online'.")
        ttk.Label(f, text=steps, justify="left").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        tok = tk.StringVar(value=s.get("netlify_token", ""))
        name = tk.StringVar(value=s.get("netlify_name", ""))
        sid = tk.StringVar(value=s.get("netlify_site_id", ""))
        ttk.Label(f, text="Access token:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=tok, show="*", width=48).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(f, text="Website name (optional):").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=name, width=48).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(f, text="e.g. surgical-ho-roster  ->  surgical-ho-roster.netlify.app\n"
                          "(blank = Netlify picks a random name; only used the first time)",
                  foreground="#666").grid(row=3, column=1, sticky="w")
        ttk.Label(f, text="Site ID (filled in for you):").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=sid, width=48).grid(row=4, column=1, sticky="ew", pady=4)
        ttk.Label(f, text="Clear the Site ID to start a new website.", foreground="#666").grid(row=5, column=1, sticky="w")

        def save():
            n = name.get().strip().lower().replace(" ", "-")
            self.remember(netlify_token=tok.get().strip(), netlify_name=n,
                          netlify_site_id=sid.get().strip(),
                          **({} if sid.get().strip() else {"netlify_url": ""}))
            if not sid.get().strip():
                self.url.set("not published yet")
            win.destroy()
            self.log("Website settings saved.")
        b = ttk.Frame(f)
        b.grid(row=6, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(b, text="Cancel", command=win.destroy).pack(side="right", padx=4)
        ttk.Button(b, text="Save", command=save).pack(side="right", padx=4)
        win.grab_set()

    def copy_link(self):
        if self.url.get().startswith("http"):
            self.clipboard_clear()
            self.clipboard_append(self.url.get())
            self.log(f"Link copied: {self.url.get()}")
        else:
            self.log("No website yet - press 'Publish online' first.")

    def check(self):
        if self.busy or not self.ok_paths():
            return
        self.section("Check newest week")

        def chk():
            self.q.put(("log", "Reading timetable..."))
            wb = openpyxl.load_workbook(self.tt.get())
            weeks = load_weeks(wb, 3)
            if not weeks:
                raise RosterError("No week tabs found in the timetable - is the Timetable box pointing at the right file?")
            rd = rdata.read_data_workbook(self.rd.get())
            issues = check_week(weeks[0], weeks[1] if len(weeks) > 1 else None, rd)
            self.q.put(("log", f"Checked {weeks[0].ws.title}: {len(issues)} issue(s)"))
            for i in issues:
                bad = i.startswith(("SHORT", "NOT PAIRED")) or "should be PN" in i
                self.q.put(("log", ("  ! " if bad else "  - ") + i))
        self.run(chk, "Checking")


def selftest(tt, rd, out, logfile):
    """HO Roster.exe --selftest TIMETABLE DATA OUT LOG  (no window; for testing the build)"""
    with open(logfile, "w", encoding="utf-8") as f:
        try:
            generate(tt, rd, None, log=lambda t: print(t, file=f, flush=True), output_path=out)
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}", file=f)


def crisp_text():
    """Sharp text on high-resolution Windows screens."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--selftest":
        selftest(*sys.argv[2:])
    else:
        crisp_text()
        App().mainloop()
