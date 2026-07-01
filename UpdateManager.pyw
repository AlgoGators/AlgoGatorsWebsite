import sys
import os
import shutil
import re
import json
import base64
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import requests

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    DND_FILES = None

if getattr(sys, "frozen", False):
    SITE_ROOT = Path(sys.executable).parent
else:
    SITE_ROOT = Path(__file__).parent

CONFIG_FILE   = SITE_ROOT / "_tool" / "config.json"
RESEARCH_HTML = SITE_ROOT / "research.html"
WHO_HTML      = SITE_ROOT / "who-we-are.html"
HEADSHOTS_DIR = SITE_ROOT / "Headshots"
RESEARCH_DIR  = SITE_ROOT / "Research"

DEPARTMENTS = [
    "Leadership",
    "Quantitative Research",
    "Quantitative Trading",
    "Quantitative Development / Engineering",
    "Investor Relations",
]

DEPT_KEY = {
    "Leadership":                             "LEADERSHIP",
    "Quantitative Research":                  "QR",
    "Quantitative Trading":                   "QT",
    "Quantitative Development / Engineering": "QDE",
    "Investor Relations":                     "IR",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ORANGE  = "#FF5C00"
BG      = "#0D0D0D"
SURFACE = "#161616"
BORDER  = "#282828"
TEXT    = "#FFFFFF"
MUTED   = "#5A5A5A"
HINT    = "#888888"
GREEN   = "#22C55E"
RED     = "#EF4444"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        if HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                pass

        self.title("AlgoGators — Update Manager")
        self.resizable(False, False)
        self.configure(fg_color=BG)

        self._pdf_path       = None
        self._img_path       = None
        self._last_msg       = "Updated website content"
        self._pdf_fname      = None
        self._headshot_fname = None

        # State carried across manage-screen refreshes
        self._manage_to_put    = []
        self._manage_to_delete = []
        self._manage_msg       = ""

        if self._config_valid():
            self._show_home()
        else:
            self._show_setup()

    # ── config helpers ───────────────────────────────────────────────────────
    def _load_config_safe(self):
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _config_valid(self):
        cfg = self._load_config_safe()
        return bool(cfg and cfg.get("pat") and cfg.get("owner") and cfg.get("repo"))

    # ── layout helpers ───────────────────────────────────────────────────────
    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _lbl(self, parent, text, size=12, bold=False, color=None, **kw):
        return ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont("Poppins", size, "bold" if bold else "normal"),
            text_color=color or TEXT, **kw,
        )

    def _entry(self, parent, placeholder=""):
        return ctk.CTkEntry(
            parent, height=42,
            font=ctk.CTkFont("Poppins", 13),
            fg_color="#0F0F0F", border_color=BORDER,
            placeholder_text=placeholder, corner_radius=6,
        )

    def _btn(self, parent, text, cmd, primary=True, **kw):
        return ctk.CTkButton(
            parent, text=text, height=48, command=cmd,
            font=ctk.CTkFont("Poppins", 14, "bold"),
            fg_color=ORANGE if primary else SURFACE,
            hover_color="#D94D00" if primary else "#1E1E1E",
            border_width=0 if primary else 1,
            border_color=BORDER, corner_radius=8, **kw,
        )

    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=10,
                            border_width=1, border_color=BORDER)

    def _back_btn(self):
        ctk.CTkButton(
            self, text="← Back", width=72, height=28,
            font=ctk.CTkFont("Poppins", 11),
            fg_color="transparent", hover_color=BORDER,
            text_color=MUTED, anchor="w",
            command=self._show_home,
        ).pack(anchor="w", padx=20, pady=(14, 0))

    def _drop_zone(self, parent, mode, store_fn):
        frame = ctk.CTkFrame(parent, fg_color="#0C0C0C", corner_radius=8,
                             border_width=1, border_color=BORDER, height=72)
        frame.pack_propagate(False)

        hint = ("Drop PDF here — or click to browse"
                if mode == "pdf" else "Drop image here — or click to browse")
        if not HAS_DND:
            hint = hint.replace("Drop", "Click to browse")

        lbl = self._lbl(frame, hint, size=12, color=HINT)
        lbl.pack(expand=True)

        def browse(_=None):
            ft = ([("PDF", "*.pdf")] if mode == "pdf"
                  else [("Image", "*.jpg *.jpeg *.png")])
            p = filedialog.askopenfilename(filetypes=ft)
            if p:
                store_fn(p)
                lbl.configure(text=f"✓  {os.path.basename(p)}", text_color=ORANGE)

        frame.bind("<Button-1>", browse)
        lbl.bind("<Button-1>", browse)

        if HAS_DND:
            try:
                frame.drop_target_register(DND_FILES)
                def on_drop(e):
                    p = e.data.strip().strip("{}")
                    store_fn(p)
                    lbl.configure(text=f"✓  {os.path.basename(p)}", text_color=ORANGE)
                frame.dnd_bind("<<Drop>>", on_drop)
            except Exception:
                pass

        return frame

    def _action_row(self, save_cmd, commit_label):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(14, 0))
        self._btn(row, "Save", save_cmd).pack(
            side="left", expand=True, fill="x", padx=(0, 6))
        self._btn(row, "Push to Internet",
                  lambda: self._push(commit_label), primary=False).pack(
            side="left", expand=True, fill="x")

    # ── setup screen ─────────────────────────────────────────────────────────
    def _show_setup(self, from_settings=False):
        self._clear()
        self.geometry("520x460")

        if from_settings:
            self._back_btn()

        top_pad = (10, 4) if from_settings else (36, 4)
        self._lbl(self, "GitHub Setup", 20, bold=True).pack(pady=top_pad)
        self._lbl(self, "Connect the tool to your GitHub repository", 12,
                  color=MUTED).pack(pady=(0, 20))

        card = self._card(self)
        card.pack(fill="x", padx=20)

        self._lbl(card, "PERSONAL ACCESS TOKEN", 10, color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(16, 2))
        self.cfg_pat = ctk.CTkEntry(
            card, height=42,
            font=ctk.CTkFont("Poppins", 13),
            fg_color="#0F0F0F", border_color=BORDER,
            placeholder_text="ghp_...",
            show="•", corner_radius=6,
        )
        self.cfg_pat.pack(fill="x", padx=16, pady=(0, 12))

        self._lbl(card, "GITHUB OWNER / ORG", 10, color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(0, 2))
        self.cfg_owner = self._entry(card, "e.g. AlgoGators")
        self.cfg_owner.pack(fill="x", padx=16, pady=(0, 12))

        self._lbl(card, "REPOSITORY NAME", 10, color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(0, 2))
        self.cfg_repo = self._entry(card, "e.g. algogators-website")
        self.cfg_repo.pack(fill="x", padx=16, pady=(0, 16))

        existing = self._load_config_safe()
        if existing:
            self.cfg_pat.insert(0, existing.get("pat", ""))
            self.cfg_owner.insert(0, existing.get("owner", ""))
            self.cfg_repo.insert(0, existing.get("repo", ""))

        self._btn(self, "Save & Continue", self._save_config).pack(
            fill="x", padx=20, pady=(16, 0))

        self.cfg_st = self._lbl(self, "", 12, color=MUTED)
        self.cfg_st.pack(pady=(8, 0))

    def _save_config(self):
        pat   = self.cfg_pat.get().strip()
        owner = self.cfg_owner.get().strip()
        repo  = self.cfg_repo.get().strip()

        if not pat or not owner or not repo:
            self.cfg_st.configure(text="⚠  All fields are required.", text_color=RED)
            return

        cfg = {"pat": pat, "owner": owner, "repo": repo}
        CONFIG_FILE.parent.mkdir(exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        self._show_home()

    # ── home ─────────────────────────────────────────────────────────────────
    def _show_home(self):
        self._clear()
        self.geometry("520x460")

        canvas = ctk.CTkCanvas(self, width=40, height=40, bg=BG,
                               highlightthickness=0)
        canvas.pack(pady=(36, 0))
        canvas.create_polygon(20, 2, 38, 36, 2, 36,
                               outline=ORANGE, fill="", width=2)

        self._lbl(self, "AlgoGators", 28, bold=True).pack(pady=(8, 3))
        self._lbl(self, "Website Update Manager", 12, color=MUTED).pack(pady=(0, 28))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack()

        self._btn(grid, "Add Research", self._show_research,
                  width=195).grid(row=0, column=0, padx=8, pady=6)
        self._btn(grid, "Add Headshot", self._show_headshot,
                  primary=False, width=195).grid(row=0, column=1, padx=8, pady=6)
        self._btn(grid, "Manage Research", self._show_manage_research,
                  primary=False, width=195).grid(row=1, column=0, padx=8, pady=6)
        self._btn(grid, "Manage Headshots", self._show_manage_headshots,
                  primary=False, width=195).grid(row=1, column=1, padx=8, pady=6)

        ctk.CTkButton(
            self, text="⚙  Settings", width=120, height=28,
            font=ctk.CTkFont("Poppins", 11),
            fg_color="transparent", hover_color=BORDER,
            text_color=MUTED,
            command=lambda: self._show_setup(from_settings=True),
        ).pack(pady=(18, 0))

    # ── add research form ─────────────────────────────────────────────────────
    def _show_research(self):
        self._clear()
        self.geometry("520x540")
        self._pdf_path = None
        self._back_btn()

        self._lbl(self, "Add Research Paper", 20, bold=True).pack(pady=(10, 16))

        card = self._card(self)
        card.pack(fill="x", padx=20)

        self._lbl(card, "TITLE", 10, color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(16, 2))
        self.r_title = self._entry(card, "Paper title…")
        self.r_title.pack(fill="x", padx=16, pady=(0, 12))

        self._lbl(card, "AUTHOR", 10, color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(0, 2))
        self.r_author = self._entry(card, "Author name…")
        self.r_author.pack(fill="x", padx=16, pady=(0, 12))

        self.r_cap = ctk.CTkCheckBox(
            card, text="Capstone paper",
            font=ctk.CTkFont("Poppins", 12), text_color=TEXT,
            checkmark_color="#000", fg_color=ORANGE, hover_color="#D94D00",
            border_color=BORDER,
        )
        self.r_cap.pack(anchor="w", padx=16, pady=(0, 12))

        self._drop_zone(card, "pdf",
                        lambda p: setattr(self, "_pdf_path", p)
                        ).pack(fill="x", padx=16, pady=(0, 16))

        self._action_row(self._save_research, "research")

        self.r_st = self._lbl(self, "", 12, color=MUTED)
        self.r_st.pack(pady=(10, 0))

    # ── add headshot form ─────────────────────────────────────────────────────
    def _show_headshot(self):
        self._clear()
        self.geometry("520x590")
        self._img_path = None
        self._back_btn()

        self._lbl(self, "Add Team Member", 20, bold=True).pack(pady=(10, 16))

        card = self._card(self)
        card.pack(fill="x", padx=20)

        self._lbl(card, "FULL NAME", 10, color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(16, 2))
        self.h_name = self._entry(card, "First Last")
        self.h_name.pack(fill="x", padx=16, pady=(0, 12))

        self._lbl(card, "TITLE / ROLE", 10, color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(0, 2))
        self.h_role = self._entry(card, "e.g. Senior Quant Researcher")
        self.h_role.pack(fill="x", padx=16, pady=(0, 12))

        self._lbl(card, "DEPARTMENT", 10, color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(0, 2))
        self.h_dept = ctk.CTkOptionMenu(
            card, values=DEPARTMENTS,
            font=ctk.CTkFont("Poppins", 13),
            fg_color="#0F0F0F", button_color=BORDER,
            button_hover_color=ORANGE, dropdown_fg_color=SURFACE,
            corner_radius=6,
        )
        self.h_dept.pack(fill="x", padx=16, pady=(0, 12))

        self._drop_zone(card, "image",
                        lambda p: setattr(self, "_img_path", p)
                        ).pack(fill="x", padx=16, pady=(0, 16))

        self._action_row(self._save_headshot, "headshot")

        self.h_st = self._lbl(self, "", 12, color=MUTED)
        self.h_st.pack(pady=(10, 0))

    # ── save (add) logic ──────────────────────────────────────────────────────
    def _save_research(self):
        title  = self.r_title.get().strip()
        author = self.r_author.get().strip()
        cap    = self.r_cap.get()

        if not title or not author:
            self.r_st.configure(text="⚠  Title and Author are required.", text_color=RED)
            return

        html  = RESEARCH_HTML.read_text(encoding="utf-8")
        count = len(re.findall(r'class="index-row"', html))
        num   = str(count + 1).zfill(3)

        href = "#"
        self._pdf_fname = None
        if self._pdf_path and Path(self._pdf_path).exists():
            fname = Path(self._pdf_path).name
            shutil.copy2(self._pdf_path, RESEARCH_DIR / fname)
            href  = f"Research/{fname}"
            self._pdf_fname = fname

        tag = '<span class="tag">Capstone</span>' if cap else ""
        new_row = (
            f'      <a class="index-row" data-reveal href="{href}" target="_blank" rel="noopener">\n'
            f'        <span class="no">{num}</span>\n'
            f'        <span class="ttl">{title}</span>\n'
            f'        <span class="meta"><span class="auth">{author}</span>{tag}</span>\n'
            f'        <span class="go">↗</span>\n'
            f'      </a>\n\n'
        )

        sentinel = "      <!-- INSERT_RESEARCH -->"
        if sentinel not in html:
            self.r_st.configure(
                text="⚠  INSERT_RESEARCH marker missing from research.html", text_color=RED)
            return

        html = html.replace(sentinel, new_row + sentinel)
        html = re.sub(r"Index — \d+ Papers", f"Index — {count + 1} Papers", html)
        RESEARCH_HTML.write_text(html, encoding="utf-8")

        self._last_msg = f"Add research: {title} by {author}"
        self.r_st.configure(text=f"✓  Paper {num} added. Click Push to go live.", text_color=GREEN)

    def _save_headshot(self):
        name = self.h_name.get().strip()
        role = self.h_role.get().strip()
        dept = self.h_dept.get()

        if not name or not role:
            self.h_st.configure(text="⚠  Name and Role are required.", text_color=RED)
            return
        if not self._img_path or not Path(self._img_path).exists():
            self.h_st.configure(text="⚠  Please provide a headshot image.", text_color=RED)
            return

        ext   = Path(self._img_path).suffix.lower()
        fname = name.replace(" ", "_") + ext
        shutil.copy2(self._img_path, HEADSHOTS_DIR / fname)
        self._headshot_fname = fname

        member = (
            f'      <div class="member" data-reveal>'
            f'<div class="ph"><img loading="lazy" src="Headshots/{fname}" alt="{name}"/></div>'
            f'<p class="nm">{name}</p>'
            f'<p class="rl">{role}</p></div>\n'
        )

        key      = DEPT_KEY[dept]
        sentinel = f"      <!-- INSERT_{key} -->"

        html = WHO_HTML.read_text(encoding="utf-8")
        if sentinel not in html:
            self.h_st.configure(
                text=f"⚠  {sentinel} missing from who-we-are.html", text_color=RED)
            return

        html = html.replace(sentinel, member + sentinel)
        html = re.sub(
            rf'(<h2>{re.escape(dept)}</h2><span class="count">/ )(\d+)(</span>)',
            lambda m: m.group(1) + str(int(m.group(2)) + 1).zfill(2) + m.group(3),
            html,
        )

        WHO_HTML.write_text(html, encoding="utf-8")
        self._last_msg = f"Add headshot: {name} ({dept})"
        self.h_st.configure(text=f"✓  {name} added. Click Push to go live.", text_color=GREEN)

    # ── parse helpers ─────────────────────────────────────────────────────────
    def _parse_members(self):
        """Return list of dicts per dept section: dept, name, role, src, html."""
        html = WHO_HTML.read_text(encoding="utf-8")
        member_re = re.compile(
            r'<div class="member"[^>]*>'
            r'<div class="ph"><img[^>]+src="([^"]+)"[^>]*/></div>'
            r'<p class="nm">([^<]+)</p>'
            r'<p class="rl">([^<]+)</p>'
            r'</div>'
        )
        members = []
        for dept, key in DEPT_KEY.items():
            sentinel = f"<!-- INSERT_{key} -->"
            if sentinel not in html:
                continue
            before = html.split(sentinel)[0]
            idx = before.rfind(f'<h2>{dept}</h2>')
            if idx == -1:
                continue
            section = before[idx:]
            for m in member_re.finditer(section):
                members.append({
                    "dept": dept,
                    "src":  m.group(1),
                    "name": m.group(2),
                    "role": m.group(3),
                    "html": m.group(0),
                })
        return members

    def _parse_papers(self):
        """Return list of dicts: num, title, author, href, capstone, html."""
        html = RESEARCH_HTML.read_text(encoding="utf-8")
        paper_re = re.compile(
            r'<a class="index-row"[^>]*href="([^"]*)"[^>]*>\s*'
            r'<span class="no">(\d+)</span>\s*'
            r'<span class="ttl">([^<]+)</span>\s*'
            r'<span class="meta"><span class="auth">([^<]+)</span>'
            r'([^<]*(?:<span[^>]*>[^<]*</span>)?[^<]*)</span>\s*'
            r'<span class="go">[^<]*</span>\s*'
            r'</a>',
            re.DOTALL,
        )
        papers = []
        for m in paper_re.finditer(html):
            papers.append({
                "num":      m.group(2),
                "title":    m.group(3).strip(),
                "author":   m.group(4).strip(),
                "href":     m.group(1),
                "capstone": bool(re.search(r'class="tag"', m.group(5))),
                "html":     m.group(0),
            })
        return papers

    # ── manage headshots screen ───────────────────────────────────────────────
    def _show_manage_headshots(self):
        self._clear()
        self.geometry("520x640")
        self._selected_member = None
        self._member_rows     = []
        self._back_btn()

        self._lbl(self, "Manage Team Members", 20, bold=True).pack(pady=(6, 2))
        self._lbl(self, "Click a member to select, then Remove to delete them", 12,
                  color=MUTED).pack(pady=(0, 10))

        members = self._parse_members()

        if not members:
            self._lbl(self, "No members found in who-we-are.html", 13,
                      color=MUTED).pack(pady=40)
            self.mh_st = self._lbl(self, "", 12, color=MUTED)
            self.mh_st.pack()
            return

        scroll = ctk.CTkScrollableFrame(
            self, fg_color=SURFACE, corner_radius=10,
            border_width=1, border_color=BORDER,
        )
        scroll.pack(fill="both", expand=True, padx=20)

        current_dept = None
        for i, member in enumerate(members):
            if member["dept"] != current_dept:
                current_dept = member["dept"]
                if i > 0:
                    ctk.CTkFrame(scroll, height=1, fg_color=BORDER).pack(
                        fill="x", padx=8, pady=(10, 0))
                self._lbl(scroll, current_dept.upper(), 9, color=ORANGE, anchor="w").pack(
                    fill="x", padx=12, pady=(6, 2))

            row = ctk.CTkFrame(scroll, fg_color="transparent", corner_radius=6,
                               cursor="hand2")
            row.pack(fill="x", padx=4, pady=2)

            name_lbl = self._lbl(row, member["name"], 13, bold=True, anchor="w")
            name_lbl.pack(side="left", padx=(10, 6))
            role_lbl = self._lbl(row, member["role"], 12, color=MUTED, anchor="w")
            role_lbl.pack(side="left")

            def make_select(r=row, m=member):
                def select(_=None):
                    for rw in self._member_rows:
                        rw.configure(fg_color="transparent")
                    r.configure(fg_color=BORDER)
                    self._selected_member = m
                    self._rm_member_btn.configure(state="normal")
                return select

            sel = make_select()
            row.bind("<Button-1>", sel)
            name_lbl.bind("<Button-1>", sel)
            role_lbl.bind("<Button-1>", sel)
            self._member_rows.append(row)

        action = ctk.CTkFrame(self, fg_color="transparent")
        action.pack(fill="x", padx=20, pady=(10, 0))

        self._rm_member_btn = ctk.CTkButton(
            action, text="Remove Selected", height=48, state="disabled",
            font=ctk.CTkFont("Poppins", 14, "bold"),
            fg_color=RED, hover_color="#C83535", corner_radius=8,
            command=self._confirm_remove_member,
        )
        self._rm_member_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self._btn(action, "Push to Internet", self._push_manage,
                  primary=False).pack(side="left", expand=True, fill="x")

        self.mh_st = self._lbl(self, "", 12, color=MUTED)
        self.mh_st.pack(pady=(8, 4))

    def _confirm_remove_member(self):
        m = self._selected_member
        if not m:
            return
        if messagebox.askyesno(
            "Confirm Remove",
            f"Remove {m['name']} from {m['dept']}?\n\n"
            "This updates who-we-are.html locally. "
            "Click Push to Internet to publish.",
        ):
            self._do_remove_member(m)

    def _do_remove_member(self, member):
        html = WHO_HTML.read_text(encoding="utf-8")

        if member["html"] not in html:
            self.mh_st.configure(
                text="⚠  Entry not found — may already be removed.", text_color=RED)
            return

        html = html.replace(member["html"], "", 1)

        dept = member["dept"]
        html = re.sub(
            rf'(<h2>{re.escape(dept)}</h2><span class="count">/ )(\d+)(</span>)',
            lambda m: m.group(1) + str(max(0, int(m.group(2)) - 1)).zfill(2) + m.group(3),
            html,
        )
        WHO_HTML.write_text(html, encoding="utf-8")

        to_delete = []
        src = member["src"]
        if src not in html:
            local_path = SITE_ROOT / Path(src.replace("\\", "/"))
            if local_path.exists():
                try:
                    local_path.unlink()
                except Exception:
                    pass
            to_delete = [src.replace("\\", "/")]

        self._manage_to_put    = [("who-we-are.html", WHO_HTML)]
        self._manage_to_delete = to_delete
        self._manage_msg       = f"Remove headshot: {member['name']} ({dept})"

        removed_name = member["name"]
        self._show_manage_headshots()
        self.mh_st.configure(
            text=f"✓  {removed_name} removed. Click Push to go live.",
            text_color=GREEN,
        )

    # ── manage research screen ────────────────────────────────────────────────
    def _show_manage_research(self):
        self._clear()
        self.geometry("520x640")
        self._selected_paper = None
        self._paper_rows     = []
        self._back_btn()

        self._lbl(self, "Manage Research Papers", 20, bold=True).pack(pady=(6, 2))
        self._lbl(self, "Click a paper to select, then Remove to delete it", 12,
                  color=MUTED).pack(pady=(0, 10))

        papers = self._parse_papers()

        if not papers:
            self._lbl(self, "No papers found in research.html", 13,
                      color=MUTED).pack(pady=40)
            self.mr_st = self._lbl(self, "", 12, color=MUTED)
            self.mr_st.pack()
            return

        scroll = ctk.CTkScrollableFrame(
            self, fg_color=SURFACE, corner_radius=10,
            border_width=1, border_color=BORDER,
        )
        scroll.pack(fill="both", expand=True, padx=20)

        for i, paper in enumerate(papers):
            if i > 0:
                ctk.CTkFrame(scroll, height=1, fg_color=BORDER).pack(
                    fill="x", padx=8, pady=(2, 0))

            row = ctk.CTkFrame(scroll, fg_color="transparent", corner_radius=6,
                               cursor="hand2")
            row.pack(fill="x", padx=4, pady=4)

            num_lbl = self._lbl(row, paper["num"], 11, color=ORANGE, anchor="w")
            num_lbl.pack(side="left", padx=(10, 10))

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(side="left", fill="x", expand=True, pady=4)

            title_lbl = self._lbl(inner, paper["title"], 12, bold=True, anchor="w")
            title_lbl.pack(fill="x")

            meta_text = paper["author"]
            if paper["capstone"]:
                meta_text += "  •  Capstone"
            meta_lbl = self._lbl(inner, meta_text, 11, color=MUTED, anchor="w")
            meta_lbl.pack(fill="x")

            def make_select(r=row, p=paper):
                def select(_=None):
                    for rw in self._paper_rows:
                        rw.configure(fg_color="transparent")
                    r.configure(fg_color=BORDER)
                    self._selected_paper = p
                    self._rm_paper_btn.configure(state="normal")
                return select

            sel = make_select()
            for widget in (row, num_lbl, inner, title_lbl, meta_lbl):
                widget.bind("<Button-1>", sel)
            self._paper_rows.append(row)

        action = ctk.CTkFrame(self, fg_color="transparent")
        action.pack(fill="x", padx=20, pady=(10, 0))

        self._rm_paper_btn = ctk.CTkButton(
            action, text="Remove Selected", height=48, state="disabled",
            font=ctk.CTkFont("Poppins", 14, "bold"),
            fg_color=RED, hover_color="#C83535", corner_radius=8,
            command=self._confirm_remove_paper,
        )
        self._rm_paper_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self._btn(action, "Push to Internet", self._push_manage,
                  primary=False).pack(side="left", expand=True, fill="x")

        self.mr_st = self._lbl(self, "", 12, color=MUTED)
        self.mr_st.pack(pady=(8, 4))

    def _confirm_remove_paper(self):
        p = self._selected_paper
        if not p:
            return
        title_short = p["title"][:60] + ("…" if len(p["title"]) > 60 else "")
        if messagebox.askyesno(
            "Confirm Remove",
            f'Remove paper #{p["num"]}:\n"{title_short}"\nby {p["author"]}?\n\n'
            "Remaining papers will be renumbered. "
            "Click Push to Internet to publish.",
        ):
            self._do_remove_paper(p)

    def _do_remove_paper(self, paper):
        html = RESEARCH_HTML.read_text(encoding="utf-8")

        if paper["html"] not in html:
            self.mr_st.configure(
                text="⚠  Entry not found — may already be removed.", text_color=RED)
            return

        html = html.replace(paper["html"], "", 1)

        # Renumber all remaining papers sequentially
        count = [0]
        def renumber(m):
            count[0] += 1
            return f'<span class="no">{str(count[0]).zfill(3)}</span>'
        html = re.sub(r'<span class="no">\d+</span>', renumber, html)

        html = re.sub(r"Index — \d+ Papers",
                      f"Index — {count[0]} Papers", html)
        RESEARCH_HTML.write_text(html, encoding="utf-8")

        to_delete = []
        href = paper.get("href", "#")
        if href and href != "#":
            local_pdf = SITE_ROOT / Path(href.replace("/", os.sep))
            if local_pdf.exists():
                try:
                    local_pdf.unlink()
                except Exception:
                    pass
            to_delete = [href]

        self._manage_to_put    = [("research.html", RESEARCH_HTML)]
        self._manage_to_delete = to_delete
        self._manage_msg       = f"Remove research: {paper['title']} by {paper['author']}"

        title_short = paper["title"][:40] + ("…" if len(paper["title"]) > 40 else "")
        self._show_manage_research()
        self.mr_st.configure(
            text=f"✓  \"{title_short}\" removed. Click Push to go live.",
            text_color=GREEN,
        )

    # ── GitHub push ───────────────────────────────────────────────────────────
    def _push_changes(self, to_put, to_delete, msg):
        cfg = self._load_config_safe()
        if not cfg or not cfg.get("pat") or not cfg.get("owner") or not cfg.get("repo"):
            messagebox.showerror(
                "Not configured",
                "GitHub settings are missing.\nOpen ⚙ Settings and fill in all fields.")
            return

        owner   = cfg["owner"]
        repo    = cfg["repo"]
        pat     = cfg["pat"]
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github+json",
        }
        base = f"https://api.github.com/repos/{owner}/{repo}/contents"

        def run():
            try:
                for api_path, local_path in to_put:
                    url = f"{base}/{api_path}"
                    r = requests.get(url, headers=headers)
                    if r.status_code not in (200, 404):
                        raise RuntimeError(
                            f"GET {api_path} → {r.status_code}: "
                            f"{r.json().get('message', r.text)}")
                    sha = r.json().get("sha") if r.status_code == 200 else None
                    b64 = base64.b64encode(Path(local_path).read_bytes()).decode()
                    payload = {"message": msg, "content": b64}
                    if sha:
                        payload["sha"] = sha
                    r = requests.put(url, headers=headers, json=payload)
                    if r.status_code not in (200, 201):
                        raise RuntimeError(
                            f"PUT {api_path} → {r.status_code}: "
                            f"{r.json().get('message', r.text)}")

                for api_path in to_delete:
                    url = f"{base}/{api_path}"
                    r = requests.get(url, headers=headers)
                    if r.status_code == 200:
                        sha = r.json().get("sha")
                        r = requests.delete(url, headers=headers,
                                            json={"message": msg, "sha": sha})
                        if r.status_code not in (200, 204):
                            raise RuntimeError(
                                f"DELETE {api_path} → {r.status_code}: "
                                f"{r.json().get('message', r.text)}")

                def done():
                    self._manage_to_put    = []
                    self._manage_to_delete = []
                    self._manage_msg       = ""
                    messagebox.showinfo("Pushed ✓", f"Live on GitHub!\n\n{msg}")
                self.after(0, done)

            except Exception as exc:
                err = str(exc)
                self.after(0, lambda e=err: messagebox.showerror("Push failed", e))

        threading.Thread(target=run, daemon=True).start()

    def _push(self, kind):
        to_put    = []
        to_delete = []

        if kind == "research":
            to_put.append(("research.html", RESEARCH_HTML))
            if self._pdf_fname and (RESEARCH_DIR / self._pdf_fname).exists():
                to_put.append((f"Research/{self._pdf_fname}",
                               RESEARCH_DIR / self._pdf_fname))
        elif kind == "headshot":
            to_put.append(("who-we-are.html", WHO_HTML))
            if self._headshot_fname and (HEADSHOTS_DIR / self._headshot_fname).exists():
                to_put.append((f"Headshots/{self._headshot_fname}",
                               HEADSHOTS_DIR / self._headshot_fname))

        self._push_changes(to_put, to_delete, self._last_msg)

    def _push_manage(self):
        if not self._manage_to_put:
            messagebox.showwarning(
                "Nothing to push",
                "Remove an entry first, then click Push to Internet.")
            return
        self._push_changes(
            self._manage_to_put,
            self._manage_to_delete,
            self._manage_msg,
        )


if __name__ == "__main__":
    app = App()
    app.mainloop()
