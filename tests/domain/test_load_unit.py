"""Pruebas de LoadUnit."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.load_unit import LoadUnit

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "sku": "SKU-001",
        "name": "Caja estándar",
        "dimensions": _DIMS,
        "weight_kg": 12.5,
    }
    kwargs.update(overrides)
    return kwargs


def test_valid_creation() -> None:
    unit = LoadUnit(**_base_kwargs())
    assert unit.sku == "SKU-001"
    assert unit.quantity == 1


def test_empty_sku_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(sku="   "))


def test_empty_name_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(name=""))


def test_negative_weight_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(weight_kg=-1.0))


def test_zero_quantity_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(quantity=0))


def test_zero_units_per_package_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(units_per_package=0, package_type=PackageType.GROUPED_BOX))


def test_zero_max_stack_count_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(max_stack_count=0))


def test_invalid_color_hex_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(color_hex="red"))


def test_valid_color_hex_is_accepted() -> None:
    unit = LoadUnit(**_base_kwargs(color_hex="#1A2B3C"))
    assert unit.color_hex == "#1A2B3C"


def test_empty_allowed_orientations_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(allowed_orientation_codes=()))


def test_duplicate_orientations_are_deduplicated_preserving_order() -> None:
    unit = LoadUnit(
        **_base_kwargs(
            allowed_orientation_codes=(
                OrientationCode.LWH_XYZ,
                OrientationCode.WLH_XYZ,
                OrientationCode.LWH_XYZ,
            )
        )
    )
    assert unit.allowed_orientation_codes == (
        OrientationCode.LWH_XYZ,
        OrientationCode.WLH_XYZ,
    )


def test_default_orientations_are_all_six() -> None:
    unit = LoadUnit(**_base_kwargs())
    assert len(unit.allowed_orientation_codes) == 6


def test_normal_package_defaults() -> None:
    unit = LoadUnit(**_base_kwargs())
    assert unit.is_extinguisher is False
    assert unit.extinguisher_agent is ExtinguisherAgent.NOT_APPLICABLE
    assert unit.extinguisher_nominal_kg is None


def test_valid_extinguisher() -> None:
    unit = LoadUnit(
        **_base_kwargs(
            is_extinguisher=True,
            extinguisher_agent=ExtinguisherAgent.PQS,
            extinguisher_nominal_kg=6.0,
        )
    )
    assert unit.is_extinguisher is True
    assert unit.extinguisher_agent is ExtinguisherAgent.PQS
    assert unit.extinguisher_nominal_kg == 6.0


def test_extinguisher_missing_agent_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(is_extinguisher=True, extinguisher_nominal_kg=6.0))


def test_extinguisher_missing_nominal_weight_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(is_extinguisher=True, extinguisher_agent=ExtinguisherAgent.CO2))


def test_non_extinguisher_with_extinguisher_data_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(extinguisher_agent=ExtinguisherAgent.CO2))

    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(extinguisher_nominal_kg=6.0))


def test_individual_package_requires_units_per_package_equal_one() -> None:
    with pytest.raises(DomainValidationError):
        LoadUnit(**_base_kwargs(package_type=PackageType.INDIVIDUAL, units_per_package=2))


def test_grouped_box_allows_units_per_package_greater_than_one() -> None:
    unit = LoadUnit(**_base_kwargs(package_type=PackageType.GROUPED_BOX, units_per_package=12))
    assert unit.units_per_package == 12


def test_total_requested_units() -> None:
    unit = LoadUnit(
        **_base_kwargs(
            package_type=PackageType.GROUPED_BOX,
            quantity=3,
            units_per_package=12,
        )
    )
    assert unit.total_requested_units == 36
    assert unit.total_requested_packages == 3


def test_total_requested_weight_kg() -> None:
    unit = LoadUnit(**_base_kwargs(weight_kg=10.0, quantity=4))
    assert unit.total_requested_weight_kg == 40.0


def test_package_volume_cm3() -> None:
    unit = LoadUnit(**_base_kwargs())
    assert unit.package_volume_cm3 == _DIMS.volume_cm3


def test_candidate_orientations_matches_allowed_codes() -> None:
    unit = LoadUnit(
        **_base_kwargs(allowed_orientation_codes=(OrientationCode.LWH_XYZ, OrientationCode.HLW_XYZ))
    )
    orientations = unit.candidate_orientations()
    assert len(orientations) == 2
    assert orientations[0].code is OrientationCode.LWH_XYZ
    assert orientations[1].code is OrientationCode.HLW_XYZ
