"""
test_04_comparison.py

Tests for ordering operators on UCUMQuantity and CDT Literals:
- Python-level: __lt__, __le__, __gt__, __ge__
- Cross-unit comparison via Pint conversion
- Derived and compound unit comparison
- Incompatible dimension → UCUMDimensionError
- Numeric boundary comparisons (large, small, precision limits)
- Temperature comparisons (offset units)
- Dimensionless comparisons
"""
from cmath import isfinite
from math import isfinite as math_isfinite

import pytest
from rdflib import Literal

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.quantity import UCUMQuantity
from rdflib_ucum.exceptions import UCUMDimensionError


# Python-level comparisons: UCUMQuantity operators
class TestLessThan:

    def test_lt_same_unit(self):
        assert UCUMQuantity("500 m") < UCUMQuantity("1000 m")

    def test_lt_mass_cross_unit(self):
        assert UCUMQuantity("500 g") < UCUMQuantity("1 kg")

    def test_lt_time_cross_unit(self):
        assert UCUMQuantity("59 min") < UCUMQuantity("1 h")

    def test_lt_energy(self):
        assert UCUMQuantity("1 eV") < UCUMQuantity("1 J")

    def test_lt_false_when_greater(self):
        assert not (UCUMQuantity("1 km") < UCUMQuantity("500 m"))

    def test_lt_false_when_equal(self):
        assert not (UCUMQuantity("1 km") < UCUMQuantity("1000 m"))

    def test_lt_incompatible_dimensions_raises(self):
        with pytest.raises(UCUMDimensionError):
            UCUMQuantity("1 m") < UCUMQuantity("1 kg")

    #  Below test contain 300 zeros.
    def test_lt_on_large_value(self):
        assert UCUMQuantity("10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 m"
                            ) < UCUMQuantity("10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001 m")

    def test_lt_compound_unit(self):
        assert UCUMQuantity("500 g.m/s2") < UCUMQuantity("1 kg.m/s2")


class TestGreaterThan:

    def test_gt_mass(self):
        assert UCUMQuantity("1 kg") > UCUMQuantity("999 g")

    def test_gt_speed(self):
        assert UCUMQuantity("10 m/s") > UCUMQuantity("30 km/h")

    def test_gt_acceleration(self):
        assert UCUMQuantity("9.81 m/s2") > UCUMQuantity("9.0 m/s2")

    def test_gt_false_when_equal(self):
        assert not (UCUMQuantity("1000 m") > UCUMQuantity("1 km"))

    def test_gt_incompatible_dimensions_raises(self):
        with pytest.raises(UCUMDimensionError):
            UCUMQuantity("1 m") > UCUMQuantity("1 s")

    def test_gt_derived_newton_vs_force(self):
        assert UCUMQuantity("2 N") > UCUMQuantity("1 kg.m/s2")


class TestLessOrEqual:

    def test_le_equal_cross_unit(self):
        assert UCUMQuantity("1000 m") <= UCUMQuantity("1 km")

    def test_le_false_when_greater(self):
        assert not (UCUMQuantity("2 km") <= UCUMQuantity("1000 m"))

    def test_le_incompatible_raises(self):
        with pytest.raises(UCUMDimensionError):
            UCUMQuantity("1 m") <= UCUMQuantity("1 kg")


class TestGreaterOrEqual:

    def test_ge_equal_cross_unit(self):
        assert UCUMQuantity("1 km") >= UCUMQuantity("1000 m")

    def test_ge_false_when_less(self):
        assert not (UCUMQuantity("500 m") >= UCUMQuantity("1 km"))

    def test_ge_incompatible_raises(self):
        with pytest.raises(UCUMDimensionError):
            UCUMQuantity("1 m") >= UCUMQuantity("1 s")


class TestCompoundAndDerivedComparison:

    def test_compound_acceleration(self):
        assert UCUMQuantity("9.81 m/s2") > UCUMQuantity("9.0 m/s2")

    def test_compound_force(self):
        assert UCUMQuantity("10 kg.m/s2") > UCUMQuantity("5 N")

    def test_compound_pressure(self):
        assert UCUMQuantity("101325 Pa") > UCUMQuantity("1 bar")

    def test_inverse_unit_frequency(self):
        """100 Hz > 10 Hz expressed as s-1."""
        assert UCUMQuantity("100 s-1") > UCUMQuantity("10 Hz")

    def test_energy_cross_type(self):
        """1 kJ > 1 J."""
        assert UCUMQuantity("1 kJ") > UCUMQuantity("1 J")

    def test_gt_complex_compound(self):
        """[ly].kg/([AU].s2) vs m.kg/([AU].s2) — force-like quantity with astronomical units."""
        assert UCUMQuantity("1 [ly].kg/([AU].s2)") > UCUMQuantity("1 m.kg/([AU].s2)")
        assert isfinite(UCUMQuantity("1 [ly].kg/([AU].s2)").magnitude)


