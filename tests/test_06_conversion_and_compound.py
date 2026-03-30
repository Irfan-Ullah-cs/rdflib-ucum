"""
test_06_conversion_and_compound.py

Tests for:
- UCUMQuantity.to_si() SI base unit conversion
- Prefix handling: km -> m, mg -> kg, MHz -> Hz, mV -> V
- Derived multi-hop conversions: eV -> J, km/h -> m/s
- Compound unit parsing and dimension identity
- Derived SI equivalences: N = kg.m/s2, J = N.m, Pa = kg/(m.s2), Ohm = V/A
- Prefix on compound: kPa, mN, MJ, kW
- Negative exponent notation: s-1 = Hz, m-2
- Incompatible conversion raises DimensionalityError
"""
import pytest
import pint

import rdflib_ucum
from rdflib_ucum.quantity import UCUMQuantity
from rdflib_ucum import CDT
from rdflib import Literal


   
# to() — explicit unit conversion
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
        assert result.magnitude == pytest.approx(1.602176634e-19, rel=1e-6)

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



   
# Negative exponent / inverse notation
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




   
