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

# Try to load tkinterdnd2 for native drag-and-drop
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

# ── theme constants ─────────────────────────────────────────────────────────
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

        # Patch in tkinterdnd2 support on the existing Tk instance
        if HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                pass

        self.title("AlgoGators — Update Tool")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self._pdf_path       = None
        self._img_path       = None
        self._last_msg       = "Updated website content"
        self._pdf_fname      = None
        self._headshot_fname = None

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

    # ── setup / config screen ────────────────────────────────────────────────
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

        # Pre-fill existing values if present
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
        self.geometry("520x400")

        # Triangle logo
        canvas = ctk.CTkCanvas(self, width=40, height=40, bg=BG,
                               highlightthickness=0)
        canvas.pack(pady=(44, 0))
        canvas.create_polygon(20, 2, 38, 36, 2, 36,
                               outline=ORANGE, fill="", width=2)

        self._lbl(self, "AlgoGators", 28, bold=True).pack(pady=(8, 3))
        self._lbl(self, "Website Update Tool", 12, color=MUTED).pack(pady=(0, 36))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        self._btn(row, "Add Research", self._show_research,
                  width=195).grid(row=0, column=0, padx=8)
        self._btn(row, "Add Headshot", self._show_headshot,
                  primary=False, width=195).grid(row=0, column=1, padx=8)

        ctk.CTkButton(
            self, text="⚙  Settings", width=120, height=28,
            font=ctk.CTkFont("Poppins", 11),
            fg_color="transparent", hover_color=BORDER,
            text_color=MUTED,
            command=lambda: self._show_setup(from_settings=True),
        ).pack(pady=(18, 0))

    # ── research form ─────────────────────────────────────────────────────────
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

    # ── headshot form ─────────────────────────────────────────────────────────
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

    # ── save logic ────────────────────────────────────────────────────────────
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

        # bump dept count  e.g.  / 07  →  / 08
        html = re.sub(
            rf'(<h2>{re.escape(dept)}</h2><span class="count">/ )(\d+)(</span>)',
            lambda m: m.group(1) + str(int(m.group(2)) + 1).zfill(2) + m.group(3),
            html,
        )

        WHO_HTML.write_text(html, encoding="utf-8")
        self._last_msg = f"Add headshot: {name} ({dept})"
        self.h_st.configure(text=f"✓  {name} added. Click Push to go live.", text_color=GREEN)

    # ── GitHub API push ───────────────────────────────────────────────────────
    def _push(self, kind):
        cfg = self._load_config_safe()
        if not cfg or not cfg.get("pat") or not cfg.get("owner") or not cfg.get("repo"):
            messagebox.showerror(
                "Not configured",
                "GitHub settings are missing.\nOpen ⚙ Settings and fill in all fields.")
            return

        msg     = self._last_msg
        owner   = cfg["owner"]
        repo    = cfg["repo"]
        pat     = cfg["pat"]
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github+json",
        }

        def push_file(api_path, local_path):
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{api_path}"

            r = requests.get(url, headers=headers)
            if r.status_code not in (200, 404):
                try:
                    err = r.json().get("message", r.text)
                except Exception:
                    err = r.text
                raise RuntimeError(f"GET {api_path} returned {r.status_code}:\n{err}")

            sha = r.json().get("sha") if r.status_code == 200 else None

            b64 = base64.b64encode(Path(local_path).read_bytes()).decode()
            payload = {"message": msg, "content": b64}
            if sha:
                payload["sha"] = sha

            r = requests.put(url, headers=headers, json=payload)
            if r.status_code not in (200, 201):
                try:
                    err = r.json().get("message", r.text)
                except Exception:
                    err = r.text
                raise RuntimeError(f"PUT {api_path} returned {r.status_code}:\n{err}")

        def run():
            try:
                if kind == "research":
                    push_file("research.html", RESEARCH_HTML)
                    if self._pdf_fname and (RESEARCH_DIR / self._pdf_fname).exists():
                        push_file(f"Research/{self._pdf_fname}",
                                  RESEARCH_DIR / self._pdf_fname)
                elif kind == "headshot":
                    push_file("who-we-are.html", WHO_HTML)
                    if self._headshot_fname and (HEADSHOTS_DIR / self._headshot_fname).exists():
                        push_file(f"Headshots/{self._headshot_fname}",
                                  HEADSHOTS_DIR / self._headshot_fname)

                self.after(0, lambda: messagebox.showinfo(
                    "Pushed ✓", f"Live on GitHub!\n\n{msg}"))
            except Exception as exc:
                err = str(exc)
                self.after(0, lambda e=err: messagebox.showerror("Push failed", e))

        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
