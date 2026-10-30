"""
hermes_theme.py - a Tkinter design system reverse-engineered from the
Hermes Agent marketing site (hermes-agent.nousresearch.com).

Design tokens were extracted from the live site's CSS bundles, not guessed:
  --hermes-color-blue     #0000F2   (page ground)
  --hermes-color-white    #F2F2F2   (foreground / paper)
  --hpv2-ink              #1A1A1A   (ink on light panels)
  --hermes-color-neutral  #616191
  neon accents: yellow #F2F200, cyan #00F2F2, green #00F279, magenta #F200F2,
                orange #F27900, red #F20000, pink #F20079, indigo #7900F2
  --hpv2-hairline         color-mix(ink 20%) ; --hermes-outline-w .5px
  labels:  uppercase, letter-spacing .1em, monospace
  headings: condensed display face, tracking .03em, line-height ~.9
  geometry: square corners (border-radius 0 dominant), 1px/0.5px hard rules,
            large whitespace, no soft shadows

Font substitution on Windows:
  Rules Gothic Condensed -> Bahnschrift Condensed
  Aeonik Fono Pro / mono -> Consolas

Everything here is layout/composition only - no Hermes assets, logos or code
were copied; only the visual grammar (colour, rhythm, type, rules).
"""
import tkinter as tk
import tkinter.font as tkfont

# --------------------------------------------------------------------------- #
# palette
# --------------------------------------------------------------------------- #
# The site's flat #0000F2 field measures 28x the luminance of this floor; on a
# screen you sit in front of for an hour it glares. The brand blue survives as
# an accent (rules, focus, the figure's corona) and inside the engraved texture.
BLUE = "#05050F"          # ground  (was the site's #0000F2)
ACCENT = "#0000F2"        # --hermes-color-blue, accent only
BLUE_DEEP = "#0B0B1C"     # raised surface
PAPER = "#F2F2F2"         # --hermes-color-white
INK = "#141422"           # --hpv2-ink, dark enough for paper-button labels
NEUTRAL = "#8E8EA8"       # readable tertiary on the new floor
BRAND = "#0000F2"         # --hpv2-brand mapped onto the accent

YELLOW = "#F2F200"        # --hermes-color-yellow  (accent)
CYAN = "#00F2F2"          # --hermes-color-cyan
GREEN = "#00F279"         # --hermes-color-green
MAGENTA = "#F200F2"
ORANGE = "#F27900"
RED = "#F20000"
PINK = "#F20079"
NEON = "#79F200"
DANGER = "#FB2C36"

DISPLAY = "Bahnschrift Condensed"
DISPLAY_ALT = "Bahnschrift SemiCondensed"
MONO = "Consolas"
UI = "Segoe UI"


# --------------------------------------------------------------------------- #
# colour mixing (the site builds every tint with color-mix + layer percentages)
# --------------------------------------------------------------------------- #
def _rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(fg, bg, pct):
    """color-mix(in srgb, fg pct%, bg) - pct is fg share, 0..1."""
    fr, fg_, fb = _rgb(fg)
    br, bg_, bb = _rgb(bg)
    r = round(fr * pct + br * (1 - pct))
    g = round(fg_ * pct + bg_ * (1 - pct))
    b = round(fb * pct + bb * (1 - pct))
    return f"#{r:02x}{g:02x}{b:02x}"


# tints used across the UI, derived the same way the site derives its layers
# Text tints pinned to measured contrast against BLUE (#05050F):
#   fg 17.9:1 (AAA) | fg_60 8.9:1 | fg_50 6.5:1 | fg_40 4.9:1  -- all >= AA
# The old ramp mixed paper into the bright blue ground and produced 3.3:1 and
# 1.97:1 labels: fine on a marketing page, unreadable in a tool you work in.
ON_BLUE = {
    "fg": PAPER,
    "fg_60": "#B4B4C8",
    "fg_50": "#9C9CB0",
    "fg_40": "#8E8EA8",
    "fill_2": "#08081A",
    "fill_4": "#0B0B1C",
    "fill_6": "#0F0F22",
    "fill_10": "#14142D",
    "fill_14": "#1B1B38",
    "hair": "#2A2A44",
    "hair_strong": "#3C3C60",
}


# --------------------------------------------------------------------------- #
# typography helpers
# --------------------------------------------------------------------------- #
def track(text, gap=1):
    """letter-spacing: Tk has none, so labels are tracked manually.

    The site sets `.1em` on every uppercased mono label - this reproduces it.
    """
    text = text.upper()
    if gap <= 0:
        return text
    return (" " * gap).join(text)


