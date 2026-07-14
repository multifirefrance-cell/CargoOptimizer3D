"""Reglas críticas para extintores.

Distinción central que este módulo nunca debe confundir (ver
docs/DomainModel.md y docs/RulesEngine.md):

- ``weight_kg``: peso bruto del empaque.
- ``extinguisher_nominal_kg``: capacidad nominal de cada extintor.
- ``units_per_package``: número de extintores dentro de la caja.
- ``quantity``: número de cajas o paquetes solicitados.
- ``total_requested_units``: extintores totales contenidos.

La regla de horizontalidad y las capacidades recomendadas dependen
siempre de ``extinguisher_nominal_kg``, nunca de ``weight_kg``.
"""

from __future__ import annotations

from cargo_optimizer.domain.enums import OrientationCode, PackageType
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.rules.codes import (
    EXTINGUISHER_AXIS_NOT_PARALLEL_TO_X,
    EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD,
    EXTINGUISHER_INDIVIDUAL_MUST_BE_HORIZONTAL,
)
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation

NOMINAL_WEIGHT_TOLERANCE_KG = 0.05
"""Tolerancia para comparar pesos nominales de extintores, en kg.

Los valores nominales de fabricación son convencionalmente números
redondos (1, 2, 3, 5, 6 kg...). Esta tolerancia absorbe variaciones de
redondeo o conversión de unidades sin confundir productos realmente
distintos (3 kg y 3.5 kg siguen siendo nominales distintos).
"""

_RECOMMENDED_UNITS_PER_PACKAGE: dict[float, int] = {1.0: 10, 2.0: 8, 3.0: 6}
"""Capacidades recomendadas (no obligatorias) por kg nominal de extintor."""

# Eje (X/Y/Z) sobre el que queda la dimensión original `length_cm` de la caja
# para cada OrientationCode. Ver el docstring de OrientationCode en
# cargo_optimizer.domain.enums para la semántica exacta de cada código
# (LWH_XYZ: length->X; WLH_XYZ: length->Y; LHW_XYZ: length->X;
# HWL_XYZ: length->Z; WHL_XYZ: length->Z; HLW_XYZ: length->Y). No se deriva
# dinámicamente porque OrientationCode es un enum pequeño y cerrado, estable
# por contrato (ADR-0005); una prueba dedicada verifica que esta tabla no
# haya divergido de la semántica real de `Orientation.from_base_dimensions`.
_LENGTH_AXIS_BY_CODE: dict[OrientationCode, str] = {
    OrientationCode.LWH_XYZ: "X",
    OrientationCode.LHW_XYZ: "X",
    OrientationCode.WLH_XYZ: "Y",
    OrientationCode.HLW_XYZ: "Y",
    OrientationCode.HWL_XYZ: "Z",
    OrientationCode.WHL_XYZ: "Z",
}


def _matches_nominal(value: float, target: float) -> bool:
    return abs(value - target) <= NOMINAL_WEIGHT_TOLERANCE_KG


def is_individual_large_extinguisher(load_unit: LoadUnit) -> bool:
    """True si es un extintor individual de 3 kg nominales o más (regla 7.1)."""
    nominal = load_unit.extinguisher_nominal_kg
    return (
        load_unit.is_extinguisher
        and load_unit.package_type is PackageType.INDIVIDUAL
        and nominal is not None
        and nominal >= 3.0 - NOMINAL_WEIGHT_TOLERANCE_KG
    )


def is_grouped_small_extinguisher(load_unit: LoadUnit) -> bool:
    """True si es una caja grupal de extintores de 1, 2 o 3 kg nominales (regla 7.2)."""
    if not (load_unit.is_extinguisher and load_unit.package_type is PackageType.GROUPED_BOX):
        return False
    nominal = load_unit.extinguisher_nominal_kg
    if nominal is None:
        return False
    return any(_matches_nominal(nominal, target) for target in _RECOMMENDED_UNITS_PER_PACKAGE)


