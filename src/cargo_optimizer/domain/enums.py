"""Enumeraciones de dominio.

Los valores string de estos enums forman parte del formato de
persistencia futuro (fase 7) y de la futura API/integración ERP (fase
9): son estables y no deben renombrarse sin una migración explícita.
Ver docs/ADR/ADR-0005-inmutabilidad-y-enums-estables.md.
"""

from __future__ import annotations

from enum import StrEnum


class LoadingSpaceCategory(StrEnum):
    """Categoría de un Loading Space. `OTHER` cubre cualquier espacio no listado."""

    CONTAINER = "container"
    TRUCK = "truck"
    VAN = "van"
    TRAILER = "trailer"
    WAREHOUSE = "warehouse"
    RACK = "rack"
    OTHER = "other"


class DoorPosition(StrEnum):
    """Cara del Loading Space por la que se accede para cargar/descargar."""

    FRONT = "front"
    REAR = "rear"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    UNRESTRICTED = "unrestricted"


class PackageType(StrEnum):
    """Tipo de empaque físico de un Load Unit."""

    INDIVIDUAL = "individual"
    GROUPED_BOX = "grouped_box"
    PALLET = "pallet"
    DRUM = "drum"
    CYLINDER = "cylinder"
    IRREGULAR_BOUNDING_BOX = "irregular_bounding_box"
    OTHER = "other"


class ExtinguisherAgent(StrEnum):
    """Agente extintor cuando un Load Unit representa un extintor.

    `NOT_APPLICABLE` es el único valor válido cuando el Load Unit no es
    un extintor (ver validación en `LoadUnit`).
    """

    PQS = "pqs"
    CO2 = "co2"
    WATER = "water"
    FOAM = "foam"
    WET_CHEMICAL = "wet_chemical"
    CLEAN_AGENT = "clean_agent"
    OTHER = "other"
    NOT_APPLICABLE = "not_applicable"


class OrientationCode(StrEnum):
    """Las seis permutaciones ortogonales de (length, width, height) sobre (X, Y, Z).

    El nombre codifica, en orden, qué dimensión original de la caja
    queda alineada con X, Y y Z respectivamente. Por ejemplo:

    - ``LWH_XYZ``: length->X, width->Y, height->Z (orientación original, sin rotar).
    - ``WLH_XYZ``: width->X, length->Y, height->Z (rotación de 90° sobre el eje Z).
    - ``LHW_XYZ``: length->X, height->Y, width->Z (rotación de 90° sobre el eje X).
    - ``HWL_XYZ``: height->X, width->Y, length->Z (rotación de 90° sobre el eje Y).
    - ``WHL_XYZ``: width->X, height->Y, length->Z.
    - ``HLW_XYZ``: height->X, length->Y, width->Z.
    """

    LWH_XYZ = "lwh_xyz"
    WLH_XYZ = "wlh_xyz"
    LHW_XYZ = "lhw_xyz"
    HWL_XYZ = "hwl_xyz"
    WHL_XYZ = "whl_xyz"
    HLW_XYZ = "hlw_xyz"
