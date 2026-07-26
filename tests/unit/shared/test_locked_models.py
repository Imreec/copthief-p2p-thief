"""The locked-model registry (ADR-0004 v2 item 5; kit SPEC §7).

Two properties matter here and nowhere else: our declared hash equals the KIT's pin
byte-for-byte (otherwise the lock is a private ritual, not an interop artifact), and a
registration that contradicts the signed constitution is refused before it can be
declared (otherwise we announce physics we do not play).
"""

import json
from pathlib import Path
from typing import Any

import pytest

from copthief_core.shared.config_model import PheromoneParams
from copthief_core.shared.locked_models import (
    SCENT_MODEL,
    LockedModelError,
    LockedModelRegistry,
    assert_agrees_with,
    load_locked_models,
    lock_decision,
)

REGISTRY = load_locked_models(Path("config/locked_models.json"))
KIT = json.loads((Path("tests/conformance/vectors/locked_model.json")).read_text(encoding="utf-8"))
SHIPPED = PheromoneParams(center_intensity=0.9, decay=0.1, grid_size=5, min_center_intensity=0.5)


def _kit_entry(name: str) -> dict[str, Any]:
    return next(r for r in KIT["registered"] if r["doc"]["name"] == name)


def test_the_declared_key_is_the_family_suffixed_form() -> None:
    assert LockedModelRegistry.declared_key(SCENT_MODEL) == "scent_model_sha256"


def test_an_unregistered_name_is_refused_not_silently_skipped() -> None:
    with pytest.raises(LockedModelError, match="no registration"):
        REGISTRY.doc(SCENT_MODEL, "gaussian_fitted_v9")


def test_a_registry_without_a_version_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "locked_models.json"
    path.write_text(json.dumps({"models": {}}), encoding="utf-8")
    with pytest.raises(LockedModelError, match="carries no version"):
        load_locked_models(path)


def test_both_shipped_scent_registrations_agree_with_the_signed_constitution() -> None:
    for name in ("subtractive_chebyshev_v1", "multiplicative_book_v1"):
        assert_agrees_with(REGISTRY.doc(SCENT_MODEL, name), SHIPPED)


def test_a_registration_that_contradicts_the_signed_terms_is_refused() -> None:
    """A changed pheromone value IS a different model; it must earn a new registration
    rather than ride the old hash."""
    drifted = PheromoneParams(
        center_intensity=0.9, decay=0.2, grid_size=5, min_center_intensity=0.5
    )
    with pytest.raises(LockedModelError, match="disagrees with the signed constitution"):
        assert_agrees_with(REGISTRY.doc(SCENT_MODEL, "subtractive_chebyshev_v1"), drifted)


def test_omission_is_never_refusal_in_either_direction() -> None:
    """A lock that fail-fasts on silence cannot start a game against the reference peer."""
    ours = REGISTRY.hash(SCENT_MODEL, "subtractive_chebyshev_v1")
    assert lock_decision(ours, None) == "play"
    assert lock_decision(None, ours) == "play"
    assert lock_decision(None, None) == "play"


def test_build_scent_model_constructs_the_named_physics_from_the_registry() -> None:
    """The builder is the ONE door from a registration to running physics (M7-14):
    same doc lookup, same signed-terms guard, same params — peer and referee paths
    can never construct the model two different ways."""
    from copthief_core.domain.scent_book import MultiplicativeBookV1
    from copthief_core.domain.scent_models import SubtractiveChebyshevV1
    from copthief_core.shared.locked_models import build_scent_model

    book = build_scent_model(REGISTRY, "multiplicative_book_v1", SHIPPED)
    assert isinstance(book, MultiplicativeBookV1)
    reference = build_scent_model(REGISTRY, "subtractive_chebyshev_v1", SHIPPED)
    assert isinstance(reference, SubtractiveChebyshevV1)


def test_build_scent_model_refuses_a_registration_the_constitution_contradicts() -> None:
    from copthief_core.shared.locked_models import build_scent_model

    drifted = PheromoneParams(
        center_intensity=0.9, decay=0.2, grid_size=5, min_center_intensity=0.5
    )
    with pytest.raises(LockedModelError, match="disagrees with the signed constitution"):
        build_scent_model(REGISTRY, "multiplicative_book_v1", drifted)
