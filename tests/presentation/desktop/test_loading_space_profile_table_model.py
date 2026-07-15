"""Pruebas de `LoadingSpaceProfileTableModel` (fase 7.1)."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.infrastructure.database.repositories import LoadingSpaceProfileEntry
from cargo_optimizer.presentation.desktop.models.loading_space_profile_table_model import (
    COL_NAME,
    COL_ORIGIN,
    LoadingSpaceProfileTableModel,
)


def _entry(**overrides: object) -> LoadingSpaceProfileEntry:
    space_kwargs: dict[str, object] = {
        "name": "Bodega",
        "category": LoadingSpaceCategory.WAREHOUSE,
        "internal_dimensions": Dimensions3D(500.0, 300.0, 300.0),
    }
    is_active = overrides.pop("is_active", True)
    is_builtin = overrides.pop("is_builtin", False)
    space_kwargs.update(overrides)
    space = LoadingSpace(**space_kwargs)  # type: ignore[arg-type]
    return LoadingSpaceProfileEntry(
        loading_space=space, is_active=bool(is_active), is_builtin=bool(is_builtin)
    )


def test_starts_empty(qapp: object) -> None:
    model = LoadingSpaceProfileTableModel()
    assert model.rowCount() == 0


def test_set_entries_populates_rows(qapp: object) -> None:
    model = LoadingSpaceProfileTableModel()
    model.set_entries([_entry(name="A"), _entry(name="B")])
    assert model.rowCount() == 2


def test_origin_column_distinguishes_builtin_custom_and_archived(qapp: object) -> None:
    from PySide6.QtCore import Qt

    model = LoadingSpaceProfileTableModel()
    model.set_entries(
        [
            _entry(name="Integrado", is_builtin=True),
            _entry(name="Personalizado", is_builtin=False),
            _entry(name="Archivado", is_active=False),
        ]
    )
    assert model.data(model.index(0, COL_ORIGIN), Qt.ItemDataRole.DisplayRole) == "Integrado"
    assert model.data(model.index(1, COL_ORIGIN), Qt.ItemDataRole.DisplayRole) == "Personalizado"
    assert model.data(model.index(2, COL_ORIGIN), Qt.ItemDataRole.DisplayRole) == "Archivado"


def test_name_column(qapp: object) -> None:
    from PySide6.QtCore import Qt

    model = LoadingSpaceProfileTableModel()
    model.set_entries([_entry(name="Camión rígido")])
    assert model.data(model.index(0, COL_NAME), Qt.ItemDataRole.DisplayRole) == "Camión rígido"
