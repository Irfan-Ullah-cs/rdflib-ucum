"""
test_05_arithmetic.py

Tests for UCUMQuantity arithmetic operators:
- Basic: +, -, same unit and cross-unit
- Complex: *, / dimension-changing (Pint tracks new dimensions)
- Scalar operations: quantity * int/float
- Derived physics: force, energy, power, pressure, velocity
- Dimensionless results: m/m, kg/kg
- Unary: __neg__, __abs__
- Error cases: incompatible dimensions for +/-
"""
import pytest

import rdflib_ucum
from rdflib_ucum.quantity import UCUMQuantity


# ---------------------------------------------------------------------------
# Addition and Subtraction
# ---------------------------------------------------------------------------

class TestAddition:

    def test_add_same_unit(self):
        result = UCUMQuantity("5 km") + UCUMQuantity("3 km")
        assert result.magnitude == pytest.approx(8)
        assert result.ucum_unit == "km"

    def test_add_cross_unit_converts_to_left(self):
        """200 m added to 5 km — result in km."""
        result = UCUMQuantity("5 km") + UCUMQuantity("200 m")
        assert result.magnitude == pytest.approx(5.2)
        assert result.ucum_unit == "km"

    def test_add_mass(self):
        result = UCUMQuantity("1 kg") + UCUMQuantity("500 g")
        assert result.magnitude == pytest.approx(1.5)
        assert result.ucum_unit == "kg"

    def test_add_time(self):
        result = UCUMQuantity("1 h") + UCUMQuantity("30 min")
        assert result.magnitude == pytest.approx(1.5)
        assert result.ucum_unit == "h"

    def test_add_pressure(self):
        result = UCUMQuantity("1 kPa") + UCUMQuantity("500 Pa")
        assert result.magnitude == pytest.approx(1.5)
        assert result.ucum_unit == "kPa"

    def test_add_energy(self):
        result = UCUMQuantity("1 kJ") + UCUMQuantity("500 J")
        assert result.magnitude == pytest.approx(1.5)
        assert result.ucum_unit == "kJ"

    def test_add_incompatible_raises(self):
        with pytest.raises(TypeError):
            UCUMQuantity("1 m") + UCUMQuantity("1 kg")

    def test_add_returns_not_implemented_for_non_quantity(self):
        result = UCUMQuantity("1 m").__add__(5)
        assert result is NotImplemented


class TestSubtraction:

    def test_sub_same_unit(self):
        result = UCUMQuantity("5 km") - UCUMQuantity("3 km")
        assert result.magnitude == pytest.approx(2)
        assert result.ucum_unit == "km"

    def test_sub_cross_unit(self):
        result = UCUMQuantity("5 km") - UCUMQuantity("200 m")
        assert result.magnitude == pytest.approx(4.8)
        assert result.ucum_unit == "km"

    def test_sub_zero_result(self):
        result = UCUMQuantity("1 km") - UCUMQuantity("1000 m")
        assert result.magnitude == pytest.approx(0)

    def test_sub_negative_result(self):
        """Result stays in left operand's unit: 200 m - 1000 m = -800 m."""
        result = UCUMQuantity("200 m") - UCUMQuantity("1 km")
        assert result.magnitude == pytest.approx(-800.0)
        assert result.ucum_unit == "m"

    def test_sub_incompatible_raises(self):
        with pytest.raises(TypeError):
            UCUMQuantity("1 m") - UCUMQuantity("1 s")

    def test_sub_returns_not_implemented_for_non_quantity(self):
        result = UCUMQuantity("1 m").__sub__(5)
        assert result is NotImplemented


# ---------------------------------------------------------------------------
# Scalar Multiplication and Division
# ---------------------------------------------------------------------------

class TestScalarOperations:

    def test_mul_by_int(self):
        result = UCUMQuantity("5 km") * 3
        assert result.magnitude == pytest.approx(15)
        assert result.ucum_unit == "km"

    def test_mul_by_float(self):
        result = UCUMQuantity("2 km") * 0.5
        assert result.magnitude == pytest.approx(1.0)

    def test_rmul_by_int(self):
        result = 3 * UCUMQuantity("5 km")
        assert result.magnitude == pytest.approx(15)

    def test_div_by_int(self):
        result = UCUMQuantity("10 km") / 2
        assert result.magnitude == pytest.approx(5)
        assert result.ucum_unit == "km"

    def test_div_by_float(self):
        result = UCUMQuantity("1 km") / 0.5
        assert result.magnitude == pytest.approx(2.0)

    def test_mul_returns_not_implemented_for_string(self):
        result = UCUMQuantity("1 m").__mul__("x")
        assert result is NotImplemented

    def test_div_returns_not_implemented_for_string(self):
        result = UCUMQuantity("1 m").__truediv__("x")
        assert result is NotImplemented


# ---------------------------------------------------------------------------
# Dimension-changing Multiplication and Division (complex Pint cases)
# ---------------------------------------------------------------------------

