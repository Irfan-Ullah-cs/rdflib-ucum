"""
test_04_comparison.py

Tests for ordering operators on UCUMQuantity and CDT Literals:
- Python-level: __lt__, __le__, __gt__, __ge__
- Cross-unit comparison via Pint conversion
- Derived and compound unit comparison
- Incompatible dimension → TypeError
"""
import pytest
from rdflib import Literal

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.quantity import UCUMQuantity


   
# Python-level comparisons: UCUMQuantity operators
class TestLessThan:

    def test_lt_same_unit(self):
        assert UCUMQuantity("500 m") < UCUMQuantity("1000 m")

    def test_lt_cross_unit(self):
        assert UCUMQuantity("500 m") < UCUMQuantity("1 km")

    def test_lt_mass_cross_unit(self):
        assert UCUMQuantity("500 g") < UCUMQuantity("1 kg")

    def test_lt_time_cross_unit(self):
        assert UCUMQuantity("59 min") < UCUMQuantity("1 h")

    def test_lt_pressure(self):
        assert UCUMQuantity("1 Pa") < UCUMQuantity("1 kPa")

    def test_lt_energy(self):
        assert UCUMQuantity("1 eV") < UCUMQuantity("1 J")

    def test_lt_false_when_greater(self):
        assert not (UCUMQuantity("1 km") < UCUMQuantity("500 m"))

    def test_lt_false_when_equal(self):
        assert not (UCUMQuantity("1 km") < UCUMQuantity("1000 m"))

    def test_lt_incompatible_dimensions_raises(self):
        with pytest.raises(TypeError):
            UCUMQuantity("1 m") < UCUMQuantity("1 kg")

    def test_lt_returns_not_implemented_for_non_quantity(self):
        result = UCUMQuantity("1 m").__lt__(42)
        assert result is NotImplemented


class TestGreaterThan:

    def test_gt_same_unit(self):
        assert UCUMQuantity("1000 m") > UCUMQuantity("500 m")

    def test_gt_cross_unit(self):
        assert UCUMQuantity("1 km") > UCUMQuantity("500 m")

    def test_gt_mass(self):
        assert UCUMQuantity("1 kg") > UCUMQuantity("999 g")

    def test_gt_speed(self):
        assert UCUMQuantity("10 m/s") > UCUMQuantity("30 km/h")

    def test_gt_acceleration(self):
        assert UCUMQuantity("9.81 m/s2") > UCUMQuantity("9.0 m/s2")

    def test_gt_false_when_less(self):
        assert not (UCUMQuantity("500 m") > UCUMQuantity("1 km"))

    def test_gt_false_when_equal(self):
        assert not (UCUMQuantity("1000 m") > UCUMQuantity("1 km"))

    def test_gt_incompatible_dimensions_raises(self):
        with pytest.raises(TypeError):
            UCUMQuantity("1 m") > UCUMQuantity("1 s")

    def test_gt_derived_newton_vs_force(self):
        assert UCUMQuantity("2 N") > UCUMQuantity("1 kg.m/s2")


class TestLessOrEqual:

    def test_le_less(self):
        assert UCUMQuantity("500 m") <= UCUMQuantity("1 km")

    def test_le_equal_same_unit(self):
        assert UCUMQuantity("1 km") <= UCUMQuantity("1 km")

    def test_le_equal_cross_unit(self):
        assert UCUMQuantity("1000 m") <= UCUMQuantity("1 km")

    def test_le_false_when_greater(self):
        assert not (UCUMQuantity("2 km") <= UCUMQuantity("1000 m"))

    def test_le_incompatible_raises(self):
        with pytest.raises(TypeError):
            UCUMQuantity("1 m") <= UCUMQuantity("1 kg")


class TestGreaterOrEqual:

    def test_ge_greater(self):
        assert UCUMQuantity("1 km") >= UCUMQuantity("500 m")

    def test_ge_equal_same_unit(self):
        assert UCUMQuantity("1 km") >= UCUMQuantity("1 km")

    def test_ge_equal_cross_unit(self):
        assert UCUMQuantity("1 km") >= UCUMQuantity("1000 m")

    def test_ge_false_when_less(self):
        assert not (UCUMQuantity("500 m") >= UCUMQuantity("1 km"))

    def test_ge_incompatible_raises(self):
        with pytest.raises(TypeError):
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

    def test_electric_potential(self):
        assert UCUMQuantity("1 kV") > UCUMQuantity("999 V")

    def test_energy_cross_type(self):
        """1 kJ > 1 J."""
        assert UCUMQuantity("1 kJ") > UCUMQuantity("1 J")


   
# RDFLib Literal-level comparisons (Python __gt__ etc.)
class TestLiteralComparison:

    def test_literal_gt_same_unit(self):
        a = Literal("1000 m", datatype=CDT.length)
        b = Literal("500 m", datatype=CDT.length)
        assert a > b

    def test_literal_gt_cross_unit(self):
        a = Literal("1 km", datatype=CDT.length)
        b = Literal("500 m", datatype=CDT.length)
        assert a > b

    def test_literal_lt_cross_unit(self):
        a = Literal("500 m", datatype=CDT.length)
        b = Literal("1 km", datatype=CDT.length)
        assert a < b

    def test_literal_ge_equal(self):
        a = Literal("1 km", datatype=CDT.length)
        b = Literal("1000 m", datatype=CDT.length)
        assert a >= b

    def test_literal_le_equal(self):
        a = Literal("1000 m", datatype=CDT.length)
        b = Literal("1 km", datatype=CDT.length)
        assert a <= b

    def test_literal_mass_comparison(self):
        a = Literal("1 kg", datatype=CDT.mass)
        b = Literal("500 g", datatype=CDT.mass)
        assert a > b
