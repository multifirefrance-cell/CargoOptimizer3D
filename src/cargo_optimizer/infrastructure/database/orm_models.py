"""Modelos ORM de SQLAlchemy 2.x para el catálogo, perfiles e historial.

Completamente separados de `domain`: ninguna clase de aquí se expone
fuera de `infrastructure` (ver `repositories.py`, que convierte
explícitamente ORM <-> entidades de dominio, nunca vía `__dict__`).
Ningún modelo importa Qt ni tiene métodos de interfaz.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_UTC_DATETIME = DateTime(timezone=True)


class Base(DeclarativeBase):
    """Base declarativa común a todas las tablas de esta base de datos."""


class SchemaMetadataORM(Base):
    __tablename__ = "schema_metadata"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)


class ProductCatalogORM(Base):
    __tablename__ = "product_catalog"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    length_cm: Mapped[float] = mapped_column(Float)
    width_cm: Mapped[float] = mapped_column(Float)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    package_type: Mapped[str] = mapped_column(String)
    units_per_package: Mapped[int] = mapped_column(Integer)
    max_stack_count: Mapped[int] = mapped_column(Integer)
    max_supported_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    allowed_orientation_codes: Mapped[str] = mapped_column(String)
    fragile: Mapped[bool] = mapped_column(Boolean)
    is_extinguisher: Mapped[bool] = mapped_column(Boolean)
    extinguisher_agent: Mapped[str] = mapped_column(String)
    extinguisher_nominal_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    color_hex: Mapped[str] = mapped_column(String)
    notes: Mapped[str] = mapped_column(String)
    loading_priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(_UTC_DATETIME)
    updated_at: Mapped[datetime] = mapped_column(_UTC_DATETIME)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoadingSpaceProfileORM(Base):
    __tablename__ = "loading_space_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String)
    length_cm: Mapped[float] = mapped_column(Float)
    width_cm: Mapped[float] = mapped_column(Float)
    height_cm: Mapped[float] = mapped_column(Float)
    max_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    door_position: Mapped[str] = mapped_column(String)
    notes: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(_UTC_DATETIME)
    updated_at: Mapped[datetime] = mapped_column(_UTC_DATETIME)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)


class ImportMappingProfileORM(Base):
    __tablename__ = "import_mapping_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    target_kind: Mapped[str] = mapped_column(String)
    column_mapping_json: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(_UTC_DATETIME)
    last_used_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectHistoryORM(Base):
    __tablename__ = "project_history"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, index=True)
    project_name: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String, unique=True, index=True)
    last_opened_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    last_saved_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    application_version: Mapped[str] = mapped_column(String)
    packed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume_utilization_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    used_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    algorithm_name: Mapped[str | None] = mapped_column(String, nullable=True)


class PackingRunHistoryORM(Base):
    __tablename__ = "packing_run_history"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, index=True)
    project_name: Mapped[str] = mapped_column(String)
    executed_at: Mapped[datetime] = mapped_column(_UTC_DATETIME)
    algorithm_name: Mapped[str] = mapped_column(String)
    requested_count: Mapped[int] = mapped_column(Integer)
    packed_count: Mapped[int] = mapped_column(Integer)
    unpacked_count: Mapped[int] = mapped_column(Integer)
    used_volume_cm3: Mapped[float] = mapped_column(Float)
    volume_utilization_percent: Mapped[float] = mapped_column(Float)
    used_weight_kg: Mapped[float] = mapped_column(Float)
    weight_utilization_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_time_seconds: Mapped[float] = mapped_column(Float)
    warning_count: Mapped[int] = mapped_column(Integer)
    application_version: Mapped[str] = mapped_column(String)
    project_file_path: Mapped[str | None] = mapped_column(String, nullable=True)