# RDFLib Literal-level comparisons
class TestLiteralComparison:

    def test_literal_gt_same_unit(self):
        a = Literal("1000 m", datatype=CDT.ucum)
        b = Literal("500 m", datatype=CDT.ucum)
        assert a > b

    def test_literal_gt_cross_unit(self):
        a = Literal("1 km", datatype=CDT.ucum)
        b = Literal("500 m", datatype=CDT.ucum)
        assert a > b

    def test_literal_lt_cross_unit(self):
        a = Literal("500 m", datatype=CDT.ucum)
        b = Literal("1 km", datatype=CDT.ucum)
        assert a < b

    def test_literal_ge_equal(self):
        a = Literal("1 km", datatype=CDT.ucum)
        b = Literal("1000 m", datatype=CDT.ucum)
        assert a >= b

    def test_literal_le_equal(self):
        a = Literal("1000 m", datatype=CDT.ucum)
        b = Literal("1 km", datatype=CDT.ucum)
        assert a <= b

    def test_literal_mass_comparison(self):
        a = Literal("1 [ly].kg/([AU].s2)", datatype=CDT.ucum)
        b = Literal("1 m.kg/([AU].s2)", datatype=CDT.ucum)
        assert a > b


# Numeric boundary comparisons 
class TestLargeValueComparison:

    def test_large_value_parses(self):
        q = UCUMQuantity("1e308 m")
        assert q.magnitude == 1e308
        assert math_isfinite(q.magnitude)

    @pytest.mark.xfail(reason="IEEE 754: 1e309 overflows to inf, not a finite value")
    def test_overflow_value(self):
        q = UCUMQuantity("1e309 m")
        assert q.magnitude == 1e309
        assert math_isfinite(q.magnitude)

    def test_large_value_comparison(self):
        assert UCUMQuantity("1e308 m") > UCUMQuantity("1e307 m")

    def test_large_value_cross_unit(self):
        assert UCUMQuantity("1e200 km") == UCUMQuantity("1e203 m")


class TestSmallValueComparison:

    def test_small_value_parses(self):
        q = UCUMQuantity("1e-323 m")
        assert q.magnitude == 1e-323
        assert math_isfinite(q.magnitude) and q.magnitude > 0

    @pytest.mark.xfail(reason="IEEE 754: 1e-324 underflows to 0")
    def test_underflow_value(self):
        q = UCUMQuantity("1e-324 m")
        assert q.magnitude == 1e-324
        assert math_isfinite(q.magnitude) and q.magnitude > 0

    def test_small_value_distinguishable(self):
        assert UCUMQuantity("1.000000000000003 m") != UCUMQuantity("1.000000000000002 m")

    def test_small_value_indistinguishable_at_precision_limit(self):
        assert UCUMQuantity("1.0000000000000003 m") == UCUMQuantity("1.0000000000000002 m")  # 15-16 sig digits

    def test_small_value_comparison(self):
        assert UCUMQuantity("1e-20 m") < UCUMQuantity("1e-19 m")

    @pytest.mark.xfail(reason="IEEE 754: at small scales float density causes direct == to fail across units")
    def test_small_value_cross_unit_via_conversion(self):
        """Use .to() — direct == is unreliable at small scales."""
        result = UCUMQuantity("1e-20 km").to("m")
        assert result.magnitude == 1e-17


# Temperature comparisons 
class TestTemperatureComparison:

    def test_kelvin_parses(self):
        q = UCUMQuantity("273.15 K")
        assert q.magnitude == 273.15

    def test_celsius_parses(self):
        q = UCUMQuantity("0 Cel")
        assert q.magnitude == 0

    def test_kelvin_comparison_works(self):
        assert UCUMQuantity("300 K") > UCUMQuantity("273.15 K")

    def test_kelvin_cross_unit_comparison(self):
        assert UCUMQuantity("300 K") > UCUMQuantity("0 Cel")    # 300K > 273.15K
        assert UCUMQuantity("200 K") < UCUMQuantity("0 Cel")    # 200K < 273.15K

    def test_kelvin_literal_comparison(self):
        a = Literal("100 K", datatype=CDT.ucum)
        b = Literal("90 K", datatype=CDT.ucum)
        assert a > b


# Dimensionless comparisons 
class TestDimensionlessComparison:

    def test_dimensionless_comparison(self):
        assert UCUMQuantity("0.5 1") < UCUMQuantity("1 1")
