"""Repositorios del catálogo de productos, perfiles de espacio e historial.

Cada método abre y cierra su propia sesión corta
(`DatabaseManager.session_scope`) — nunca hay una transacción abierta
mientras un diálogo espera al usuario, y nunca se comparte una
`Session` entre hilos. La conversión ORM <-> `domain` es siempre
explícita, campo a campo (`_load_unit_to_orm`/`_orm_to_load_unit`,
etc.) — nunca `__dict__` ni un mapeo automático. Ningún objeto de
SQLAlchemy sale de este módulo: los métodos públicos siempre devuelven
entidades de `domain` o los DTO de historial definidos aquí mismo.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import (
    DoorPosition,
    ExtinguisherAgent,
    LoadingSpaceCategory,
    OrientationCode,
    PackageType,
)
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.exceptions import (
    DuplicateCatalogSkuError,
    DuplicateImportMappingProfileError,
    DuplicateLoadingSpaceProfileError,
    RecordNotFoundError,
    RepositoryError,
)
from cargo_optimizer.infrastructure.database.orm_models import (
    ImportMappingProfileORM,
    LoadingSpaceProfileORM,
    PackingRunHistoryORM,
    ProductCatalogORM,
    ProjectHistoryORM,
)

# ----------------------------------------------------------------------
# Conversión: LoadUnit <-> ProductCatalogORM
# ----------------------------------------------------------------------


def _apply_load_unit_fields(orm: ProductCatalogORM, load_unit: LoadUnit) -> None:
    orm.sku = load_unit.sku
    orm.name = load_unit.name
    orm.length_cm = load_unit.dimensions.length_cm
    orm.width_cm = load_unit.dimensions.width_cm
    orm.height_cm = load_unit.dimensions.height_cm
    orm.weight_kg = load_unit.weight_kg
    orm.package_type = load_unit.package_type.value
    orm.units_per_package = load_unit.units_per_package
    orm.max_stack_count = load_unit.max_stack_count
    orm.max_supported_weight_kg = load_unit.max_supported_weight_kg
    orm.allowed_orientation_codes = json.dumps(
        [code.value for code in load_unit.allowed_orientation_codes]
    )
    orm.fragile = load_unit.fragile
    orm.is_extinguisher = load_unit.is_extinguisher
    orm.extinguisher_agent = load_unit.extinguisher_agent.value
    orm.extinguisher_nominal_kg = load_unit.extinguisher_nominal_kg
    orm.color_hex = load_unit.color_hex
    orm.notes = load_unit.notes


def _new_product_catalog_orm(
    load_unit: LoadUnit, *, now: datetime, is_active: bool = True
) -> ProductCatalogORM:
    orm = ProductCatalogORM(
        id=str(load_unit.id),
        sku=load_unit.sku,
        name=load_unit.name,
        length_cm=load_unit.dimensions.length_cm,
        width_cm=load_unit.dimensions.width_cm,
        height_cm=load_unit.dimensions.height_cm,
        weight_kg=load_unit.weight_kg,
        package_type=load_unit.package_type.value,
        units_per_package=load_unit.units_per_package,
        max_stack_count=load_unit.max_stack_count,
        max_supported_weight_kg=load_unit.max_supported_weight_kg,
        allowed_orientation_codes=json.dumps(
            [code.value for code in load_unit.allowed_orientation_codes]
        ),
        fragile=load_unit.fragile,
        is_extinguisher=load_unit.is_extinguisher,
        extinguisher_agent=load_unit.extinguisher_agent.value,
        extinguisher_nominal_kg=load_unit.extinguisher_nominal_kg,
        color_hex=load_unit.color_hex,
        notes=load_unit.notes,
        created_at=now,
        updated_at=now,
        is_active=is_active,
    )
    return orm


@dataclass(frozen=True, slots=True)
class CatalogProductEntry:
    """Fila del catálogo para la interfaz: un `LoadUnit` más su estado activo/archivado."""

    load_unit: LoadUnit
    is_active: bool


def _orm_to_load_unit(orm: ProductCatalogORM) -> LoadUnit:
    try:
        return LoadUnit(
            id=UUID(orm.id),
            sku=orm.sku,
            name=orm.name,
            dimensions=Dimensions3D(orm.length_cm, orm.width_cm, orm.height_cm),
            weight_kg=orm.weight_kg,
            package_type=PackageType(orm.package_type),
            units_per_package=orm.units_per_package,
            max_stack_count=orm.max_stack_count,
            max_supported_weight_kg=orm.max_supported_weight_kg,
            allowed_orientation_codes=tuple(
                OrientationCode(code) for code in json.loads(orm.allowed_orientation_codes)
            ),
            fragile=orm.fragile,
            is_extinguisher=orm.is_extinguisher,
            extinguisher_agent=ExtinguisherAgent(orm.extinguisher_agent),
            extinguisher_nominal_kg=orm.extinguisher_nominal_kg,
            color_hex=orm.color_hex,
            notes=orm.notes,
        )
    except (DomainValidationError, ValueError, KeyError) as exc:
        raise RepositoryError(f"Producto de catálogo corrupto (id={orm.id}): {exc}") from exc


class ProductCatalogRepository:
    """Catálogo global de `LoadUnit` reutilizables entre proyectos."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    def add(self, load_unit: LoadUnit) -> LoadUnit:
        now = datetime.now(UTC)
        with self._db.session_scope() as session:
            self._check_sku_available(session, load_unit.sku, exclude_id=None)
            orm = _new_product_catalog_orm(load_unit, now=now)
            session.add(orm)
            session.flush()
            return _orm_to_load_unit(orm)

    def update(self, load_unit: LoadUnit) -> LoadUnit:
        with self._db.session_scope() as session:
            orm = session.get(ProductCatalogORM, str(load_unit.id))
            if orm is None:
                raise RecordNotFoundError(
                    f"No existe un producto de catálogo con id={load_unit.id}."
                )
            self._check_sku_available(session, load_unit.sku, exclude_id=load_unit.id)
            _apply_load_unit_fields(orm, load_unit)
            orm.updated_at = datetime.now(UTC)
            session.flush()
            return _orm_to_load_unit(orm)

    def get_by_id(self, id: UUID) -> LoadUnit | None:
        with self._db.session_scope() as session:
            orm = session.get(ProductCatalogORM, str(id))
            return _orm_to_load_unit(orm) if orm is not None else None

    def get_by_sku(self, sku: str) -> LoadUnit | None:
        with self._db.session_scope() as session:
            orm = session.scalar(
                select(ProductCatalogORM).where(
                    func.lower(ProductCatalogORM.sku) == sku.lower(),
                    ProductCatalogORM.is_active.is_(True),
                )
            )
            return _orm_to_load_unit(orm) if orm is not None else None

    def list_active(self) -> tuple[LoadUnit, ...]:
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(ProductCatalogORM)
                .where(ProductCatalogORM.is_active.is_(True))
                .order_by(func.lower(ProductCatalogORM.sku))
            ).all()
            return tuple(_orm_to_load_unit(row) for row in rows)

    def search(self, text: str) -> tuple[LoadUnit, ...]:
        pattern = f"%{text.lower()}%"
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(ProductCatalogORM)
                .where(
                    ProductCatalogORM.is_active.is_(True),
                    (func.lower(ProductCatalogORM.sku).like(pattern))
                    | (func.lower(ProductCatalogORM.name).like(pattern)),
                )
                .order_by(func.lower(ProductCatalogORM.sku))
            ).all()
            return tuple(_orm_to_load_unit(row) for row in rows)

    def archive(self, id: UUID) -> None:
        self._set_active(id, active=False)

    def restore(self, id: UUID) -> None:
        self._set_active(id, active=True)

    def duplicate(self, id: UUID, new_sku: str, new_name: str | None = None) -> LoadUnit:
        with self._db.session_scope() as session:
            orm = session.get(ProductCatalogORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un producto de catálogo con id={id}.")
            self._check_sku_available(session, new_sku, exclude_id=None)
            now = datetime.now(UTC)
            new_orm = ProductCatalogORM(
                id=str(uuid4()),
                sku=new_sku,
                name=new_name if new_name is not None else orm.name,
                length_cm=orm.length_cm,
                width_cm=orm.width_cm,
                height_cm=orm.height_cm,
                weight_kg=orm.weight_kg,
                package_type=orm.package_type,
                units_per_package=orm.units_per_package,
                max_stack_count=orm.max_stack_count,
                max_supported_weight_kg=orm.max_supported_weight_kg,
                allowed_orientation_codes=orm.allowed_orientation_codes,
                fragile=orm.fragile,
                is_extinguisher=orm.is_extinguisher,
                extinguisher_agent=orm.extinguisher_agent,
                extinguisher_nominal_kg=orm.extinguisher_nominal_kg,
                color_hex=orm.color_hex,
                notes=orm.notes,
                created_at=now,
                updated_at=now,
                is_active=True,
            )
            session.add(new_orm)
            session.flush()
            return _orm_to_load_unit(new_orm)

    def list_all(self) -> tuple[CatalogProductEntry, ...]:
        """Activos y archivados juntos, para la columna "Activo" del diálogo de catálogo."""
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(ProductCatalogORM).order_by(func.lower(ProductCatalogORM.sku))
            ).all()
            return tuple(
                CatalogProductEntry(load_unit=_orm_to_load_unit(row), is_active=row.is_active)
                for row in rows
            )

    def count_active(self) -> int:
        with self._db.session_scope() as session:
            count = session.scalar(
                select(func.count())
                .select_from(ProductCatalogORM)
                .where(ProductCatalogORM.is_active.is_(True))
            )
            return int(count or 0)

    def apply_bulk(
        self, *, to_add: Sequence[LoadUnit] = (), to_update: Sequence[LoadUnit] = ()
    ) -> None:
        """Añade y actualiza varios productos en una única transacción (todo o nada).

        Usado por la importación masiva/con mapeo de la fase 8.1: si
        cualquier fila falla (SKU duplicado, id inexistente), la
        excepción sale de este `with` y `session_scope` revierte *toda*
        la operación — el catálogo nunca queda modificado a medias.
        """
        now = datetime.now(UTC)
        with self._db.session_scope() as session:
            for unit in to_add:
                self._check_sku_available(session, unit.sku, exclude_id=None)
                session.add(_new_product_catalog_orm(unit, now=now))
            for unit in to_update:
                orm = session.get(ProductCatalogORM, str(unit.id))
                if orm is None:
                    raise RecordNotFoundError(
                        f"No existe un producto de catálogo con id={unit.id}."
                    )
                self._check_sku_available(session, unit.sku, exclude_id=unit.id)
                _apply_load_unit_fields(orm, unit)
                orm.updated_at = now

    def _set_active(self, id: UUID, *, active: bool) -> None:
        with self._db.session_scope() as session:
            orm = session.get(ProductCatalogORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un producto de catálogo con id={id}.")
            orm.is_active = active
            orm.updated_at = datetime.now(UTC)

    def _check_sku_available(self, session: Session, sku: str, *, exclude_id: UUID | None) -> None:
        query = select(ProductCatalogORM).where(
            func.lower(ProductCatalogORM.sku) == sku.lower(),
            ProductCatalogORM.is_active.is_(True),
        )
        if exclude_id is not None:
            query = query.where(ProductCatalogORM.id != str(exclude_id))
        if session.scalar(query) is not None:
            raise DuplicateCatalogSkuError(
                f"Ya existe un producto activo del catálogo con SKU '{sku}'."
            )


# ----------------------------------------------------------------------
# Conversión: LoadingSpace <-> LoadingSpaceProfileORM
# ----------------------------------------------------------------------

_BUILTIN_PROFILE_FACTORIES = (
    LoadingSpace.standard_20ft_container,
    LoadingSpace.standard_40ft_container,
    LoadingSpace.standard_40ft_high_cube_container,
)


@dataclass(frozen=True, slots=True)
class LoadingSpaceProfileEntry:
    """Fila de perfil para la interfaz: un `LoadingSpace` más su estado y si es integrado."""

    loading_space: LoadingSpace
    is_active: bool
    is_builtin: bool


def _orm_to_loading_space(orm: LoadingSpaceProfileORM) -> LoadingSpace:
    try:
        return LoadingSpace(
            id=UUID(orm.id),
            name=orm.name,
            category=LoadingSpaceCategory(orm.category),
            internal_dimensions=Dimensions3D(orm.length_cm, orm.width_cm, orm.height_cm),
            door_position=DoorPosition(orm.door_position),
            max_weight_kg=orm.max_weight_kg,
            notes=orm.notes,
        )
    except (DomainValidationError, ValueError, KeyError) as exc:
        raise RepositoryError(f"Perfil de espacio corrupto (id={orm.id}): {exc}") from exc


class LoadingSpaceProfileRepository:
    """Perfiles de `LoadingSpace` reutilizables entre proyectos (incluidos los integrados)."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    def add(self, space: LoadingSpace, is_builtin: bool = False) -> LoadingSpace:
        now = datetime.now(UTC)
        with self._db.session_scope() as session:
            self._check_name_available(session, space.name, exclude_id=None)
            orm = LoadingSpaceProfileORM(
                id=str(space.id),
                name=space.name,
                category=space.category.value,
                length_cm=space.internal_dimensions.length_cm,
                width_cm=space.internal_dimensions.width_cm,
                height_cm=space.internal_dimensions.height_cm,
                max_weight_kg=space.max_weight_kg,
                door_position=space.door_position.value,
                notes=space.notes,
                created_at=now,
                updated_at=now,
                is_active=True,
                is_builtin=is_builtin,
            )
            session.add(orm)
            session.flush()
            return _orm_to_loading_space(orm)

    def update(self, space: LoadingSpace) -> LoadingSpace:
        with self._db.session_scope() as session:
            orm = session.get(LoadingSpaceProfileORM, str(space.id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un perfil de espacio con id={space.id}.")
            if orm.is_builtin:
                raise RepositoryError(
                    "No se puede modificar un perfil integrado directamente; duplícalo primero."
                )
            self._check_name_available(session, space.name, exclude_id=space.id)
            orm.name = space.name
            orm.category = space.category.value
            orm.length_cm = space.internal_dimensions.length_cm
            orm.width_cm = space.internal_dimensions.width_cm
            orm.height_cm = space.internal_dimensions.height_cm
            orm.max_weight_kg = space.max_weight_kg
            orm.door_position = space.door_position.value
            orm.notes = space.notes
            orm.updated_at = datetime.now(UTC)
            session.flush()
            return _orm_to_loading_space(orm)

    def get_by_id(self, id: UUID) -> LoadingSpace | None:
        with self._db.session_scope() as session:
            orm = session.get(LoadingSpaceProfileORM, str(id))
            return _orm_to_loading_space(orm) if orm is not None else None

    def get_by_name(self, name: str) -> LoadingSpace | None:
        with self._db.session_scope() as session:
            orm = session.scalar(
                select(LoadingSpaceProfileORM).where(
                    func.lower(LoadingSpaceProfileORM.name) == name.lower(),
                    LoadingSpaceProfileORM.is_active.is_(True),
                )
            )
            return _orm_to_loading_space(orm) if orm is not None else None

    def list_active(self) -> tuple[LoadingSpace, ...]:
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(LoadingSpaceProfileORM)
                .where(LoadingSpaceProfileORM.is_active.is_(True))
                .order_by(func.lower(LoadingSpaceProfileORM.name))
            ).all()
            return tuple(_orm_to_loading_space(row) for row in rows)

    def search(self, text: str) -> tuple[LoadingSpaceProfileEntry, ...]:
        pattern = f"%{text.lower()}%"
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(LoadingSpaceProfileORM)
                .where(
                    LoadingSpaceProfileORM.is_active.is_(True),
                    func.lower(LoadingSpaceProfileORM.name).like(pattern),
                )
                .order_by(func.lower(LoadingSpaceProfileORM.name))
            ).all()
            return tuple(
                LoadingSpaceProfileEntry(
                    loading_space=_orm_to_loading_space(row),
                    is_active=row.is_active,
                    is_builtin=row.is_builtin,
                )
                for row in rows
            )

    def archive(self, id: UUID) -> None:
        with self._db.session_scope() as session:
            orm = session.get(LoadingSpaceProfileORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un perfil de espacio con id={id}.")
            if orm.is_builtin:
                raise RepositoryError(
                    "No se puede archivar un perfil integrado directamente; duplícalo primero."
                )
        self._set_active(id, active=False)

    def restore(self, id: UUID) -> None:
        self._set_active(id, active=True)

    def duplicate(self, id: UUID, new_name: str) -> LoadingSpace:
        with self._db.session_scope() as session:
            orm = session.get(LoadingSpaceProfileORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un perfil de espacio con id={id}.")
            self._check_name_available(session, new_name, exclude_id=None)
            now = datetime.now(UTC)
            new_orm = LoadingSpaceProfileORM(
                id=str(uuid4()),
                name=new_name,
                category=orm.category,
                length_cm=orm.length_cm,
                width_cm=orm.width_cm,
                height_cm=orm.height_cm,
                max_weight_kg=orm.max_weight_kg,
                door_position=orm.door_position,
                notes=orm.notes,
                created_at=now,
                updated_at=now,
                is_active=True,
                is_builtin=False,
            )
            session.add(new_orm)
            session.flush()
            return _orm_to_loading_space(new_orm)

    def list_all(self) -> tuple[LoadingSpaceProfileEntry, ...]:
        """Activos y archivados juntos, para la columna "Activo" del diálogo de perfiles."""
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(LoadingSpaceProfileORM).order_by(func.lower(LoadingSpaceProfileORM.name))
            ).all()
            return tuple(
                LoadingSpaceProfileEntry(
                    loading_space=_orm_to_loading_space(row),
                    is_active=row.is_active,
                    is_builtin=row.is_builtin,
                )
                for row in rows
            )

    def ensure_builtin_profiles(self) -> None:
        with self._db.session_scope() as session:
            existing_names = {
                name.lower() for name in session.scalars(select(LoadingSpaceProfileORM.name)).all()
            }
            now = datetime.now(UTC)
            for factory in _BUILTIN_PROFILE_FACTORIES:
                space = factory()
                if space.name.lower() in existing_names:
                    continue
                orm = LoadingSpaceProfileORM(
                    id=str(space.id),
                    name=space.name,
                    category=space.category.value,
                    length_cm=space.internal_dimensions.length_cm,
                    width_cm=space.internal_dimensions.width_cm,
                    height_cm=space.internal_dimensions.height_cm,
                    max_weight_kg=space.max_weight_kg,
                    door_position=space.door_position.value,
                    notes=space.notes,
                    created_at=now,
                    updated_at=now,
                    is_active=True,
                    is_builtin=True,
                )
                session.add(orm)

    def _set_active(self, id: UUID, *, active: bool) -> None:
        with self._db.session_scope() as session:
            orm = session.get(LoadingSpaceProfileORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un perfil de espacio con id={id}.")
            orm.is_active = active
            orm.updated_at = datetime.now(UTC)

    def _check_name_available(
        self, session: Session, name: str, *, exclude_id: UUID | None
    ) -> None:
        query = select(LoadingSpaceProfileORM).where(
            func.lower(LoadingSpaceProfileORM.name) == name.lower(),
            LoadingSpaceProfileORM.is_active.is_(True),
        )
        if exclude_id is not None:
            query = query.where(LoadingSpaceProfileORM.id != str(exclude_id))
        if session.scalar(query) is not None:
            raise DuplicateLoadingSpaceProfileError(
                f"Ya existe un perfil de espacio activo con el nombre '{name}'."
            )


# ----------------------------------------------------------------------
# Perfiles de mapeo de columnas de importación Excel (fase 8.1)
# ----------------------------------------------------------------------

# Cabeceras canónicas de `infrastructure/excel/product_rows.py::PRODUCT_COLUMNS`
# y `packing_list_importer.py::PACKING_LIST_COLUMNS`, copiadas aquí como datos
# literales (nunca importadas): `infrastructure/database` nunca depende de
# `infrastructure/excel` — mismo criterio que evita que
# `packing_list_importer.py` dependa de este módulo (ver `docs/Excel.md`).
_BUILTIN_MAPPING_PROFILES: tuple[tuple[str, str, dict[str, str]], ...] = (
    (
        "Formato estándar CargoOptimizer",
        "catalog",
        {
            "SKU": "SKU",
            "Nombre": "Nombre",
            "Largo (cm)": "Largo (cm)",
            "Ancho (cm)": "Ancho (cm)",
            "Alto (cm)": "Alto (cm)",
            "Peso (kg)": "Peso (kg)",
            "Cantidad": "Cantidad",
            "Color": "Color",
            "Fragil": "Fragil",
            "Tipo de empaque": "Tipo de empaque",
            "Extintor": "Extintor",
            "Agente": "Agente",
            "Peso nominal (kg)": "Peso nominal (kg)",
            "Apilamiento": "Apilamiento",
            "Orientaciones": "Orientaciones",
            "Notas": "Notas",
        },
    ),
    (
        "Kupfer",
        "catalog",
        {
            "Código": "SKU",
            "Descripción": "Nombre",
            "Largo": "Largo (cm)",
            "Ancho": "Ancho (cm)",
            "Alto": "Alto (cm)",
            "Peso bruto": "Peso (kg)",
            "Cantidad": "Cantidad",
        },
    ),
    (
        "Joan",
        "catalog",
        {
            "Item": "SKU",
            "Producto": "Nombre",
            "Largo cm": "Largo (cm)",
            "Ancho cm": "Ancho (cm)",
            "Alto cm": "Alto (cm)",
            "Peso": "Peso (kg)",
            "Unidades": "Cantidad",
        },
    ),
    (
        "Exanco",
        "catalog",
        {
            "Referencia": "SKU",
            "Denominación": "Nombre",
            "Largo (cm)": "Largo (cm)",
            "Ancho (cm)": "Ancho (cm)",
            "Alto (cm)": "Alto (cm)",
            "Peso Kg": "Peso (kg)",
            "Cantidad": "Cantidad",
        },
    ),
)


@dataclass(frozen=True, slots=True)
class ImportMappingProfileEntry:
    """Perfil de mapeo de columnas de Excel: nombre, tipo de destino y el mapeo mismo.

    ``column_mapping`` es ``{cabecera_en_el_archivo: columna_canonica}``.
    ``target_kind`` es ``"catalog"``, ``"packing_list"`` o
    ``"loading_space"`` — a qué esquema de columnas de
    `infrastructure/excel` se aplica este perfil.
    """

    id: UUID
    name: str
    target_kind: str
    column_mapping: dict[str, str]
    created_at: datetime
    last_used_at: datetime | None
    is_active: bool
    is_builtin: bool


def _orm_to_mapping_profile_entry(orm: ImportMappingProfileORM) -> ImportMappingProfileEntry:
    try:
        column_mapping = json.loads(orm.column_mapping_json)
    except (TypeError, ValueError) as exc:
        raise RepositoryError(f"Perfil de mapeo corrupto (id={orm.id}): {exc}") from exc
    return ImportMappingProfileEntry(
        id=UUID(orm.id),
        name=orm.name,
        target_kind=orm.target_kind,
        column_mapping=column_mapping,
        created_at=orm.created_at,
        last_used_at=orm.last_used_at,
        is_active=orm.is_active,
        is_builtin=orm.is_builtin,
    )


class ImportMappingProfileRepository:
    """Perfiles de mapeo de columnas de Excel reutilizables entre importaciones."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    def add(
        self,
        name: str,
        target_kind: str,
        column_mapping: Mapping[str, str],
        *,
        is_builtin: bool = False,
    ) -> ImportMappingProfileEntry:
        now = datetime.now(UTC)
        with self._db.session_scope() as session:
            self._check_name_available(session, name, exclude_id=None)
            orm = ImportMappingProfileORM(
                id=str(uuid4()),
                name=name,
                target_kind=target_kind,
                column_mapping_json=json.dumps(dict(column_mapping)),
                created_at=now,
                last_used_at=None,
                is_active=True,
                is_builtin=is_builtin,
            )
            session.add(orm)
            session.flush()
            return _orm_to_mapping_profile_entry(orm)

    def update(
        self, id: UUID, *, name: str, column_mapping: Mapping[str, str]
    ) -> ImportMappingProfileEntry:
        with self._db.session_scope() as session:
            orm = session.get(ImportMappingProfileORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un perfil de mapeo con id={id}.")
            if orm.is_builtin:
                raise RepositoryError(
                    "No se puede modificar un perfil de mapeo integrado directamente; "
                    "duplícalo primero."
                )
            self._check_name_available(session, name, exclude_id=id)
            orm.name = name
            orm.column_mapping_json = json.dumps(dict(column_mapping))
            session.flush()
            return _orm_to_mapping_profile_entry(orm)

    def get_by_id(self, id: UUID) -> ImportMappingProfileEntry | None:
        with self._db.session_scope() as session:
            orm = session.get(ImportMappingProfileORM, str(id))
            return _orm_to_mapping_profile_entry(orm) if orm is not None else None

    def get_by_name(self, name: str) -> ImportMappingProfileEntry | None:
        with self._db.session_scope() as session:
            orm = session.scalar(
                select(ImportMappingProfileORM).where(
                    func.lower(ImportMappingProfileORM.name) == name.lower(),
                    ImportMappingProfileORM.is_active.is_(True),
                )
            )
            return _orm_to_mapping_profile_entry(orm) if orm is not None else None

    def list_active(self, target_kind: str | None = None) -> tuple[ImportMappingProfileEntry, ...]:
        with self._db.session_scope() as session:
            query = select(ImportMappingProfileORM).where(
                ImportMappingProfileORM.is_active.is_(True)
            )
            if target_kind is not None:
                query = query.where(ImportMappingProfileORM.target_kind == target_kind)
            rows = session.scalars(query.order_by(func.lower(ImportMappingProfileORM.name))).all()
            return tuple(_orm_to_mapping_profile_entry(row) for row in rows)

    def list_all(self) -> tuple[ImportMappingProfileEntry, ...]:
        """Activos y archivados juntos, para la columna "Activo" del diálogo de mapeos."""
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(ImportMappingProfileORM).order_by(func.lower(ImportMappingProfileORM.name))
            ).all()
            return tuple(_orm_to_mapping_profile_entry(row) for row in rows)

    def archive(self, id: UUID) -> None:
        self._set_active(id, active=False)

    def restore(self, id: UUID) -> None:
        self._set_active(id, active=True)

    def duplicate(self, id: UUID, new_name: str) -> ImportMappingProfileEntry:
        with self._db.session_scope() as session:
            orm = session.get(ImportMappingProfileORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un perfil de mapeo con id={id}.")
            self._check_name_available(session, new_name, exclude_id=None)
            now = datetime.now(UTC)
            new_orm = ImportMappingProfileORM(
                id=str(uuid4()),
                name=new_name,
                target_kind=orm.target_kind,
                column_mapping_json=orm.column_mapping_json,
                created_at=now,
                last_used_at=None,
                is_active=True,
                is_builtin=False,
            )
            session.add(new_orm)
            session.flush()
            return _orm_to_mapping_profile_entry(new_orm)

    def touch_last_used(self, id: UUID) -> None:
        with self._db.session_scope() as session:
            orm = session.get(ImportMappingProfileORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un perfil de mapeo con id={id}.")
            orm.last_used_at = datetime.now(UTC)

    def ensure_builtin_profiles(self) -> None:
        with self._db.session_scope() as session:
            existing_names = {
                name.lower() for name in session.scalars(select(ImportMappingProfileORM.name)).all()
            }
            now = datetime.now(UTC)
            for name, target_kind, column_mapping in _BUILTIN_MAPPING_PROFILES:
                if name.lower() in existing_names:
                    continue
                session.add(
                    ImportMappingProfileORM(
                        id=str(uuid4()),
                        name=name,
                        target_kind=target_kind,
                        column_mapping_json=json.dumps(column_mapping),
                        created_at=now,
                        last_used_at=None,
                        is_active=True,
                        is_builtin=True,
                    )
                )

    def _set_active(self, id: UUID, *, active: bool) -> None:
        with self._db.session_scope() as session:
            orm = session.get(ImportMappingProfileORM, str(id))
            if orm is None:
                raise RecordNotFoundError(f"No existe un perfil de mapeo con id={id}.")
            orm.is_active = active

    def _check_name_available(
        self, session: Session, name: str, *, exclude_id: UUID | None
    ) -> None:
        query = select(ImportMappingProfileORM).where(
            func.lower(ImportMappingProfileORM.name) == name.lower(),
            ImportMappingProfileORM.is_active.is_(True),
        )
        if exclude_id is not None:
            query = query.where(ImportMappingProfileORM.id != str(exclude_id))
        if session.scalar(query) is not None:
            raise DuplicateImportMappingProfileError(
                f"Ya existe un perfil de mapeo activo con el nombre '{name}'."
            )


# ----------------------------------------------------------------------
# Historial de proyectos
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProjectHistoryEntry:
    """Fila de `project_history`: metadatos, nunca el proyecto completo."""

    project_id: UUID
    project_name: str
    file_path: str
    last_opened_at: datetime | None
    last_saved_at: datetime | None
    application_version: str
    packed_count: int | None
    requested_count: int | None
    volume_utilization_percent: float | None
    used_weight_kg: float | None
    algorithm_name: str | None


def _orm_to_project_history_entry(orm: ProjectHistoryORM) -> ProjectHistoryEntry:
    return ProjectHistoryEntry(
        project_id=UUID(orm.project_id),
        project_name=orm.project_name,
        file_path=orm.file_path,
        last_opened_at=orm.last_opened_at,
        last_saved_at=orm.last_saved_at,
        application_version=orm.application_version,
        packed_count=orm.packed_count,
        requested_count=orm.requested_count,
        volume_utilization_percent=orm.volume_utilization_percent,
        used_weight_kg=orm.used_weight_kg,
        algorithm_name=orm.algorithm_name,
    )


class ProjectHistoryRepository:
    """Historial de apertura/guardado de proyectos `.cargo3d`, una fila por `file_path`."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    def record_open(
        self, *, project_id: UUID, project_name: str, file_path: str, application_version: str
    ) -> None:
        now = datetime.now(UTC)
        with self._db.session_scope() as session:
            orm = session.scalar(
                select(ProjectHistoryORM).where(ProjectHistoryORM.file_path == file_path)
            )
            if orm is None:
                session.add(
                    ProjectHistoryORM(
                        id=str(uuid4()),
                        project_id=str(project_id),
                        project_name=project_name,
                        file_path=file_path,
                        last_opened_at=now,
                        last_saved_at=None,
                        application_version=application_version,
                    )
                )
            else:
                orm.project_id = str(project_id)
                orm.project_name = project_name
                orm.last_opened_at = now
                orm.application_version = application_version

    def record_save(
        self,
        *,
        project_id: UUID,
        project_name: str,
        file_path: str,
        application_version: str,
        packed_count: int | None = None,
        requested_count: int | None = None,
        volume_utilization_percent: float | None = None,
        used_weight_kg: float | None = None,
        algorithm_name: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        with self._db.session_scope() as session:
            orm = session.scalar(
                select(ProjectHistoryORM).where(ProjectHistoryORM.file_path == file_path)
            )
            if orm is None:
                session.add(
                    ProjectHistoryORM(
                        id=str(uuid4()),
                        project_id=str(project_id),
                        project_name=project_name,
                        file_path=file_path,
                        last_opened_at=None,
                        last_saved_at=now,
                        application_version=application_version,
                        packed_count=packed_count,
                        requested_count=requested_count,
                        volume_utilization_percent=volume_utilization_percent,
                        used_weight_kg=used_weight_kg,
                        algorithm_name=algorithm_name,
                    )
                )
            else:
                orm.project_id = str(project_id)
                orm.project_name = project_name
                orm.last_saved_at = now
                orm.application_version = application_version
                orm.packed_count = packed_count
                orm.requested_count = requested_count
                orm.volume_utilization_percent = volume_utilization_percent
                orm.used_weight_kg = used_weight_kg
                orm.algorithm_name = algorithm_name

    def list_recent(self, limit: int = 10) -> tuple[ProjectHistoryEntry, ...]:
        with self._db.session_scope() as session:
            order_key = func.coalesce(
                ProjectHistoryORM.last_saved_at, ProjectHistoryORM.last_opened_at
            )
            rows = session.scalars(
                select(ProjectHistoryORM).order_by(order_key.desc()).limit(limit)
            ).all()
            return tuple(_orm_to_project_history_entry(row) for row in rows)

    def remove_missing_paths(self) -> int:
        with self._db.session_scope() as session:
            rows = session.scalars(select(ProjectHistoryORM)).all()
            removed = 0
            for row in rows:
                if not Path(row.file_path).exists():
                    session.delete(row)
                    removed += 1
            return removed

    def clear(self) -> None:
        with self._db.session_scope() as session:
            session.execute(delete(ProjectHistoryORM))


# ----------------------------------------------------------------------
# Historial de ejecuciones de optimización
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PackingRunHistoryEntry:
    """Fila de `packing_run_history`: métricas de una ejecución, nunca los placements."""

    id: UUID
    project_id: UUID
    project_name: str
    executed_at: datetime
    algorithm_name: str
    requested_count: int
    packed_count: int
    unpacked_count: int
    used_volume_cm3: float
    volume_utilization_percent: float
    used_weight_kg: float
    weight_utilization_percent: float | None
    execution_time_seconds: float
    warning_count: int
    application_version: str
    project_file_path: str | None


def _orm_to_run_history_entry(orm: PackingRunHistoryORM) -> PackingRunHistoryEntry:
    return PackingRunHistoryEntry(
        id=UUID(orm.id),
        project_id=UUID(orm.project_id),
        project_name=orm.project_name,
        executed_at=orm.executed_at,
        algorithm_name=orm.algorithm_name,
        requested_count=orm.requested_count,
        packed_count=orm.packed_count,
        unpacked_count=orm.unpacked_count,
        used_volume_cm3=orm.used_volume_cm3,
        volume_utilization_percent=orm.volume_utilization_percent,
        used_weight_kg=orm.used_weight_kg,
        weight_utilization_percent=orm.weight_utilization_percent,
        execution_time_seconds=orm.execution_time_seconds,
        warning_count=orm.warning_count,
        application_version=orm.application_version,
        project_file_path=orm.project_file_path,
    )


class PackingRunHistoryRepository:
    """Historial de ejecuciones de `PackingEngine`, una fila por ejecución."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    def record_run(
        self,
        *,
        project_id: UUID,
        project_name: str,
        result: PackingResult,
        application_version: str,
        project_file_path: str | None = None,
    ) -> None:
        with self._db.session_scope() as session:
            session.add(
                PackingRunHistoryORM(
                    id=str(uuid4()),
                    project_id=str(project_id),
                    project_name=project_name,
                    executed_at=datetime.now(UTC),
                    algorithm_name=result.algorithm_name,
                    requested_count=result.requested_count,
                    packed_count=result.packed_count,
                    unpacked_count=result.unpacked_count,
                    used_volume_cm3=result.used_volume_cm3,
                    volume_utilization_percent=result.volume_utilization_percent,
                    used_weight_kg=result.used_weight_kg,
                    weight_utilization_percent=result.weight_utilization_percent,
                    execution_time_seconds=result.execution_time_seconds,
                    warning_count=len(result.warnings),
                    application_version=application_version,
                    project_file_path=project_file_path,
                )
            )

    def list_for_project(
        self, project_id: UUID, limit: int = 50
    ) -> tuple[PackingRunHistoryEntry, ...]:
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(PackingRunHistoryORM)
                .where(PackingRunHistoryORM.project_id == str(project_id))
                .order_by(PackingRunHistoryORM.executed_at.desc())
                .limit(limit)
            ).all()
            return tuple(_orm_to_run_history_entry(row) for row in rows)

    def list_recent(self, limit: int = 50) -> tuple[PackingRunHistoryEntry, ...]:
        with self._db.session_scope() as session:
            rows = session.scalars(
                select(PackingRunHistoryORM)
                .order_by(PackingRunHistoryORM.executed_at.desc())
                .limit(limit)
            ).all()
            return tuple(_orm_to_run_history_entry(row) for row in rows)

    def clear_for_project(self, project_id: UUID) -> None:
        with self._db.session_scope() as session:
            session.execute(
                delete(PackingRunHistoryORM).where(
                    PackingRunHistoryORM.project_id == str(project_id)
                )
            )
