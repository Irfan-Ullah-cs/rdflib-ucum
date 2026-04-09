"""
test_05_arithmetic.py

Tests for UCUMQuantity arithmetic and conversion:
- Basic: +, -, same unit and cross-unit
- Complex: *, / dimension-changing (Pint tracks new dimensions)
- Scalar operations: quantity * int/float
- Derived physics: force, energy, power, pressure, velocity
- Dimensionless results: m/m, kg/kg
- Unary: __neg__, __abs__
- Error cases: incompatible dimensions for +/-
- Unit conversion: to(), to_si(), prefix handling
- Negative exponent notation: s-1 = Hz
- Temperature arithmetic (offset unit limitations)
- Dimensionless arithmetic
- UCUMUnit: parse, equality, hash
"""
from decimal import Decimal

import pytest
import pint

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.quantity import UCUMQuantity
from rdflib_ucum.unit import UCUMUnit
from rdflib_ucum.exceptions import UCUMDimensionError
from rdflib import Literal


# Addition and Subtraction
class TestAddition:

    def test_add_same_unit(self):
        result = UCUMQuantity("5 km") + UCUMQuantity("3 km")
        assert result.magnitude == 8
        assert result.ucum_unit == "km"

    def test_add_cross_unit_converts_to_left(self):
        """200 m added to 5 km — result in km."""
        result = UCUMQuantity("5 km") + UCUMQuantity("200 m")
        assert result.magnitude == Decimal("5.2")
        assert result.ucum_unit == "km"

    def test_add_mass(self):
        result = UCUMQuantity("1 kg") + UCUMQuantity("500 g")
        assert result.magnitude == Decimal("1.5")
        assert result.ucum_unit == "kg"

    def test_add_time(self):
        result = UCUMQuantity("1 h") + UCUMQuantity("30 min")
        assert result.magnitude == Decimal("1.5")
        assert result.ucum_unit == "h"

    def test_add_energy(self):
        result = UCUMQuantity("1 kJ") + UCUMQuantity("500 J")
        assert result.magnitude == Decimal("1.5")
        assert result.ucum_unit == "kJ"

    def test_add_complex_compound(self):
        """Force units: N + kg.m/s2 — same dimension, different notation."""
        result = UCUMQuantity("10 N") + UCUMQuantity("5 kg.m/s2")
        assert result.magnitude == Decimal("15.0")
        assert result.ucum_unit == "N"

    def test_add_incompatible_raises(self):
        with pytest.raises(UCUMDimensionError):
            UCUMQuantity("1 m") + UCUMQuantity("1 kg")


class TestSubtraction:

    def test_sub_same_unit(self):
        result = UCUMQuantity("5 km") - UCUMQuantity("3 km")
        assert result.magnitude == 2
        assert result.ucum_unit == "km"

    def test_sub_cross_unit(self):
        result = UCUMQuantity("5 km") - UCUMQuantity("200 m")
        assert result.magnitude == Decimal("4.8")
        assert result.ucum_unit == "km"

    def test_sub_zero_result(self):
        result = UCUMQuantity("1 km") - UCUMQuantity("1000 m")
        assert result.magnitude == 0

    def test_sub_negative_result(self):
        """Result stays in left operand's unit: 200 m - 1000 m = -800 m."""
        result = UCUMQuantity("200 m") - UCUMQuantity("1 km")
        assert result.magnitude == -800.0
        assert result.ucum_unit == "m"

    def test_sub_incompatible_raises(self):
        with pytest.raises(UCUMDimensionError):
            UCUMQuantity("1 m") - UCUMQuantity("1 s")


# Scalar Multiplication and Division
class TestScalarOperations:

    def test_mul_by_int(self):
        result = UCUMQuantity("5 km") * 3
        assert result.magnitude == 15
        assert result.ucum_unit == "km"

    def test_mul_by_float(self):
        result = UCUMQuantity("2 km") * 0.5
        assert result.magnitude == 1.0

    def test_rmul_by_int(self):
        result = 3 * UCUMQuantity("5 km")
        assert result.magnitude == 15

    def test_div_by_int(self):
        result = UCUMQuantity("10 km") / 2
        assert result.magnitude == 5
        assert result.ucum_unit == "km"

    def test_div_by_float(self):
        result = UCUMQuantity("1 km") / 0.5
        assert result.magnitude == 2.0


