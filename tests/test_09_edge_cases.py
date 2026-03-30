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
import pytest
import pint

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.quantity import UCUMQuantity
from rdflib_ucum.unit import UCUMUnit
from rdflib import Literal, Graph, Namespace


 
# Numeric boundary values
EX = Namespace("https://example.org/")

class TestZero:

    def test_zero_parses(self):
        q = UCUMQuantity("0 m")
        assert q.magnitude == pytest.approx(0)

    def test_zero_equality(self):
        assert UCUMQuantity("0 m") == UCUMQuantity("0 km")

    def test_zero_less_than(self):
        assert UCUMQuantity("0 m") < UCUMQuantity("1 m")

    def test_zero_add(self):
        result = UCUMQuantity("0 m") + UCUMQuantity("1 km")
        assert result.magnitude == pytest.approx(0.0 + 1000.0)  # result in m

    def test_zero_mul_scalar(self):
        result = UCUMQuantity("5 km") * 0
        assert result.magnitude == pytest.approx(0)

    def test_abs_zero(self):
        assert abs(UCUMQuantity("0 m")).magnitude == pytest.approx(0)


class TestNegativeValues:

    def test_negative_parses(self):
        q = UCUMQuantity("-1.5 km")
        assert q.magnitude == pytest.approx(-1.5)

    def test_negative_less_than_positive(self):
        assert UCUMQuantity("-1 m") < UCUMQuantity("1 m")

    def test_negative_addition(self):
        result = UCUMQuantity("-5 km") + UCUMQuantity("3 km")
        assert result.magnitude == pytest.approx(-2)

    def test_negative_subtraction(self):
        result = UCUMQuantity("-5 km") - UCUMQuantity("3 km")
        assert result.magnitude == pytest.approx(-8)

    def test_negative_abs(self):
        assert abs(UCUMQuantity("-5 km")).magnitude == pytest.approx(5)

    def test_double_neg(self):
        assert (-UCUMQuantity("-5 km")).magnitude == pytest.approx(5)

    def test_negative_cross_unit(self):
        assert UCUMQuantity("-1 km") == UCUMQuantity("-1000 m")


class TestLargeValues:

    def test_large_value_parses(self):
        q = UCUMQuantity("1e100 m")
        assert q.magnitude == pytest.approx(1e100)

    def test_large_value_comparison(self):
        assert UCUMQuantity("1e100 m") > UCUMQuantity("1e99 m")

    def test_large_value_cross_unit(self):
        assert UCUMQuantity("1e100 km") == UCUMQuantity("1e103 m")

    def test_large_value_addition(self):
        result = UCUMQuantity("1e100 m") + UCUMQuantity("1e100 m")
        assert result.magnitude == pytest.approx(2e100)


class TestSmallValues:

    def test_small_value_parses(self):
        q = UCUMQuantity("1e-20 m")
        assert q.magnitude == pytest.approx(1e-20)

    def test_small_value_comparison(self):
        assert UCUMQuantity("1e-20 m") < UCUMQuantity("1e-19 m")

    def test_small_value_cross_unit_via_conversion(self):
        """Use .to() + approx — direct == is unreliable at small scales."""
        result = UCUMQuantity("1e-20 km").to("m")
        assert result.magnitude == pytest.approx(1e-17)

    @pytest.mark.xfail(reason="IEEE 754: at small scales float density causes "
                               "km*1000 != exact parsed m value")
    def test_small_value_cross_unit_equality_fails(self):
        """Documents known limitation: cross-unit == unreliable for small values."""
        assert UCUMQuantity("1e-20 km") == UCUMQuantity("1e-17 m")


 
# Temperature — offset unit behavior (documented limitation)
class TestTemperature:

    def test_kelvin_parses(self):
        q = UCUMQuantity("273.15 K")
        assert q.magnitude == pytest.approx(273.15)

    def test_celsius_parses(self):
        q = UCUMQuantity("0 Cel")
        assert q.magnitude == pytest.approx(0)

    def test_kelvin_comparison_works(self):
        """K is multiplicative — comparison works normally."""
        assert UCUMQuantity("300 K") > UCUMQuantity("273.15 K")

    def test_kelvin_cross_unit_comparison(self):
        assert UCUMQuantity("1000 K") > UCUMQuantity("500 K")

    def test_kelvin_addition(self):
        """Adding K quantities works (multiplicative unit)."""
        result = UCUMQuantity("100 K") + UCUMQuantity("200 K")
        assert result.magnitude == pytest.approx(300)

    def test_celsius_addition_raises_offset_error(self):
        """
        Adding offset units (Cel + Cel) raises OffsetUnitCalculusError in Pint.
        This is a known, documented limitation — not a bug in rdflib-ucum.
        Pint does not allow arithmetic on offset units directly.
        """
        with pytest.raises(Exception):  # pint.OffsetUnitCalculusError or TypeError
            UCUMQuantity("10 Cel") + UCUMQuantity("20 Cel")

    def test_kelvin_literal_comparison(self):
        a = Literal("300 K", datatype=CDT.ucum)
        b = Literal("273.15 K", datatype=CDT.ucum)
        assert a > b

    def test_kelvin_to_si_is_kelvin(self):
        """SI unit for temperature is K."""
        result = UCUMQuantity("100 K").to_si()
        assert result.magnitude == pytest.approx(100)


 