class Fonts:
    """Cached font tuples; built once per interpreter."""

    def __init__(self, root):
        self._cache = {}
        fams = set(tkfont.families(root))
        self.display_family = DISPLAY if DISPLAY in fams else DISPLAY_ALT
        self.mono_family = MONO if MONO in fams else "Courier New"
        self.ui_family = UI if UI in fams else "Arial"

    def get(self, kind, size, weight="normal", slant="roman"):
        key = (kind, size, weight, slant)
        if key not in self._cache:
            fam = {"display": self.display_family,
                   "mono": self.mono_family,
                   "ui": self.ui_family}[kind]
            self._cache[key] = tkfont.Font(family=fam, size=size, weight=weight, slant=slant)
        return self._cache[key]

    # semantic roles, mapped to the site's type scale
    def hero(self, size=40):
        return self.get("display", size, "bold")

    def heading(self, size=18):
        return self.get("display", size, "bold")

    def label(self, size=8):
        return self.get("mono", size, "bold")

    def mono(self, size=10, weight="normal"):
        return self.get("mono", size, weight)

    def body(self, size=10):
        return self.get("mono", size, "normal")


# --------------------------------------------------------------------------- #
# widget factories
# --------------------------------------------------------------------------- #
class Theme:
    def __init__(self, root):
        self.root = root
        self.f = Fonts(root)
        self.ON = ON_BLUE       # tints of paper over the blue ground

    # -- primitives ---------------------------------------------------------
    def frame(self, parent, bg=None, **kw):
        kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 0)
        return tk.Frame(parent, bg=bg or BLUE, **kw)

    def rule(self, parent, color=None, thickness=1, **pack):
        """A 1px hard rule - the site's hairline, quantised to a device pixel."""
        r = tk.Frame(parent, bg=color or ON_BLUE["hair"], height=thickness, bd=0,
                     highlightthickness=0)
        if pack:
            r.pack(fill=pack.pop("fill", "x"), **pack)
        return r

    def vrule(self, parent, color=None, **pack):
        r = tk.Frame(parent, bg=color or ON_BLUE["hair"], width=1, bd=0,
                     highlightthickness=0)
        if pack:
            r.pack(side=pack.pop("side", "left"), fill=pack.pop("fill", "y"), **pack)
        return r

    def label_text(self, parent, text, size=8, color=None, tracked=True, gap=1,
                   bg=None, anchor="w", **pack):
        lbl = tk.Label(
            parent,
            text=track(text, gap) if tracked else text,
            font=self.f.label(size),
            fg=color or ON_BLUE["fg_60"],
            bg=bg or BLUE,
            bd=0,
            highlightthickness=0,
            anchor=anchor,
        )
        if pack:
            lbl.pack(**pack)
        return lbl

    def value(self, parent, text, size=11, color=None, bg=None, anchor="w", **pack):
        lbl = tk.Label(parent, text=text, font=self.f.mono(size), fg=color or PAPER,
                       bg=bg or BLUE, bd=0, highlightthickness=0, anchor=anchor)
        if pack:
            lbl.pack(**pack)
        return lbl

    def eyebrow(self, parent, index, text, bg=None, **pack):
        """'01 / SERIAL' - the numbered section marker the site uses on features."""
        row = tk.Frame(parent, bg=bg or BLUE, bd=0, highlightthickness=0)
        if pack:
            row.pack(**pack)
        tk.Label(row, text=track(index, 1), font=self.f.label(8), fg=YELLOW,
                 bg=bg or BLUE, bd=0, highlightthickness=0).pack(side="left")
        tk.Frame(row, bg=YELLOW, width=14, height=1, bd=0,
                 highlightthickness=0).pack(side="left", padx=8, pady=(1, 0))
        tk.Label(row, text=track(text, 1), font=self.f.label(8),
                 fg=ON_BLUE["fg_60"], bg=bg or BLUE, bd=0,
                 highlightthickness=0).pack(side="left")
        return row

    # -- controls -----------------------------------------------------------
    def button(self, parent, text, command=None, kind="solid", width=None, bg=None):
        """Square, hard-edged button. kind: solid (paper on blue) | ghost (rule).

        Hover inverts the fill like the site's pressed state (color-mix 10%).
        """
        base_bg = bg or BLUE
        if kind == "solid":
            fill, fg = PAPER, BLUE
            hover, hover_fg = mix(PAPER, YELLOW, 0.82), BLUE
        else:
            fill, fg = base_bg, PAPER
            hover, hover_fg = ON_BLUE["fill_14"], PAPER

        lbl = tk.Label(parent, text=track(text, 1), font=self.f.label(9),
                       fg=fg, bg=fill, bd=0, padx=16, pady=9,
                       highlightthickness=1 if kind == "ghost" else 0,
                       highlightbackground=ON_BLUE["hair_strong"],
                       cursor="hand2", anchor="center")
        if width:
            lbl.configure(width=width)

        def enter(_):
            lbl.configure(bg=hover, fg=hover_fg)

        def leave(_):
            lbl.configure(bg=fill, fg=fg)

        lbl.bind("<Enter>", enter)
        lbl.bind("<Leave>", leave)
        if command:
            lbl.bind("<Button-1>", lambda e: command())
        return lbl

    def field(self, parent, textvariable=None, text=None, width=None, height=32):
        """Inset text field: 1px rule, 6% paper wash, no rounding."""
        wrap = tk.Frame(parent, bg=ON_BLUE["fill_6"], bd=0, highlightthickness=1,
                        highlightbackground=ON_BLUE["hair"], height=height)
        wrap.pack_propagate(False)
        inner_bg = ON_BLUE["fill_6"]
        if textvariable is not None:
            ent = tk.Entry(wrap, textvariable=textvariable, font=self.f.mono(10),
                           bg=inner_bg, fg=PAPER, insertbackground=YELLOW,
                           relief="flat", bd=0, highlightthickness=0)
        else:
            ent = tk.Entry(wrap, font=self.f.mono(10), bg=inner_bg, fg=PAPER,
                           insertbackground=YELLOW, relief="flat", bd=0,
                           highlightthickness=0)
            if text:
                ent.insert(0, text)
        ent.pack(fill="both", expand=True, padx=10, pady=0)
        wrap.ent = ent
        return wrap

    def card(self, parent, fill=None, rule=None):
        """A panel: 1px rule on a 4% wash."""
        return tk.Frame(parent, bg=fill or ON_BLUE["fill_4"], bd=0,
                        highlightthickness=1,
                        highlightbackground=rule or ON_BLUE["hair"])

    def dot(self, parent, color=YELLOW, size=7, bg=None):
        c = tk.Canvas(parent, width=size, height=size, bg=bg or BLUE, bd=0,
                      highlightthickness=0)
        c.create_oval(0, 0, size - 1, size - 1, fill=color, outline="")
        return c

    def kv(self, parent, key, value, value_color=None, bg=None):
        """KEY / VALUE stack - the site's mono metadata blocks."""
        row = tk.Frame(parent, bg=bg or BLUE, bd=0, highlightthickness=0)
        tk.Label(row, text=track(key, 1), font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=bg or BLUE, anchor="w",
                 bd=0, highlightthickness=0).pack(fill="x")
        tk.Label(row, text=value, font=self.f.mono(10), fg=value_color or PAPER,
                 bg=bg or BLUE, anchor="w", bd=0,
                 highlightthickness=0).pack(fill="x", pady=(2, 0))
        return row

    def kv_var(self, parent, key, variable, value_color=None, bg=None):
        """Same as kv() but bound to a StringVar so it can update live."""
        row = tk.Frame(parent, bg=bg or BLUE, bd=0, highlightthickness=0)
        tk.Label(row, text=track(key, 1), font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=bg or BLUE, anchor="w",
                 bd=0, highlightthickness=0).pack(fill="x")
        tk.Label(row, textvariable=variable, font=self.f.mono(10),
                 fg=value_color or PAPER, bg=bg or BLUE, anchor="w", bd=0,
                 highlightthickness=0).pack(fill="x", pady=(2, 0))
        return row

    # -- composite controls -------------------------------------------------
    def dropdown(self, parent, variable, options_fn, bg=None, on_open=None):
        """Square pop-up selector. options_fn() -> [(label, value), ...].

        Tk has no styled combobox that survives a dark palette, so this is a
        clickable field plus a tk.Menu popup painted to match.
        """
        bg = bg or BLUE
        wrap = tk.Frame(parent, bg=ON_BLUE["fill_6"], bd=0, highlightthickness=1,
                        highlightbackground=ON_BLUE["hair"], cursor="hand2")
        lbl = tk.Label(wrap, textvariable=variable, font=self.f.mono(10),
                       fg=PAPER, bg=ON_BLUE["fill_6"], anchor="w", bd=0,
                       highlightthickness=0, padx=10, pady=6)
        lbl.pack(side="left", fill="x", expand=True)
        arrow = tk.Label(wrap, text="▾", font=self.f.mono(9),
                         fg=ON_BLUE["fg_60"], bg=ON_BLUE["fill_6"], bd=0,
                         highlightthickness=0, padx=8)
        arrow.pack(side="right")

        def open_menu(_=None):
            if on_open:
                on_open()
            items = options_fn() or [("(none)", "")]
            m = tk.Menu(self.root, tearoff=0, bg=INK, fg=PAPER,
                        activebackground=YELLOW, activeforeground=BLUE,
                        bd=0, relief="flat", font=self.f.mono(10))
            for label, value in items:
                m.add_command(label=label,
                              command=lambda v=value: variable.set(v))
            try:
                m.tk_popup(wrap.winfo_rootx(), wrap.winfo_rooty() + wrap.winfo_height())
            finally:
                m.grab_release()

        for w in (wrap, lbl, arrow):
            w.bind("<Button-1>", open_menu)
            w.bind("<Enter>", lambda e: (wrap.configure(highlightbackground=ON_BLUE["hair_strong"]),
                                         lbl.configure(bg=ON_BLUE["fill_10"]),
                                         arrow.configure(bg=ON_BLUE["fill_10"])))
            w.bind("<Leave>", lambda e: (wrap.configure(highlightbackground=ON_BLUE["hair"]),
                                         lbl.configure(bg=ON_BLUE["fill_6"]),
                                         arrow.configure(bg=ON_BLUE["fill_6"])))
        wrap.open_menu = open_menu
        return wrap

    def checkbox(self, parent, text, variable, bg=None):
        """Square tick box; ticks yellow, no rounded checkmark glyph."""
        bg = bg or BLUE
        row = tk.Frame(parent, bg=bg, bd=0, highlightthickness=0, cursor="hand2")

        def paint():
            on = bool(variable.get())
            box.configure(bg=YELLOW if on else ON_BLUE["fill_6"],
                          highlightbackground=YELLOW if on else ON_BLUE["hair_strong"])
            mark.configure(text="✕" if on else "", fg=BLUE, bg=YELLOW if on else ON_BLUE["fill_6"])

        def toggle(_=None):
            variable.set(not variable.get())
            paint()

        box = tk.Frame(row, width=13, height=13, bd=0, highlightthickness=1,
                       highlightbackground=ON_BLUE["hair_strong"],
                       bg=ON_BLUE["fill_6"])
        box.pack(side="left")
        box.pack_propagate(False)
        mark = tk.Label(box, text="", font=self.f.label(7), bd=0, highlightthickness=0,
                        bg=ON_BLUE["fill_6"], fg=BLUE)
        mark.pack(expand=True)
        lbl = tk.Label(row, text=text, font=self.f.mono(9), fg=ON_BLUE["fg_60"],
                       bg=bg, bd=0, highlightthickness=0, cursor="hand2")
        lbl.pack(side="left", padx=(8, 0))

        for w in (row, box, mark, lbl):
            w.bind("<Button-1>", toggle)
        row.paint = paint
        paint()
        return row

    def status_row(self, parent, variable, dot_canvas=None):
        """A dot + tracked label, used for the link indicator."""
        row = tk.Frame(parent, bg=BLUE, bd=0, highlightthickness=0)
        self.dot(row, YELLOW).pack(side="left")
        tk.Label(row, textvariable=variable, font=self.f.label(8), fg=PAPER,
                 bg=BLUE, bd=0, highlightthickness=0).pack(side="left", padx=(8, 0))
        return row


class ScrollArea(tk.Frame):
    """Vertically scrollable container styled for the dark-blue ground.

    Tk's own scrollbar is used but stripped down; the wheel is bound to every
    descendant because Tk does not propagate wheel events from children.
    """

    def __init__(self, parent, theme, bg=None):
        bg = bg or BLUE
        super().__init__(parent, bg=bg, bd=0, highlightthickness=0)
        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0,
                                width=1, height=1)
        self.bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                width=10, bg=bg, troughcolor=theme.ON["fill_6"],
                                activebackground=YELLOW, bd=0,
                                highlightthickness=0, relief="flat",
                                elementborderwidth=0)
        self.inner = tk.Frame(self.canvas, bg=bg, bd=0, highlightthickness=0)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.bind_wheel(self.canvas)
        self.bind_wheel(self.inner)

    def _on_inner(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)

    def bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self._wheel)
        for child in widget.winfo_children():
            self.bind_wheel(child)

    def _wheel(self, e):
        first, last = self.canvas.yview()
        if first <= 0.0 and last >= 1.0:
            return               # nothing to scroll
        self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()

