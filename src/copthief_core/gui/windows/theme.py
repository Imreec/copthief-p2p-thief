"""Shared window theming (display-only; DRY seam for the two shells, rule 11).

Semantic states stay in the models ("green"/"gray"/"red"); this module maps them to
the theme's flat palette and centralizes fonts, chrome, and tile drawing. Every
operator-tunable knob comes from `game.toml [gui]`; the semantic hex map below is
fixed chrome, not a game value.
"""

from __future__ import annotations

import tkinter as tk

from copthief_core.shared.config_model import GuiSettings

# Semantic banner/marker colors (flat, modern shades — chrome, not config values).
SEMANTIC = {"green": "#16a34a", "gray": "#475569", "red": "#dc2626"}
ROLE_COLORS = {"police": "#38bdf8", "thief": "#f59e0b"}
BARRIER_FILL = "#020617"
BARRIER_EDGE = "#334155"


def semantic_hex(name: str) -> str:
    """A model's semantic color name as its theme hex (unknown names read as gray)."""
    return SEMANTIC.get(name, SEMANTIC["gray"])


def font(settings: GuiSettings, *, bold: bool = False, delta: int = 0) -> tuple[str, int, str]:
    """The theme font tuple, optionally emphasized (Input: knobs + bold flag + size
    delta relative to the configured base; Output: a Tk font spec)."""
    return (settings.font_family, settings.font_size + delta, "bold" if bold else "normal")


def banner(container: tk.Misc, settings: GuiSettings) -> tk.Label:
    """The full-width state banner (book fig. 9's YOUR TURN / LOCKED bar)."""
    label = tk.Label(
        container,
        text="",
        fg="white",
        bg=semantic_hex("gray"),
        font=font(settings, bold=True, delta=3),
        pady=10,
    )
    label.pack(fill="x")
    return label


def board_canvas(container: tk.Misc, settings: GuiSettings, side: int) -> tk.Canvas:
    """The board surface, flush with the dark chrome (no bevels, no focus ring)."""
    canvas = tk.Canvas(
        container,
        width=side,
        height=side,
        bg=settings.theme_bg,
        highlightthickness=0,
        bd=0,
    )
    canvas.pack(padx=12, pady=12)
    return canvas


def status_bar(container: tk.Misc, settings: GuiSettings) -> tk.Label:
    """The bottom status line (step counter, hints, cursor position)."""
    label = tk.Label(
        container,
        text="",
        anchor="w",
        bg=settings.theme_panel,
        fg=settings.theme_fg,
        font=font(settings, delta=-1),
        padx=12,
        pady=8,
    )
    label.pack(fill="x", side="bottom")
    return label


def chrome(container: tk.Tk | tk.Toplevel | tk.Frame, settings: GuiSettings) -> None:
    """Paint the window background so packed gaps read as dark chrome."""
    container.configure(bg=settings.theme_bg)


def tile(canvas: tk.Canvas, x: int, y: int, cell: int, fill: str, edge: str = "") -> None:
    """One board tile as a flat card: a small gap to the neighbors, no outline."""
    gap = max(1, cell // 16)
    canvas.create_rectangle(
        x + gap, y + gap, x + cell - gap, y + cell - gap, fill=fill, outline=edge, width=1
    )


def marker(
    canvas: tk.Canvas, x: int, y: int, cell: int, *, color: str, text: str, settings: GuiSettings
) -> None:
    """An agent marker: filled accent disc with the role letter."""
    inset = cell // 4
    canvas.create_oval(
        x + inset, y + inset, x + cell - inset, y + cell - inset, fill=color, outline=""
    )
    canvas.create_text(
        x + cell // 2,
        y + cell // 2,
        text=text,
        fill="#0b1220",
        font=font(settings, bold=True, delta=-1),
    )


def flat_button(container: tk.Misc, settings: GuiSettings, text: str, command: object) -> tk.Button:
    """A flat control button in the panel tone."""
    button = tk.Button(
        container,
        text=text,
        command=command,  # type: ignore[arg-type]
        relief="flat",
        bg=settings.theme_panel,
        fg=settings.theme_fg,
        activebackground=settings.accent,
        activeforeground=settings.theme_bg,
        font=font(settings, bold=True),
        padx=14,
        pady=4,
        bd=0,
    )
    button.pack(side="left", padx=4, pady=6)
    return button