class TestDimensionChangingArithmetic:

    def test_area_from_length_times_length(self):
        """m * m → m2."""
        result = UCUMQuantity("3 m") * UCUMQuantity("4 m")
        assert result.magnitude == pytest.approx(12)
        # Dimension should be length²
        dim = result.pint_quantity.dimensionality
        assert dim.get("[length]") == 2

    def test_velocity_from_length_div_time(self):
        """100 m / 10 s → 10 m/s."""
        result = UCUMQuantity("100 m") / UCUMQuantity("10 s")
        assert result.magnitude == pytest.approx(10)
        dim = result.pint_quantity.dimensionality
        assert dim.get("[length]") == 1
        assert dim.get("[time]") == -1

    def test_force_from_mass_times_acceleration(self):
        """2 kg * 3 m/s2 → 6 N equivalent."""
        result = UCUMQuantity("2 kg") * UCUMQuantity("3 m/s2")
        assert result.magnitude == pytest.approx(6)
        # Same dimension as newton: kg.m/s2
        newton = UCUMQuantity("6 N")
        assert result == newton
        assert result.ucum_unit == "kg.m/s2"

    def test_energy_from_force_times_distance(self):
        """10 N * 5 m → 50 J equivalent."""
        result = UCUMQuantity("10 N") * UCUMQuantity("5 m")
        assert result.magnitude == pytest.approx(50)
        assert result == UCUMQuantity("50 J")
        assert result.ucum_unit == "N.m"

    def test_power_from_energy_div_time(self):
        """100 J / 10 s → 10 W equivalent."""
        result = UCUMQuantity("100 J") / UCUMQuantity("10 s")
        assert result.magnitude == pytest.approx(10)
        assert result == UCUMQuantity("10 W")
        assert result.ucum_unit == "J/s"

    def test_pressure_from_force_div_area(self):
        """10 N / 2 m2 → 5 Pa equivalent."""
        result = UCUMQuantity("10 N") / UCUMQuantity("2 m2")
        assert result.magnitude == pytest.approx(5)
        assert result == UCUMQuantity("5 Pa")
        assert result.ucum_unit == "N/m2"

    def test_frequency_from_reciprocal_time(self):
        """1 / 0.01 s → 100 Hz equivalent."""
        result = UCUMQuantity("1 1") / UCUMQuantity("0.01 s")
        assert result.magnitude == pytest.approx(100)
        assert result == UCUMQuantity("100 Hz")

    def test_dimensionless_from_same_unit_div(self):
        result = UCUMQuantity("5 m") / UCUMQuantity("5 m")
        assert result.magnitude == pytest.approx(1.0)
        dim = result.pint_quantity.dimensionality
        non_zero = {k: v for k, v in dim.items() if v != 0}
        assert non_zero == {}, f"Expected dimensionless, got {dim}"

    def test_dimensionless_from_mass_div(self):
        """2 kg / 1 kg → dimensionless 2."""
        result = UCUMQuantity("2 kg") / UCUMQuantity("1 kg")
        assert result.magnitude == pytest.approx(2.0)

    def test_complex_chain_kinetic_energy(self):
        """KE = 0.5 * m * v^2.
        0.5 * 2 kg * (3 m/s)^2 = 9 J.
        """
        m = UCUMQuantity("2 kg")
        v = UCUMQuantity("3 m/s")
        ke = UCUMQuantity("0.5 1") * m * v * v
        assert ke.magnitude == pytest.approx(9.0)
        assert ke == UCUMQuantity("9 J")

    def test_electric_power(self):
        """P = V * I: 10 V * 2 A → 20 W."""
        result = UCUMQuantity("10 V") * UCUMQuantity("2 A")
        assert result.magnitude == pytest.approx(20)
        assert result == UCUMQuantity("20 W")
        assert result.ucum_unit == "V.A"

    def test_ohms_law(self):
        """R = V / I: 10 V / 2 A → 5 Ohm."""
        result = UCUMQuantity("10 V") / UCUMQuantity("2 A")
        assert result.magnitude == pytest.approx(5)
        assert result == UCUMQuantity("5 Ohm")
        assert result.ucum_unit == "V/A"


# ---------------------------------------------------------------------------
# Unary operators
# ---------------------------------------------------------------------------

class TestUnaryOperators:

    def test_neg(self):
        result = -UCUMQuantity("5 km")
        assert result.magnitude == pytest.approx(-5)
        assert result.ucum_unit == "km"

    def test_neg_negative_becomes_positive(self):
        result = -UCUMQuantity("-3 m")
        assert result.magnitude == pytest.approx(3)

    def test_abs_positive(self):
        result = abs(UCUMQuantity("5 km"))
        assert result.magnitude == pytest.approx(5)

    def test_abs_negative(self):
        result = abs(UCUMQuantity("-5 km"))
        assert result.magnitude == pytest.approx(5)
        assert result.ucum_unit == "km"

    def test_abs_zero(self):
        result = abs(UCUMQuantity("0 m"))
        assert result.magnitude == pytest.approx(0)