# Dimension-changing Multiplication and Division
class TestDimensionChangingArithmetic:

    def test_area_from_length_times_length(self):
        """m * m → m2."""
        result = UCUMQuantity("3 m") * UCUMQuantity("4 m")
        assert result.magnitude == 12
        dim = result.pint_quantity.dimensionality
        assert dim.get("[length]") == 2

    def test_velocity_from_length_div_time(self):
        """100 m / 10 s → 10 m/s."""
        result = UCUMQuantity("100 m") / UCUMQuantity("10 s")
        assert result.magnitude == 10
        assert result.ucum_unit == "m/s"
        dim = result.pint_quantity.dimensionality
        assert dim.get("[length]") == 1
        assert dim.get("[time]") == -1

    def test_force_from_mass_times_acceleration(self):
        """2 kg * 3 m/s2 → 6 N equivalent."""
        result = UCUMQuantity("2 kg") * UCUMQuantity("3 m/s2")
        assert result.magnitude == 6
        newton = UCUMQuantity("6 N")
        assert result == newton
        assert result.ucum_unit == "kg.m/s2"

    def test_energy_from_force_times_distance(self):
        """10 N * 5 m → 50 J equivalent."""
        result = UCUMQuantity("10 N") * UCUMQuantity("5 m")
        assert result.magnitude == 50
        assert result == UCUMQuantity("50 J")
        assert result.ucum_unit == "N.m"

    def test_power_from_energy_div_time(self):
        """100 J / 10 s → 10 W equivalent."""
        result = UCUMQuantity("100 J") / UCUMQuantity("10 s")
        assert result.magnitude == 10
        assert result == UCUMQuantity("10 W")
        assert result.ucum_unit == "J/s"

    def test_pressure_from_force_div_area(self):
        """10 N / 2 m2 → 5 Pa equivalent."""
        result = UCUMQuantity("10 N") / UCUMQuantity("2 m2")
        assert result.magnitude == 5
        assert result == UCUMQuantity("5 Pa")
        assert result.ucum_unit == "N/m2"

    def test_frequency_from_reciprocal_time(self):
        """1 / 0.01 s → 100 Hz equivalent."""
        result = UCUMQuantity("1 1") / UCUMQuantity("0.01 s")
        assert result.magnitude == 100
        assert result == UCUMQuantity("100 Hz")

    def test_dimensionless_from_same_unit_div(self):
        result = UCUMQuantity("5 m") / UCUMQuantity("5 m")
        assert result.magnitude == 1.0
        dim = result.pint_quantity.dimensionality
        assert dim == {}, f"Expected dimensionless, got {dim}"

    def test_dimensionless_from_mass_div(self):
        """2 kg / 1 kg → dimensionless 2."""
        result = UCUMQuantity("2 kg") / UCUMQuantity("1 kg")
        assert result.magnitude == 2.0

    def test_complex_chain_kinetic_energy(self):
        """KE = 0.5 * m * v^2.
        0.5 * 2 kg * (3 m/s)^2 = 9 J.
        """
        m = UCUMQuantity("2 kg")
        v = UCUMQuantity("3 m/s")
        ke = UCUMQuantity("0.5 1") * m * v * v
        assert ke.magnitude == 9.0
        assert ke == UCUMQuantity("9 J")

    def test_electric_power(self):
        """P = V * I: 10 V * 2 A → 20 W."""
        result = UCUMQuantity("10 V") * UCUMQuantity("2 A")
        assert result.magnitude == 20
        assert result == UCUMQuantity("20 W")
        assert result.ucum_unit == "V.A"

    def test_ohms_law(self):
        """R = V / I: 10 V / 2 A → 5 Ohm."""
        result = UCUMQuantity("10 V") / UCUMQuantity("2 A")
        assert result.magnitude == 5
        assert result == UCUMQuantity("5 Ohm")
        assert result.ucum_unit == "V/A"


# Unary operators
class TestUnaryOperators:

    def test_neg(self):
        result = -UCUMQuantity("5 km")
        assert result.magnitude == -5
        assert result.ucum_unit == "km"

    def test_neg_negative_becomes_positive(self):
        result = -UCUMQuantity("-3 m")
        assert result.magnitude == 3

    def test_abs_positive(self):
        result = abs(UCUMQuantity("5 km"))
        assert result.magnitude == 5

    def test_abs_negative(self):
        result = abs(UCUMQuantity("-5 km"))
        assert result.magnitude == 5
        assert result.ucum_unit == "km"

    def test_abs_zero(self):
        result = abs(UCUMQuantity("0 m"))
        assert result.magnitude == 0


