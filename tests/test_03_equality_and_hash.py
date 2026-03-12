"""
test_03_equality_and_hash.py

Tests for:
- UCUMQuantity value-space equality (CDT spec: pairs (v×r, b))
- Literal.eq() delegation to UCUMQuantity.__eq__
- Hash consistency with equality contract: a == b → hash(a) == hash(b)
- Set and dict usage
"""
import pytest
from rdflib import Literal

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.quantity import UCUMQuantity

# Python-level equality: UCUMQuantity.__eq__
class TestUCUMQuantityEquality:

    def test_same_unit_same_value(self):
        assert UCUMQuantity("1 m") == UCUMQuantity("1 m")

    def test_cross_unit_length(self):
        assert UCUMQuantity("1 km") == UCUMQuantity("1000 m")

    def test_cross_unit_mass(self):
        assert UCUMQuantity("1 kg") == UCUMQuantity("1000 g")

    def test_cross_unit_time(self):
        assert UCUMQuantity("1 h") == UCUMQuantity("3600 s")

    def test_cross_unit_pressure(self):
        assert UCUMQuantity("1 kPa") == UCUMQuantity("1000 Pa")

    def test_cross_unit_energy(self):
        assert UCUMQuantity("1 kJ") == UCUMQuantity("1000 J")

    def test_cross_unit_power(self):
        assert UCUMQuantity("1 kW") == UCUMQuantity("1000 W")

    def test_cross_unit_frequency(self):
        assert UCUMQuantity("1 kHz") == UCUMQuantity("1000 Hz")

    def test_cross_unit_speed(self):
        # 1 m/s = 3.6 km/h
        assert UCUMQuantity("3.6 km/h") == UCUMQuantity("1 m/s")

    def test_different_values_not_equal(self):
        assert not (UCUMQuantity("1 km") == UCUMQuantity("500 m"))

    def test_incompatible_dimensions_not_equal(self):
        """Different dimensions must return False, not raise."""
        assert not (UCUMQuantity("1 m") == UCUMQuantity("1 kg"))

    def test_incompatible_dimensions_time_vs_length(self):
        assert not (UCUMQuantity("1 s") == UCUMQuantity("1 m"))

    # Derived unit equivalences (CDT spec: value-space is (v×r, b))
    def test_newton_equals_kg_m_per_s2(self):
        """1 N = 1 kg.m/s2 by definition."""
        a = UCUMQuantity("1 N")
        b = UCUMQuantity("1 kg.m/s2")
        assert a == b

    def test_joule_equals_newton_meter(self):
        """1 J = 1 N.m."""
        assert UCUMQuantity("1 J") == UCUMQuantity("1 N.m")

    def test_watt_equals_joule_per_second(self):
        """1 W = 1 J/s."""
        assert UCUMQuantity("1 W") == UCUMQuantity("1 J/s")

    def test_pascal_equals_kg_per_m_s2(self):
        """1 Pa = 1 kg/(m.s2)."""
        assert UCUMQuantity("1 Pa") == UCUMQuantity("1 kg/(m.s2)")

    def test_hertz_equals_inverse_second(self):
        """1 Hz = 1 s-1."""
        assert UCUMQuantity("1 Hz") == UCUMQuantity("1 s-1")

    def test_dimensionless_ratio(self):
        """50% = 0.5 (dimensionless)."""
        assert UCUMQuantity("50 %") == UCUMQuantity("0.5 1")

    def test_not_equal_to_non_ucum_quantity(self):
        q = UCUMQuantity("1 m")
        assert q.__eq__("1 m") is NotImplemented
        assert q.__eq__(1.0) is NotImplemented


 
# RDFLib Literal.eq() delegation
class TestLiteralEquality:

    def test_eq_same_unit(self):
        a = Literal("1 km", datatype=CDT.length)
        b = Literal("1 km", datatype=CDT.length)
        assert a.eq(b)

    def test_eq_cross_unit_length(self):
        a = Literal("1 km", datatype=CDT.length)
        b = Literal("1000 m", datatype=CDT.length)
        assert a.eq(b)

    def test_eq_cross_unit_mass(self):
        a = Literal("1 kg", datatype=CDT.mass)
        b = Literal("1000 g", datatype=CDT.mass)
        assert a.eq(b)

    def test_eq_cross_unit_time(self):
        a = Literal("1 h", datatype=CDT.time)
        b = Literal("3600 s", datatype=CDT.time)
        assert a.eq(b)

    def test_neq_different_values(self):
        a = Literal("1 km", datatype=CDT.length)
        b = Literal("500 m", datatype=CDT.length)
        assert not a.eq(b)

    def test_neq_incompatible_dimensions_python(self):
        """Different physical dimensions must not be equal at Python level."""
        a = UCUMQuantity("1 m")
        b = UCUMQuantity("1 kg")
        assert not (a == b)

    def test_neq_different_cdt_type_uris_literal(self):
        """Different CDT datatype URIs — RDFLib rejects equality at datatype level."""
        a = Literal("1 m", datatype=CDT.length)
        b = Literal("1 m", datatype=CDT.mass)
        assert not a.eq(b)

    def test_eq_derived_newton(self):
        a = Literal("1 N", datatype=CDT.force)
        b = Literal("1 kg.m/s2", datatype=CDT.force)
        assert a.eq(b)

    def test_eq_speed(self):
        a = Literal("3.6 km/h", datatype=CDT.speed)
        b = Literal("1 m/s", datatype=CDT.speed)
        assert a.eq(b)


 
# Hash consistency
class TestHashConsistency:

    def test_equal_quantities_have_equal_hash(self):
        a = UCUMQuantity("1 km")
        b = UCUMQuantity("1000 m")
        assert a == b
        assert hash(a) == hash(b)

    def test_equal_mass_hash(self):
        a = UCUMQuantity("1 kg")
        b = UCUMQuantity("1000 g")
        assert hash(a) == hash(b)

    def test_equal_time_hash(self):
        a = UCUMQuantity("1 h")
        b = UCUMQuantity("3600 s")
        assert hash(a) == hash(b)

    def test_equal_derived_hash(self):
        a = UCUMQuantity("1 N")
        b = UCUMQuantity("1 kg.m/s2")
        assert a == b
        assert hash(a) == hash(b)

    def test_same_quantity_consistent_hash(self):
        q = UCUMQuantity("1.5 km")
        assert hash(q) == hash(q)

    def test_usable_as_dict_key(self):
        a = UCUMQuantity("1 km")
        b = UCUMQuantity("1000 m")
        d = {a: "distance"}
        assert d[b] == "distance"

    def test_usable_in_set_deduplication(self):
        a = UCUMQuantity("1 km")
        b = UCUMQuantity("1000 m")
        c = UCUMQuantity("2 km")
        s = {a, b, c}
        assert len(s) == 2  # a and b are the same value

    def test_different_values_likely_different_hash(self):
        a = UCUMQuantity("1 km")
        b = UCUMQuantity("2 km")
        # Not guaranteed by contract but should hold in practice
        assert hash(a) != hash(b)