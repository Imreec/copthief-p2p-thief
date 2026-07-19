"""M5-7 renders-clean pin: the committed results notebook really executed.

The DoD ("renders clean, committed with outputs") is checkable without running the
notebook: every code cell carries an execution_count and outputs from a real run,
and no output is an error. Role-blind (PR #29 rule): each repo commits its OWN
`notebooks/results_analysis.ipynb`; this mirrored pin reads whichever is local.
"""

from pathlib import Path

import nbformat

NOTEBOOK = Path("notebooks") / "results_analysis.ipynb"


def test_results_notebook_is_committed_and_fully_executed() -> None:
    assert NOTEBOOK.exists(), "notebooks/results_analysis.ipynb missing (M5-7 DoD)"
    nb = nbformat.read(NOTEBOOK, as_version=4)
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert code_cells
    for index, cell in enumerate(code_cells, start=1):
        assert cell.execution_count is not None, f"code cell {index} never executed"
        for output in cell.outputs:
            assert output.output_type != "error", f"code cell {index} errored: {output}"


def test_results_notebook_renders_its_figures() -> None:
    # "Committed with outputs" includes the CURVES: the GA fitness plot and the
    # sensitivity sweep must be rendered PNGs inside the committed notebook.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    images = sum(
        1
        for cell in nb.cells
        if cell.cell_type == "code"
        for output in cell.outputs
        if output.get("output_type") == "display_data" and "image/png" in output.get("data", {})
    )
    assert images >= 2, f"expected the GA + sensitivity figures rendered, found {images}"


def test_results_notebook_carries_the_analysis_sections() -> None:
    nb = nbformat.read(NOTEBOOK, as_version=4)
    text = "\n".join(c.source for c in nb.cells)
    for anchor in ("arena", "fitness", "sensitivity"):
        assert anchor in text.lower(), f"missing analysis section: {anchor}"
