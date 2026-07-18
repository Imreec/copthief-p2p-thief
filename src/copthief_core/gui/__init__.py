"""copthief_core.gui — live view, replay viewer, belief-vs-truth overlay (PLAN §3/§9).

`models/` holds ALL logic — pure folds over the schema-v1.1 event stream, fully tested
and coverage-counted. `windows/` holds the thin Tkinter/matplotlib rendering shells,
coverage-omitted because keyless CI opens no windows (PRD_gui_replay decision D3).
"""

__all__ = ["__version__"]
__version__ = "1.00"
