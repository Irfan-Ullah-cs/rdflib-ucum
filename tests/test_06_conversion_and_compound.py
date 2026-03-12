"""
test_06_conversion_and_compound.py

Tests for:
- UCUMQuantity.to() unit conversion for all 33 CDT dimension types
- UCUMQuantity.to_si() SI base unit conversion
- Prefix handling: km→m, mg→kg, MHz→Hz, mV→V
- Derived multi-hop conversions: eV→J, km/h→m/s
- Compound unit parsing and dimension identity
- Derived SI equivalences: N=kg.m/s2, J=N.m, Pa=kg/(m.s2), Ohm=V/A
- Prefix on compound: kPa, mN, MJ, kW
- Negative exponent notation: s-1=Hz, m-2
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
        assert result.magnitude == pytest.approx(1000)
        assert result.ucum_unit == "m"

    def test_m_to_km(self):
        result = UCUMQuantity("1000 m").to("km")
        assert result.magnitude == pytest.approx(1)

    def test_kg_to_g(self):
        result = UCUMQuantity("1 kg").to("g")
        assert result.magnitude == pytest.approx(1000)

    def test_g_to_kg(self):
        result = UCUMQuantity("500 g").to("kg")
        assert result.magnitude == pytest.approx(0.5)

    def test_h_to_s(self):
        result = UCUMQuantity("1 h").to("s")
        assert result.magnitude == pytest.approx(3600)

    def test_min_to_s(self):
        result = UCUMQuantity("1 min").to("s")
        assert result.magnitude == pytest.approx(60)

    def test_kPa_to_Pa(self):
        result = UCUMQuantity("1 kPa").to("Pa")
        assert result.magnitude == pytest.approx(1000)

    def test_kJ_to_J(self):
        result = UCUMQuantity("1 kJ").to("J")
        assert result.magnitude == pytest.approx(1000)

    def test_kW_to_W(self):
        result = UCUMQuantity("1 kW").to("W")
        assert result.magnitude == pytest.approx(1000)

    def test_kHz_to_Hz(self):
        result = UCUMQuantity("1 kHz").to("Hz")
        assert result.magnitude == pytest.approx(1000)

    def test_MHz_to_Hz(self):
        result = UCUMQuantity("1 MHz").to("Hz")
        assert result.magnitude == pytest.approx(1e6)

    def test_mV_to_V(self):
        result = UCUMQuantity("1000 mV").to("V")
        assert result.magnitude == pytest.approx(1)

    def test_km_h_to_m_s(self):
        result = UCUMQuantity("3.6 km/h").to("m/s")
        assert result.magnitude == pytest.approx(1.0)

    def test_eV_to_J(self):
        """Multi-hop: eV → J (electron volt to joule)."""
        result = UCUMQuantity("1 eV").to("J")
        assert result.magnitude == pytest.approx(1.602176634e-19, rel=1e-6)

    def test_N_to_kg_m_s2(self):
        """1 N = 1 kg.m/s2."""
        result = UCUMQuantity("1 N").to("kg.m/s2")
        assert result.magnitude == pytest.approx(1.0)

    def test_incompatible_raises(self):
        with pytest.raises(pint.DimensionalityError):
            UCUMQuantity("1 m").to("kg")

    def test_incompatible_time_to_length_raises(self):
        with pytest.raises(pint.DimensionalityError):
            UCUMQuantity("1 s").to("m")


   
# to_si() — SI base unit conversion
class TestToSI:

    def test_km_to_si(self):
        result = UCUMQuantity("1 km").to_si()
        assert result.magnitude == pytest.approx(1000)

    def test_g_to_si(self):
        result = UCUMQuantity("1000 g").to_si()
        assert result.magnitude == pytest.approx(1.0)

    def test_min_to_si(self):
        result = UCUMQuantity("1 min").to_si()
        assert result.magnitude == pytest.approx(60)

    def test_kPa_to_si(self):
        result = UCUMQuantity("1 kPa").to_si()
        assert result.magnitude == pytest.approx(1000)

    def test_kJ_to_si(self):
        result = UCUMQuantity("1 kJ").to_si()
        assert result.magnitude == pytest.approx(1000)

    def test_kW_to_si(self):
        result = UCUMQuantity("1 kW").to_si()
        assert result.magnitude == pytest.approx(1000)

    def test_N_to_si(self):
        """1 N → 1 kg.m/s2."""
        result = UCUMQuantity("1 N").to_si()
        assert result.magnitude == pytest.approx(1.0)

    def test_eV_to_si(self):
        result = UCUMQuantity("1 eV").to_si()
        assert result.magnitude == pytest.approx(1.602176634e-19, rel=1e-6)


   
# Compound unit parsing and dimension identity
class TestCompoundUnits:

    def test_parse_m_per_s(self):
        q = UCUMQuantity("10 m/s")
        assert q.magnitude == pytest.approx(10)
        dim = q.pint_quantity.dimensionality
        assert dim.get("[length]") == 1
        assert dim.get("[time]") == -1

    def test_parse_m_per_s2(self):
        q = UCUMQuantity("9.8 m/s2")
        assert q.magnitude == pytest.approx(9.8)
        dim = q.pint_quantity.dimensionality
        assert dim.get("[length]") == 1
        assert dim.get("[time]") == -2

    def test_parse_kg_dot_m_per_s2(self):
        q = UCUMQuantity("1 kg.m/s2")
        dim = q.pint_quantity.dimensionality
        assert dim.get("[mass]") == 1
        assert dim.get("[length]") == 1
        assert dim.get("[time]") == -2

    def test_parse_kg_dot_m2_per_s2(self):
        q = UCUMQuantity("1 kg.m2/s2")
        dim = q.pint_quantity.dimensionality
        assert dim.get("[mass]") == 1
        assert dim.get("[length]") == 2
        assert dim.get("[time]") == -2

    def test_parse_kg_per_m_s2(self):
        """Pressure dimension: kg/(m.s2)."""
        q = UCUMQuantity("1 kg/(m.s2)")
        dim = q.pint_quantity.dimensionality
        assert dim.get("[mass]") == 1
        assert dim.get("[length]") == -1
        assert dim.get("[time]") == -2

    def test_newton_same_dim_as_kg_m_s2(self):
        n = UCUMQuantity("1 N")
        c = UCUMQuantity("1 kg.m/s2")
        assert n.same_dimension(c)
        assert n == c

    def test_joule_same_dim_as_kg_m2_s2(self):
        j = UCUMQuantity("1 J")
        c = UCUMQuantity("1 kg.m2/s2")
        assert j.same_dimension(c)
        assert j == c

    def test_pascal_same_dim_as_kg_per_m_s2(self):
        p = UCUMQuantity("1 Pa")
        c = UCUMQuantity("1 kg/(m.s2)")
        assert p.same_dimension(c)
        assert p == c

    def test_watt_same_dim_as_kg_m2_per_s3(self):
        w = UCUMQuantity("1 W")
        c = UCUMQuantity("1 kg.m2/s3")
        assert w.same_dimension(c)
        assert w == c

    def test_ohm_same_dim_as_kg_m2_per_A2_s3(self):
        """Ohm = kg.m2/(A2.s3)."""
        o = UCUMQuantity("1 Ohm")
        c = UCUMQuantity("1 kg.m2/(A2.s3)")
        assert o.same_dimension(c)
        assert o == c

    def test_volt_same_dim_as_kg_m2_per_A_s3(self):
        """Volt = kg.m2/(A.s3)."""
        v = UCUMQuantity("1 V")
        c = UCUMQuantity("1 kg.m2/(A.s3)")
        assert v.same_dimension(c)
        assert v == c


   
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


   
# Prefix on compound units
class TestPrefixOnCompound:

    def test_kPa_conversion(self):
        assert UCUMQuantity("1 kPa") == UCUMQuantity("1000 Pa")

    def test_mN_conversion(self):
        assert UCUMQuantity("1000 mN") == UCUMQuantity("1 N")

    def test_MJ_conversion(self):
        assert UCUMQuantity("1 MJ") == UCUMQuantity("1000 kJ")

    def test_kW_conversion(self):
        assert UCUMQuantity("1 kW") == UCUMQuantity("1000 W")

    def test_km_per_h_to_m_per_s(self):
        result = UCUMQuantity("3.6 km/h").to("m/s")
        assert result.magnitude == pytest.approx(1.0)


   
# All 33 CDT dimension types — to_si() smoke test
class TestAllDimensionTypesToSI:

    @pytest.mark.parametrize("lexical,datatype", [
        ("9.8 m/s2",   CDT.acceleration),
        ("1 mol",      CDT.amountOfSubstance),
        ("1 rad",      CDT.angle),
        ("1 m2",       CDT.area),
        ("1 kat",      CDT.catalyticActivity),
        ("1 1",        CDT.dimensionless),
        ("1 F",        CDT.electricCapacitance),
        ("1 C",        CDT.electricCharge),
        ("1 S",        CDT.electricConductance),
        ("1 A",        CDT.electricCurrent),
        ("1 H",        CDT.electricInductance),
        ("1 V",        CDT.electricPotential),
        ("1 Ohm",      CDT.electricResistance),
        ("1 J",        CDT.energy),
        ("1 N",        CDT.force),
        ("1 Hz",       CDT.frequency),
        ("1 lx",       CDT.illuminance),
        ("1 m",        CDT.length),
        ("1 lm",       CDT.luminousFlux),
        ("1 cd",       CDT.luminousIntensity),
        ("1 Wb",       CDT.magneticFlux),
        ("1 T",        CDT.magneticFluxDensity),
        ("1 kg",       CDT.mass),
        ("1 W",        CDT.power),
        ("1 Pa",       CDT.pressure),
        ("1 Gy",       CDT.radiationDoseAbsorbed),
        ("1 Sv",       CDT.radiationDoseEffective),
        ("1 Bq",       CDT.radioactivity),
        ("1 sr",       CDT.solidAngle),
        ("1 m/s",      CDT.speed),
        ("1 K",        CDT.temperature),
        ("1 s",        CDT.time),
        ("1 m3",       CDT.volume),
    ])
    def test_to_si_does_not_raise(self, lexical, datatype):
        lit = Literal(lexical, datatype=datatype)
        q = lit.toPython()
        si = q.to_si()
        assert si.magnitude is not None
