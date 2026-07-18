"""Pruebas de `ProductCatalogRepository`: CRUD, búsqueda, archivado, duplicado."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.exceptions import (
    DuplicateCatalogSkuError,
    RecordNotFoundError,
)
from cargo_optimizer.infrastructure.database.repositories import ProductCatalogRepository


def _unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja de prueba",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def test_add_and_get_by_id(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit())
    fetched = repo.get_by_id(added.id)
    assert fetched == added


def test_pastel_or_manual_color_persists_and_is_restored(db_manager: DatabaseManager) -> None:
    """Fase OPT-17: un color pastel automático o elegido a mano es un `color_hex`
    normal -- persiste en el catálogo SQLite y se restaura igual que cualquier otro."""
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit(sku="BOX-COLOR", color_hex="#C9E4CA"))
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.color_hex == "#C9E4CA"


def test_get_by_sku_is_case_insensitive(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    repo.add(_unit(sku="BOX-1"))
    assert repo.get_by_sku("box-1") is not None
    assert repo.get_by_sku("BOX-1") is not None
    assert repo.get_by_sku("box-2") is None


def test_list_active_orders_by_sku(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    repo.add(_unit(sku="BOX-C"))
    repo.add(_unit(sku="BOX-A"))
    repo.add(_unit(sku="BOX-B"))
    skus = [unit.sku for unit in repo.list_active()]
    assert skus == ["BOX-A", "BOX-B", "BOX-C"]


def test_search_matches_sku_or_name_case_insensitive(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    repo.add(_unit(sku="BOX-1", name="Caja de electrodomésticos"))
    repo.add(_unit(sku="PALLET-1", name="Pallet de conservas"))
    assert [u.sku for u in repo.search("caja")] == ["BOX-1"]
    assert [u.sku for u in repo.search("PALLET")] == ["PALLET-1"]
    assert [u.sku for u in repo.search("box")] == ["BOX-1"]
    assert repo.search("inexistente") == ()


def test_update_changes_fields(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit(weight_kg=10.0))
    updated = repo.update(
        LoadUnit(
            id=added.id,
            sku=added.sku,
            name="Nuevo nombre",
            dimensions=added.dimensions,
            weight_kg=25.0,
        )
    )
    assert updated.name == "Nuevo nombre"
    assert updated.weight_kg == 25.0
    assert repo.get_by_id(added.id) == updated


def test_update_missing_record_raises(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    with pytest.raises(RecordNotFoundError):
        repo.update(_unit())


def test_add_duplicate_sku_raises(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    repo.add(_unit(sku="BOX-1"))
    with pytest.raises(DuplicateCatalogSkuError):
        repo.add(_unit(sku="box-1"))


def test_archive_then_restore(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit())
    assert repo.count_active() == 1

    repo.archive(added.id)
    assert repo.count_active() == 0
    assert repo.get_by_sku(added.sku) is None

    repo.restore(added.id)
    assert repo.count_active() == 1
    assert repo.get_by_sku(added.sku) is not None


def test_archived_sku_can_be_reused(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit(sku="BOX-1"))
    repo.archive(added.id)
    reused = repo.add(_unit(sku="BOX-1"))  # SKU único solo entre activos
    assert reused.sku == "BOX-1"


def test_duplicate_creates_independent_copy(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit(sku="BOX-1", name="Original"))
    copy = repo.duplicate(added.id, "BOX-2")
    assert copy.id != added.id
    assert copy.sku == "BOX-2"
    assert copy.name == "Original"
    assert repo.count_active() == 2


def test_duplicate_with_new_name(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit(sku="BOX-1", name="Original"))
    copy = repo.duplicate(added.id, "BOX-2", new_name="Copia con otro nombre")
    assert copy.name == "Copia con otro nombre"


def test_count_active_ignores_archived(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    a = repo.add(_unit(sku="BOX-A"))
    repo.add(_unit(sku="BOX-B"))
    repo.archive(a.id)
    assert repo.count_active() == 1


def test_round_trip_individual_extinguisher(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    unit = _unit(
        sku="EXT-1",
        dimensions=Dimensions3D(60.0, 20.0, 20.0),
        is_extinguisher=True,
        extinguisher_agent=ExtinguisherAgent.PQS,
        extinguisher_nominal_kg=5.0,
        allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
    )
    added = repo.add(unit)
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.is_extinguisher is True
    assert fetched.extinguisher_agent == ExtinguisherAgent.PQS
    assert fetched.extinguisher_nominal_kg == 5.0
    assert fetched.allowed_orientation_codes == (OrientationCode.LWH_XYZ,)


def test_round_trip_grouped_box_extinguisher(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    unit = _unit(
        sku="EXT-GROUP-1",
        package_type=PackageType.GROUPED_BOX,
        units_per_package=6,
        is_extinguisher=True,
        extinguisher_agent=ExtinguisherAgent.CO2,
        extinguisher_nominal_kg=2.0,
        max_stack_count=3,
    )
    added = repo.add(unit)
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.package_type == PackageType.GROUPED_BOX
    assert fetched.units_per_package == 6
    assert fetched.max_stack_count == 3


def test_existing_catalog_product_with_max_stack_count_one_keeps_it_at_one(
    db_manager: DatabaseManager,
) -> None:
    """Un producto de catálogo ya guardado con `max_stack_count=1` nunca se migra a 30."""
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit(sku="NOT-STACKABLE-1", max_stack_count=1))
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.max_stack_count == 1


def test_round_trip_preserves_all_orientation_codes(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit(allowed_orientation_codes=tuple(OrientationCode)))
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.allowed_orientation_codes == tuple(OrientationCode)


def test_round_trip_unicode_sku_name_and_notes(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(
        _unit(
            sku="CAJA-ÑOÑO-1",
            name="Cajón de piñas 中文 émigré",
            notes="Notas con acentos: áéíóú, ñ, 中文, emoji 📦.",
        )
    )
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.sku == "CAJA-ÑOÑO-1"
    assert fetched.name == "Cajón de piñas 中文 émigré"
    assert fetched.notes == "Notas con acentos: áéíóú, ñ, 中文, emoji 📦."


def test_round_trip_without_max_supported_weight(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    added = repo.add(_unit(max_supported_weight_kg=None))
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.max_supported_weight_kg is None


def test_apply_bulk_adds_and_updates_in_a_single_transaction(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    existing = repo.add(_unit(sku="EXISTING-1", weight_kg=10.0))

    repo.apply_bulk(
        to_add=(_unit(sku="NEW-1"), _unit(sku="NEW-2")),
        to_update=(
            LoadUnit(
                id=existing.id,
                sku=existing.sku,
                name="Actualizado",
                dimensions=existing.dimensions,
                weight_kg=99.0,
            ),
        ),
    )

    assert repo.get_by_sku("NEW-1") is not None
    assert repo.get_by_sku("NEW-2") is not None
    updated = repo.get_by_id(existing.id)
    assert updated is not None
    assert updated.name == "Actualizado"
    assert updated.weight_kg == 99.0


def test_apply_bulk_is_all_or_nothing_on_duplicate_sku(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)
    repo.add(_unit(sku="TAKEN"))

    with pytest.raises(DuplicateCatalogSkuError):
        repo.apply_bulk(to_add=(_unit(sku="NEW-VALID"), _unit(sku="TAKEN")))

    # Ninguna fila debe haberse escrito: ni siquiera la que era válida.
    assert repo.get_by_sku("NEW-VALID") is None
    assert repo.count_active() == 1


def test_apply_bulk_is_all_or_nothing_on_missing_update_target(
    db_manager: DatabaseManager,
) -> None:
    repo = ProductCatalogRepository(db_manager)

    with pytest.raises(RecordNotFoundError):
        repo.apply_bulk(to_add=(_unit(sku="SHOULD-NOT-EXIST"),), to_update=(_unit(sku="MISSING"),))

    assert repo.get_by_sku("SHOULD-NOT-EXIST") is None


def test_apply_bulk_with_no_changes_is_a_no_op(db_manager: DatabaseManager) -> None:
    repo = ProductCatalogRepository(db_manager)

    repo.apply_bulk()

    assert repo.count_active() == 0
