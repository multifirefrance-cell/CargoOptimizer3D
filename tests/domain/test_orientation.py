"""Pruebas de Orientation y OrientationCode."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.orientation import Orientation


def test_identity_orientation_matches_base_dimensions() -> None:
    base = Dimensions3D(100.0, 50.0, 30.0)
    o = Orientation.from_base_dimensions(base, OrientationCode.LWH_XYZ)
    assert (o.x_size_cm, o.y_size_cm, o.z_size_cm) == (100.0, 50.0, 30.0)


def test_all_six_codes_produce_a_permutation_of_base_dimensions() -> None:
    base = Dimensions3D(100.0, 50.0, 30.0)
    expected_multiset = sorted(base.as_tuple())
    for code in OrientationCode:
        o = Orientation.from_base_dimensions(base, code)
        assert sorted((o.x_size_cm, o.y_size_cm, o.z_size_cm)) == expected_multiset


def test_orientation_is_immutable() -> None:
    base = Dimensions3D(100.0, 50.0, 30.0)
    o = Orientation.from_base_dimensions(base, OrientationCode.WLH_XYZ)
    assert o.x_size_cm == 50.0
    assert o.y_size_cm == 100.0
    assert o.z_size_cm == 30.0