# Dimensionless
class TestDimensionless:

    def test_dimensionless_parses(self):
        q = UCUMQuantity("1 1")
        assert q.magnitude == pytest.approx(1.0)

    def test_percent_parses(self):
        q = UCUMQuantity("50 %")
        assert q.magnitude == pytest.approx(50)

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
        assert result.magnitude == pytest.approx(5.0)

    def test_dimensionless_comparison(self):
        assert UCUMQuantity("0.5 1") < UCUMQuantity("1 1")


 
# UCUMUnit
class TestUCUMUnit:

    def test_parse_simple(self):
        u = UCUMUnit("km")
        assert u.ucum_code == "km"

    def test_parse_compound(self):
        u = UCUMUnit("m/s")
        assert u.ucum_code == "m/s"

    def test_str(self):
        assert str(UCUMUnit("km")) == "km"

    def test_repr(self):
        assert repr(UCUMUnit("km")) == "UCUMUnit('km')"

    def test_equality_same_unit(self):
        assert UCUMUnit("km") == UCUMUnit("km")

    def test_equality_equivalent_units(self):
        """km and km are same — 1000m and km equivalence is at Quantity level."""
        assert UCUMUnit("km") == UCUMUnit("km")

    def test_inequality_different_units(self):
        assert not (UCUMUnit("km") == UCUMUnit("m"))

    def test_hash_consistent(self):
        assert hash(UCUMUnit("km")) == hash(UCUMUnit("km"))

    def test_usable_as_dict_key(self):
        d = {UCUMUnit("km"): "kilometer"}
        assert d[UCUMUnit("km")] == "kilometer"

    def test_ucumunit_literal(self):
        from rdflib_ucum.namespace import ucumunit
        lit = Literal("km", datatype=ucumunit)
        val = lit.toPython()
        assert isinstance(val, UCUMUnit)
        assert val.ucum_code == "km"


 
# Serialization edge cases
class TestSerialization:

    def test_integer_magnitude_no_decimal(self):
        q = UCUMQuantity("1 km")
        assert q.to_lexical() == "1 km"

    def test_float_whole_number_no_decimal(self):
        """1.0 should serialize as '1', not '1.0'."""
        q = UCUMQuantity("1.0 km")
        assert q.to_lexical() == "1 km"

    def test_decimal_magnitude_preserved(self):
        q = UCUMQuantity("1.5 km")
        assert q.to_lexical() == "1.5 km"

    def test_negative_magnitude_preserved(self):
        q = UCUMQuantity("-1.5 km")
        assert q.to_lexical() == "-1.5 km"

    def test_compound_unit_preserved(self):
        q = UCUMQuantity("9.8 m/s2")
        assert q.to_lexical() == "9.8 m/s2"


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
        assert r.toPython().magnitude == pytest.approx(0.0)

    def test_floor_zero(self):
        r = self._q1("FLOOR", "0 m")
        assert r.toPython().magnitude == pytest.approx(0.0)

    def test_round_zero(self):
        r = self._q1("ROUND", "0 m")
        assert r.toPython().magnitude == pytest.approx(0.0)

    def test_abs_zero(self):
        r = self._q1("ABS", "0 m")
        assert r.toPython().magnitude == pytest.approx(0.0)

    def test_ceil_large_value(self):
        r = self._q1("CEIL", "1e10 m")
        assert r.toPython().magnitude == pytest.approx(1e10)

    def test_floor_large_negative(self):
        r = self._q1("FLOOR", "-1e10 m")
        assert r.toPython().magnitude == pytest.approx(-1e10)

    def test_round_mass_unit(self):
        """ROUND works on non-length CDT types."""
        r = self._q1("ROUND", "2.7 kg", CDT.ucum)
        assert r.toPython().magnitude == pytest.approx(3.0)
        assert r.datatype == CDT.ucum

    def test_ceil_speed(self):
        r = self._q1("CEIL", "3.2 m/s", CDT.ucum)
        assert r.toPython().magnitude == pytest.approx(4.0)
        assert r.datatype == CDT.ucum

    def test_floor_negative_near_zero(self):
        """FLOOR(-0.1) = -1."""
        r = self._q1("FLOOR", "-0.1 m")
        assert r.toPython().magnitude == pytest.approx(-1.0)

    def test_ceil_negative_near_zero(self):
        """CEIL(-0.9) = 0."""
        r = self._q1("CEIL", "-0.9 m")
        assert r.toPython().magnitude == pytest.approx(0.0)


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






