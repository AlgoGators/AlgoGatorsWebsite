import sys
import os
import shutil
import re
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

# Try to load tkinterdnd2 for native drag-and-drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    DND_FILES = None

# When frozen by PyInstaller the exe lives next to the site files
if getattr(sys, "frozen", False):
    SITE_ROOT = Path(sys.executable).parent
else:
    SITE_ROOT = Path(__file__).parent

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
    "Leadership":                           "LEADERSHIP",
    "Quantitative Research":                "QR",
    "Quantitative Trading":                 "QT",
    "Quantitative Development / Engineering": "QDE",
    "Investor Relations":                   "IR",
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
        self._pdf_path  = None
        self._img_path  = None
        self._last_msg  = "Updated website content"
        self._show_home()

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

    # ── home ─────────────────────────────────────────────────────────────────
    def _show_home(self):
        self._clear()
        self.geometry("520x370")

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
        if self._pdf_path and Path(self._pdf_path).exists():
            fname = Path(self._pdf_path).name
            shutil.copy2(self._pdf_path, RESEARCH_DIR / fname)
            href  = f"Research/{fname}"

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

    # ── git push ──────────────────────────────────────────────────────────────
    def _push(self, kind):
        msg = self._last_msg

        def run():
            try:
                subprocess.run(
                    ["git", "-C", str(SITE_ROOT), "add", "."],
                    check=True, capture_output=True,
                )
                commit = subprocess.run(
                    ["git", "-C", str(SITE_ROOT), "commit", "-m", msg],
                    capture_output=True, text=True,
                )
                if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
                    err = commit.stderr or commit.stdout
                    self.after(0, lambda: messagebox.showerror("Commit failed", err))
                    return

                push = subprocess.run(
                    ["git", "-C", str(SITE_ROOT), "push"],
                    capture_output=True, text=True,
                )
                if push.returncode == 0:
                    self.after(0, lambda: messagebox.showinfo(
                        "Pushed ✓", f"Live on GitHub!\n\n{msg}"))
                else:
                    self.after(0, lambda: messagebox.showerror("Push failed", push.stderr))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Error", str(exc)))

        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
