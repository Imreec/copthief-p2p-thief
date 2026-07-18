"""gui.windows — thin rendering shells (Tkinter/matplotlib), coverage-omitted (D3).

No logic lives here: every decision a shell renders comes from a tested model in
`gui.models`. Imported lazily by the sdk so keyless CI never touches a display stack.
"""

__all__ = ["__version__"]
__version__ = "1.00"