# Unit conversion: to() and to_si() 
class TestUnitConversion:

    def test_km_to_m(self):
        result = UCUMQuantity("1 km").to("m")
        assert result.magnitude == 1000
        assert result.ucum_unit == "m"

    def test_m_to_km(self):
        result = UCUMQuantity("1000 m").to("km")
        assert result.magnitude == 1

    def test_g_to_kg(self):
        result = UCUMQuantity("500 g").to("kg")
        assert result.magnitude == 0.5

    def test_h_to_s(self):
        result = UCUMQuantity("1 h").to("s")
        assert result.magnitude == 3600

    def test_min_to_s(self):
        result = UCUMQuantity("1 min").to("s")
        assert result.magnitude == 60

    def test_MHz_to_Hz(self):
        result = UCUMQuantity("1 MHz").to("Hz")
        assert result.magnitude == 1e6

    def test_mV_to_V(self):
        result = UCUMQuantity("1000 mV").to("V")
        assert result.magnitude == 1

    def test_km_h_to_m_s(self):
        result = UCUMQuantity("3.6 km/h").to("m/s")
        assert result.magnitude == 1.0

    def test_eV_to_J(self):
        """Multi-hop: eV → J (electron volt to joule)."""
        result = UCUMQuantity("1 eV").to("J")
        assert result.magnitude == Decimal('1.602176634E-19')

    def test_N_to_kg_m_s2(self):
        """1 N = 1 kg.m/s2."""
        result = UCUMQuantity("1 N").to("kg.m/s2")
        assert result.magnitude == 1.0

    def test_incompatible_raises(self):
        with pytest.raises(pint.DimensionalityError):
            UCUMQuantity("1 m").to("kg")

    def test_incompatible_time_to_length_raises(self):
        with pytest.raises(pint.DimensionalityError):
            UCUMQuantity("1 s").to("m")


# Negative exponent / inverse notation  (from test_06)
class TestNegativeExponentUnits:

    def test_s_minus1_equals_hz(self):
        """s-1 is the same as Hz."""
        assert UCUMQuantity("1 s-1") == UCUMQuantity("1 Hz")

    def test_m_minus2_dimension(self):
        q = UCUMQuantity("1 m-2")
        dim = q.pint_quantity.dimensionality
        assert dim.get("[length]") == -2

    def test_inverse_second_comparison(self):
        assert UCUMQuantity("100 s-1") > UCUMQuantity("10 Hz")

    def test_m_per_s_equals_m_dot_s_minus1(self):
        """m/s and m.s-1 are the same."""
        a = UCUMQuantity("1 m/s")
        b = UCUMQuantity("1 m.s-1")
        assert a == b


# Temperature arithmetic  (from test_08)
class TestTemperatureArithmetic:

    def test_kelvin_addition(self):
        """Adding K quantities works (multiplicative unit)."""
        result = UCUMQuantity("100 K") + UCUMQuantity("200 K")
        assert result.magnitude == 300

    def test_celsius_addition_raises_offset_error(self):
        """
        Adding offset units (Cel + Cel) raises OffsetUnitCalculusError in Pint.
        This is a known, documented limitation — not a bug in rdflib-ucum.
        """
        with pytest.raises(pint.errors.OffsetUnitCalculusError):
            UCUMQuantity("10 Cel") + UCUMQuantity("20 Cel")


# Dimensionless arithmetic  (from test_08)
class TestDimensionlessArithmetic:

    def test_dimensionless_parses(self):
        q = UCUMQuantity("1 1")
        assert q.magnitude == 1.0

    def test_percent_parses(self):
        q = UCUMQuantity("50 %")
        assert q.magnitude == 50

    def test_percent_equality_with_dimensionless(self):
        """50% == 0.5 (dimensionless)."""
        assert UCUMQuantity("50 %") == UCUMQuantity("0.5 1")

    def test_dimensionless_from_division(self):
        """5 m / 5 m → dimensionless."""
        result = UCUMQuantity("5 m") / UCUMQuantity("5 m")
        dim = result.pint_quantity.dimensionality
        assert all(v == 0 for v in dim.values())

    def test_dimensionless_multiplication(self):
        result = UCUMQuantity("0.5 1") * UCUMQuantity("10 m")
        assert result.magnitude == 5.0


# UCUMUnit  
class TestUCUMUnit:

    def test_parse_simple(self):
        u = UCUMUnit("km")
        assert u.ucum_code == "km"

    def test_equality_cancellation(self):
        assert UCUMUnit("m.kg/kg") == UCUMUnit("m")

    def test_equality_equivalent_notation(self):
        assert UCUMUnit("m/s2") == UCUMUnit("m.s-2")

    def test_inequality_different_units(self):
        assert not (UCUMUnit("km") == UCUMUnit("m"))

    def test_hash_consistent(self):
        assert hash(UCUMUnit("km")) == hash(UCUMUnit("km"))
