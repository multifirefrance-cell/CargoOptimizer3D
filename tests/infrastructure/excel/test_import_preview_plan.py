"""Pruebas de `import_preview.py`/`import_plan.py`: clasificación, filtros y duplicados (8.1)."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.excel.import_plan import build_import_plan
from cargo_optimizer.infrastructure.excel.import_preview import build_catalog_preview
from cargo_optimizer.infrastructure.excel.results import CatalogImportResult, RowError


def _unit(sku: str = "SKU-1", **overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": sku,
        "name": "Producto de prueba",
        "dimensions": Dimensions3D(50, 40, 30),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def test_build_catalog_preview_classifies_new_and_existing_units() -> None:
    new_unit = _unit("NEW-1")
    existing_in_catalog = _unit("EXISTING-1")
    result = CatalogImportResult(units=(new_unit, existing_in_catalog), errors=())

    def resolve_sku(sku: str) -> LoadUnit | None:
        return existing_in_catalog if sku == "EXISTING-1" else None

    preview = build_catalog_preview(result, resolve_sku, column_count=16)

    assert preview.new_units == (new_unit,)
    assert preview.existing_units == (existing_in_catalog,)
    assert preview.new_count == 1
    assert preview.existing_count == 1
    assert preview.row_count == 2
    assert preview.column_count == 16


def test_build_catalog_preview_splits_duplicate_and_invalid_errors() -> None:
    result = CatalogImportResult(
        units=(),
        errors=(
            RowError(row_number=2, message="SKU duplicado en la fila 2."),
            RowError(row_number=3, message="'Largo (cm)' no es un numero valido."),
        ),
    )

    preview = build_catalog_preview(result, lambda _sku: None, column_count=16)

    assert len(preview.duplicate_errors) == 1
    assert preview.duplicate_errors[0].row_number == 2
    assert len(preview.invalid_errors) == 1
    assert preview.invalid_errors[0].row_number == 3
    assert preview.duplicate_count == 1
    assert preview.invalid_count == 1
    assert preview.row_count == 2


def test_build_import_plan_default_mode_adds_new_and_updates_existing() -> None:
    new_unit = _unit("NEW-1")
    existing_unit = _unit("EXISTING-1")
    catalog_unit = _unit("EXISTING-1")
    result = CatalogImportResult(units=(new_unit, existing_unit), errors=())
    preview = build_catalog_preview(
        result, lambda sku: catalog_unit if sku == "EXISTING-1" else None, column_count=16
    )

    plan = build_import_plan(preview, lambda sku: catalog_unit if sku == "EXISTING-1" else None)

    assert plan.to_add == (new_unit,)
    assert len(plan.to_update) == 1
    assert plan.to_update[0].id == catalog_unit.id
    assert plan.ignored_skus == ()
    assert plan.total_count == 2


def test_build_import_plan_new_only_mode_skips_existing() -> None:
    new_unit = _unit("NEW-1")
    existing_unit = _unit("EXISTING-1")
    result = CatalogImportResult(units=(new_unit, existing_unit), errors=())
    preview = build_catalog_preview(
        result, lambda sku: existing_unit if sku == "EXISTING-1" else None, column_count=16
    )

    plan = build_import_plan(preview, lambda _sku: existing_unit, selection_mode="new_only")

    assert plan.to_add == (new_unit,)
    assert plan.to_update == ()


def test_build_import_plan_updated_only_mode_skips_new() -> None:
    new_unit = _unit("NEW-1")
    existing_unit = _unit("EXISTING-1")
    catalog_unit = _unit("EXISTING-1")
    result = CatalogImportResult(units=(new_unit, existing_unit), errors=())
    preview = build_catalog_preview(
        result, lambda sku: catalog_unit if sku == "EXISTING-1" else None, column_count=16
    )

    plan = build_import_plan(
        preview,
        lambda sku: catalog_unit if sku == "EXISTING-1" else None,
        selection_mode="updated_only",
    )

    assert plan.to_add == ()
    assert len(plan.to_update) == 1


def test_build_import_plan_selected_mode_filters_by_sku() -> None:
    unit_a = _unit("A")
    unit_b = _unit("B")
    result = CatalogImportResult(units=(unit_a, unit_b), errors=())
    preview = build_catalog_preview(result, lambda _sku: None, column_count=16)

    plan = build_import_plan(
        preview, lambda _sku: None, selection_mode="selected", selected_skus=frozenset({"A"})
    )

    assert plan.to_add == (unit_a,)


def test_build_import_plan_duplicate_resolution_update_reuses_existing_id() -> None:
    existing_unit = _unit("EXISTING-1")
    catalog_unit = _unit("EXISTING-1")
    result = CatalogImportResult(units=(existing_unit,), errors=())
    preview = build_catalog_preview(
        result, lambda sku: catalog_unit if sku == "EXISTING-1" else None, column_count=16
    )

    plan = build_import_plan(
        preview,
        lambda sku: catalog_unit if sku == "EXISTING-1" else None,
        duplicate_resolutions={"EXISTING-1": "update"},
    )

    assert len(plan.to_update) == 1
    assert plan.to_update[0].id == catalog_unit.id


def test_build_import_plan_duplicate_resolution_duplicate_creates_new_sku() -> None:
    existing_unit = _unit("EXISTING-1")
    catalog_unit = _unit("EXISTING-1")
    result = CatalogImportResult(units=(existing_unit,), errors=())
    preview = build_catalog_preview(
        result, lambda sku: catalog_unit if sku == "EXISTING-1" else None, column_count=16
    )

    plan = build_import_plan(
        preview,
        lambda sku: catalog_unit if sku == "EXISTING-1" else None,
        duplicate_resolutions={"EXISTING-1": "duplicate"},
    )

    assert plan.to_update == ()
    assert len(plan.to_add) == 1
    assert plan.to_add[0].sku == "EXISTING-1-DUP"
    assert plan.to_add[0].id != catalog_unit.id


def test_build_import_plan_duplicate_resolution_ignore_skips_row() -> None:
    existing_unit = _unit("EXISTING-1")
    catalog_unit = _unit("EXISTING-1")
    result = CatalogImportResult(units=(existing_unit,), errors=())
    preview = build_catalog_preview(
        result, lambda sku: catalog_unit if sku == "EXISTING-1" else None, column_count=16
    )

    plan = build_import_plan(
        preview,
        lambda sku: catalog_unit if sku == "EXISTING-1" else None,
        duplicate_resolutions={"EXISTING-1": "ignore"},
    )

    assert plan.to_add == ()
    assert plan.to_update == ()
    assert plan.ignored_skus == ("EXISTING-1",)


def test_build_import_plan_apply_to_all_default_resolution() -> None:
    unit_a = _unit("A")
    unit_b = _unit("B")
    catalog_a = _unit("A")
    catalog_b = _unit("B")
    result = CatalogImportResult(units=(unit_a, unit_b), errors=())

    def resolve(sku: str) -> LoadUnit | None:
        return {"A": catalog_a, "B": catalog_b}.get(sku)

    preview = build_catalog_preview(result, resolve, column_count=16)

    plan = build_import_plan(preview, resolve, default_duplicate_resolution="ignore")

    assert plan.to_add == ()
    assert plan.to_update == ()
    assert set(plan.ignored_skus) == {"A", "B"}
