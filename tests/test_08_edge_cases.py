"""
test_09_edge_cases.py

Tests for boundary values, known limitations, and special cases:

Numeric boundaries (Pint float limits):
- Zero, negative, very large (1e308), very small (1e-308)

Temperature (offset units — known Pint limitation):
- K comparisons work (multiplicative)
- Cel + Cel raises OffsetUnitCalculusError — documented behavior
- K to Cel conversion behaviort

Dimensionless:
- "1 1" parses correctly
- "50 %" equality with "0.5 1"
- m/m arithmetic result is dimensionless

UCUMUnit:
- Parse, equality, hash, str, repr

Serialization edge cases:
- Integer magnitude serializes without decimal point
- Float that is whole number serializes without decimal
- Scientific notation magnitude preservation
"""
from math import isfinite

import pytest
import pint

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.quantity import UCUMQuantity
from rdflib_ucum.unit import UCUMUnit
from rdflib import Literal, Graph, Namespace


 
# Numeric boundary values
EX = Namespace("https://example.org/")







class TestLargeValues:

    def test_large_value_parses(self):
        q = UCUMQuantity("1e308 m")
        assert q.magnitude == 1e308
        assert isfinite(q.magnitude)
    @pytest.mark.xfail(reason="IEEE 754: 1e309 overflows to inf, not a finite value")
    def test_large_value_parses2(self):
        q2 = UCUMQuantity("1e309 m")
        assert q2.magnitude == 1e309  # inf in IEEE 754
        assert isfinite(q2.magnitude)

    def test_large_value_comparison(self):
        assert UCUMQuantity("1e308 m") > UCUMQuantity("1e307 m")

    def test_large_value_cross_unit(self):
        assert UCUMQuantity("1e200 km") == UCUMQuantity("1e203 m")




class TestSmallValues:

    def test_small_value_parses(self):
        q = UCUMQuantity("1e-323 m")
        assert q.magnitude ==1e-323
        assert isfinite(q.magnitude) and q.magnitude > 0

    @pytest.mark.xfail(reason="IEEE 754: 1e-324 underflows to 0")
    def test_small_value_parses2(self):
        q = UCUMQuantity("1e-324 m")
        assert q.magnitude ==1e-324  # underflow to 0 in IEEE 754
        assert isfinite(q.magnitude) and q.magnitude > 0

    def test_small_value(self):
        assert UCUMQuantity("1.000000000000003 m") != UCUMQuantity("1.000000000000002 m")

    def test_small_value2(self):
        assert UCUMQuantity("1.0000000000000003 m") == UCUMQuantity("1.0000000000000002 m") # 15, 16 significant digits in IEEE 754

    def test_small_value_comparison(self):
        assert UCUMQuantity("1e-20 m") < UCUMQuantity("1e-19 m")
    
    @pytest.mark.xfail(reason="IEEE 754: at small scales float density causes direct == to fail across units")
    def test_small_value_cross_unit_via_conversion(self):
        """Use .to() + approx — direct == is unreliable at small scales."""
        result = UCUMQuantity("1e-20 km").to("m")
        assert result.magnitude == 1e-17   #9.999999999999999e-18 == 1e-17




 
# Temperature — offset unit behavior (documented limitation)
class TestTemperature:

    def test_kelvin_parses(self):
        q = UCUMQuantity("273.15 K")
        assert q.magnitude == 273.15

    def test_celsius_parses(self):
        q = UCUMQuantity("0 Cel")
        assert q.magnitude == 0
        
    def test_kelvin_comparison_works(self):
        """comparison works normally."""
        assert UCUMQuantity("300 K") > UCUMQuantity("273.15 K")

    def test_kelvin_cross_unit_comparison(self):
        assert UCUMQuantity("300 K") > UCUMQuantity("0 Cel")   # 300K > 273.15K
        assert UCUMQuantity("200 K") < UCUMQuantity("0 Cel")   # 200K < 273.15K

    def test_kelvin_addition(self):
        """Adding K quantities works (multiplicative unit)."""
        result = UCUMQuantity("100 K") + UCUMQuantity("200 K")
        assert result.magnitude == 300

    def test_celsius_addition_raises_offset_error(self):
        """
        Adding offset units (Cel + Cel) raises OffsetUnitCalculusError in Pint.
        This is a known, documented limitation — not a bug in rdflib-ucum.
        Pint does not allow arithmetic on offset units directly.
        """
        with pytest.raises(pint.errors.OffsetUnitCalculusError):
            UCUMQuantity("10 Cel") + UCUMQuantity("20 Cel")

    def test_kelvin_literal_comparison(self):
        a = Literal("100 K", datatype=CDT.ucum)
        b = Literal("90 K", datatype=CDT.ucum)
        assert a > b

 