def recommended_grouped_units_per_package(nominal_kg: float) -> int | None:
    """Capacidad recomendada (no obligatoria) para un nominal de 1, 2 o 3 kg; si no, None."""
    for target, recommended in _RECOMMENDED_UNITS_PER_PACKAGE.items():
        if _matches_nominal(nominal_kg, target):
            return recommended
    return None


def effective_max_stack_count(load_unit: LoadUnit) -> int:
    """`load_unit.max_stack_count`, salvo para extintores individuales grandes (siempre 1)."""
    if is_individual_large_extinguisher(load_unit):
        return 1
    return load_unit.max_stack_count


def evaluate_extinguisher_configuration(load_unit: LoadUnit) -> RuleEvaluation:
    """Advertencias de configuración específicas de extintores (no invariantes de dominio).

    Hoy solo cubre la recomendación de `units_per_package` en cajas
    grupales de 1/2/3 kg: una capacidad distinta de la recomendada
    genera una advertencia, nunca un rechazo (el usuario puede
    configurar la que necesite).
    """
    if not is_grouped_small_extinguisher(load_unit):
        return RuleEvaluation.allowed()

    nominal = load_unit.extinguisher_nominal_kg
    if nominal is None:
        return RuleEvaluation.allowed()

    recommended = recommended_grouped_units_per_package(nominal)
    if recommended is None or load_unit.units_per_package == recommended:
        return RuleEvaluation.allowed()

    return RuleEvaluation.allowed(
        (
            RuleViolation(
                code=EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD,
                message=(
                    f"'{load_unit.sku}': se recomiendan {recommended} unidades por caja "
                    f"para extintores de {nominal:g} kg en caja grupal; configurado: "
                    f"{load_unit.units_per_package}."
                ),
                severity=RuleSeverity.WARNING,
                load_unit_id=load_unit.id,
            ),
        )
    )


def evaluate_extinguisher_orientation(
    load_unit: LoadUnit,
    loading_space: LoadingSpace,
    orientation: Orientation,
) -> RuleEvaluation:
    """Para extintores individuales grandes: el eje `length_cm` original debe quedar sobre X.

    Cualquier otra orientación se rechaza: si `length` termina en Z, la
    caja quedaría vertical; si termina en Y, quedaría horizontal pero
    no paralela a X. Para cualquier otro LoadUnit, la regla no aplica y
    se permite siempre.

    `loading_space` se recibe por uniformidad con el resto de la API de
    `rules` (todas las evaluaciones de orientación reciben el mismo
    conjunto de argumentos); esta regla en concreto no depende de sus
    dimensiones, porque el eje X es una propiedad fija del sistema de
    coordenadas, no del espacio de carga concreto.
    """
    if not is_individual_large_extinguisher(load_unit):
        return RuleEvaluation.allowed()

    axis = _LENGTH_AXIS_BY_CODE[orientation.code]
    if axis == "X":
        return RuleEvaluation.allowed()

    if axis == "Z":
        return RuleEvaluation.rejected(
            (
                RuleViolation(
                    code=EXTINGUISHER_INDIVIDUAL_MUST_BE_HORIZONTAL,
                    message=(
                        f"'{load_unit.sku}' es un extintor individual >= 3 kg: no puede "
                        "colocarse en vertical (su eje longitudinal quedaría sobre Z)."
                    ),
                    severity=RuleSeverity.ERROR,
                    load_unit_id=load_unit.id,
                ),
            )
        )

    return RuleEvaluation.rejected(
        (
            RuleViolation(
                code=EXTINGUISHER_AXIS_NOT_PARALLEL_TO_X,
                message=(
                    f"'{load_unit.sku}' es un extintor individual >= 3 kg: su eje "
                    "longitudinal debe quedar paralelo a X; en esta orientación queda "
                    "sobre Y."
                ),
                severity=RuleSeverity.ERROR,
                load_unit_id=load_unit.id,
            ),
        )
    )
