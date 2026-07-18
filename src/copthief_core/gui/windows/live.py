"""Live window shell (PRD_gui_replay §4): Tkinter rendering of LiveViewModel frames.

Display-only by design — our agents are autonomous, so there is no move input to lock
(the book's §7.3.2 input-ignore rule is satisfied vacuously, stronger than required).
The window stays open after the game settles so the operator can take the App C
screenshot; closing it returns control to the sdk.
"""

from __future__ import annotations

import queue
import tkinter as tk
from dataclasses import dataclass
from typing import Any

from copthief_core.domain.board import Board
from copthief_core.gui.models.live import LiveViewModel, heat_color
from copthief_core.gui.windows import theme
from copthief_core.shared.config_model import GuiSettings


@dataclass
class LiveView:
    """One role's view wiring: its model, its event queue, and the render knobs."""

    model: LiveViewModel
    events: queue.Queue[dict[str, Any]]
    board: Board
    settings: GuiSettings
    title: str


class LiveWindow:
    """One Tk container rendering one LiveView (banner + heatmap grid + hint lines)."""

    def __init__(self, container: tk.Tk | tk.Toplevel, view: LiveView) -> None:
        self._view = view
        side = view.board.grid_size * view.settings.cell_px
        theme.chrome(container, view.settings)
        self._banner = theme.banner(container, view.settings)
        self._canvas = theme.board_canvas(container, view.settings, side)
        self._status = theme.status_bar(container, view.settings)

    def pump(self) -> None:
        """Drain queued events into the model, then redraw the current frame."""
        try:
            while True:
                self._view.model.apply(self._view.events.get_nowait())
        except queue.Empty:
            pass
        self._redraw()

    def _redraw(self) -> None:
        view, state = self._view, self._view.model.state()
        banner = state.outcome or state.banner if state.finished else state.banner
        self._banner.configure(text=banner, bg=theme.semantic_hex(state.banner_color))
        self._status.configure(
            text=(f"step {state.step}   heard: {state.hint_in!r}   said: {state.hint_out!r}")
        )
        cell, origin = view.settings.cell_px, view.board.axis_start_index
        self._canvas.delete("all")
        for row in range(view.board.grid_size):
            for col in range(view.board.grid_size):
                coord = (row + origin, col + origin)
                y = self._display_row(row) * cell
                x = col * cell
                if coord in state.barriers:
                    theme.tile(self._canvas, x, y, cell, theme.BARRIER_FILL, theme.BARRIER_EDGE)
                else:
                    fill = heat_color(
                        self._shade(state.belief, coord),
                        low=view.settings.heat_low,
                        high=view.settings.heat_high,
                    )
                    theme.tile(self._canvas, x, y, cell, fill)
                if coord == state.own_position:
                    theme.marker(
                        self._canvas,
                        x,
                        y,
                        cell,
                        color=view.settings.accent,
                        text=state.role[0].upper(),
                        settings=view.settings,
                    )

    def _display_row(self, row: int) -> int:
        """Canvas row for a board row under the signed axis contract."""
        if self._view.board.axis_origin_corner.startswith("bottom"):
            return self._view.board.grid_size - 1 - row
        return row

    @staticmethod
    def _shade(belief: dict[str, float], coord: tuple[int, int]) -> float:
        """Display contrast: probabilities scaled by the current maximum (ratio only —
        the objective numbers stay in the log; the view is qualitative, book fig. 9)."""
        if not belief:
            return 0.0
        top = max(belief.values())
        return belief.get(f"{coord[0]},{coord[1]}", 0.0) / top if top else 0.0


def run_live_views(views: list[LiveView], start_game: Any) -> None:  # noqa: ANN401 - thread target
    """Open one window per view, run the game in a daemon thread, and pump event
    queues until the operator closes the root window."""
    import threading

    root = tk.Tk()
    root.title(views[0].title)
    windows = [LiveWindow(root, views[0])]
    for view in views[1:]:
        top = tk.Toplevel(root)
        top.title(view.title)
        windows.append(LiveWindow(top, view))
    threading.Thread(target=start_game, daemon=True).start()

    def tick() -> None:
        for window in windows:
            window.pump()
        root.after(views[0].settings.refresh_ms, tick)

    tick()
    root.mainloop()