# Dimensionless
class TestDimensionless:

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

    def test_dimensionless_comparison(self):
        assert UCUMQuantity("0.5 1") < UCUMQuantity("1 1")


 
# UCUMUnit
class TestUCUMUnit:

    def test_parse_simple(self):
        u = UCUMUnit("km")
        assert u.ucum_code == "km"


    def test_equality_same_unit(self):
        assert UCUMUnit("m.kg/kg") == UCUMUnit("m")

    def test_equality_same_unit(self):
        assert UCUMUnit("m/s2") == UCUMUnit("m.s-2")

    def test_inequality_different_units(self):
        assert not (UCUMUnit("km") == UCUMUnit("m"))

    def test_hash_consistent(self):
        assert hash(UCUMUnit("km")) == hash(UCUMUnit("km"))


# SPARQL edge cases: CEIL / FLOOR / ROUND / ABS on boundary values

class TestSPARQLMathEdgeCases:

    def _q1(self, fn, lexical, datatype=CDT.ucum):
        g = Graph()
        g.add((EX.s, EX.v, Literal(lexical, datatype=datatype)))
        res = list(g.query(f"""
        PREFIX ex: <https://example.org/>
        SELECT ({fn}(?v) AS ?r) WHERE {{ ex:s ex:v ?v . }}
        """))
        return res[0][0]

    def test_ceil_zero(self):
        r = self._q1("CEIL", "0 m")
        assert r.toPython().magnitude == 0.0

    def test_floor_zero(self):
        r = self._q1("FLOOR", "0 m")
        assert r.toPython().magnitude == 0.0

    def test_round_zero(self):
        r = self._q1("ROUND", "0 m")
        assert r.toPython().magnitude == 0.0

    def test_abs(self):
        r = self._q1("ABS", "-1 m")
        assert r.toPython().magnitude ==1

    def test_round_mass_unit(self):
        """ROUND works on non-length CDT types."""
        r = self._q1("ROUND", "2.7 kg", CDT.ucum)
        assert r.toPython().magnitude == 3.0
        assert r.datatype == CDT.ucum

    def test_ceil_speed(self):
        r = self._q1("CEIL", "3.2 m/s", CDT.ucum)
        assert r.toPython().magnitude == 4.0
        assert r.datatype == CDT.ucum

    def test_floor_negative_near_zero(self):
        """FLOOR(-0.1) = -1."""
        r = self._q1("FLOOR", "-0.1 m")
        assert r.toPython().magnitude == -1.0

    def test_ceil_negative_near_zero(self):
        """CEIL(-0.9) = 0."""
        r = self._q1("CEIL", "-0.9 m")
        assert r.toPython().magnitude == 0.0


# SPARQL edge cases: dimensionless in SPARQL expressions
# ---------------------------------------------------------------------------

class TestSPARQLDimensionless:

    def test_filter_dimensionless_equality(self):
        """50% == 0.5 in a SPARQL FILTER."""
        g = Graph()
        g.add((EX.s1, EX.v, Literal("50 %",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.v, Literal("0.5 1", datatype=CDT.ucum)))
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:v ?v .
            FILTER(?v = "0.5 1"^^<https://w3id.org/cdt/ucum>)
        }
        """))
        subjects = {str(r[0]) for r in res}
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects

    def test_order_by_dimensionless(self):
        g = Graph()
        g.add((EX.s1, EX.v, Literal("0.25 1", datatype=CDT.ucum)))
        g.add((EX.s2, EX.v, Literal("50 %",   datatype=CDT.ucum)))
        g.add((EX.s3, EX.v, Literal("0.1 1",  datatype=CDT.ucum)))
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT ?s ?v WHERE { ?s ex:v ?v . }
        ORDER BY ?v
        """))
        magnitudes = [r[1].toPython().to_si().magnitude for r in res]
        assert magnitudes == sorted(magnitudes)






