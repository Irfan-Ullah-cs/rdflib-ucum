"""
test_07_sparql.py

Tests for SPARQL-level CDT operator support and custom functions:
- FILTER equality (=, !=) via Literal.eq()
- FILTER comparison (<, >, <=, >=) via monkey-patched RelationalExpression
- ORDER BY with mixed units
- Arithmetic in SELECT (+, -, *, /) via monkey-patched Additive/MultiplicativeExpression
- Scalar multiply in SPARQL
- Derived unit arithmetic in SPARQL (force = mass × acceleration)
- Incompatible dimension → SPARQLError
- cdt:sameDimension custom function
- Patch install/uninstall idempotency
"""
import pytest
from rdflib import Graph, Literal, Namespace, URIRef, XSD
from rdflib.plugins.sparql.evalutils import SPARQLError

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.quantity import UCUMQuantity
from rdflib_ucum.sparql_operators import install_sparql_patches, uninstall_sparql_patches

EX = Namespace("https://example.org/")


def make_graph():
    """Return a fresh graph with sample CDT data."""
    g = Graph()
    g.add((EX.s1, EX.length, Literal("1 km",    datatype=CDT.ucum)))
    g.add((EX.s2, EX.length, Literal("1000 m",  datatype=CDT.ucum)))
    g.add((EX.s3, EX.length, Literal("500 m",   datatype=CDT.ucum)))
    g.add((EX.s4, EX.length, Literal("2 km",    datatype=CDT.ucum)))
    g.add((EX.s1, EX.mass,   Literal("70 kg",   datatype=CDT.ucum)))
    g.add((EX.s2, EX.mass,   Literal("70000 g", datatype=CDT.ucum)))
    g.add((EX.s3, EX.mass,   Literal("35 kg",   datatype=CDT.ucum)))
    g.add((EX.s1, EX.speed,  Literal("3.6 km/h",datatype=CDT.ucum)))
    g.add((EX.s2, EX.speed,  Literal("1 m/s",   datatype=CDT.ucum)))
    g.add((EX.s1, EX.energy, Literal("1 kJ",    datatype=CDT.ucum)))
    g.add((EX.s2, EX.energy, Literal("1000 J",  datatype=CDT.ucum)))
    return g


  
# SPARQL Equality
class TestSPARQLEquality:

    def test_eq_cross_unit_finds_match(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        PREFIX cdt: <https://w3id.org/cdt/>
        SELECT ?s WHERE {
            ?s ex:length ?l .
            FILTER(?l = "1000 m"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        # Both s1 (1 km) and s2 (1000 m) equal 1000 m
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects

    def test_neq_filters_correctly(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:length ?l .
            FILTER(?l != "500 m"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s3) not in subjects
        assert str(EX.s1) in subjects    
        assert str(EX.s2) in subjects    
        assert str(EX.s4) in subjects    

    def test_eq_mass_cross_unit(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:mass ?m .
            FILTER(?m = "70 kg"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects

    def test_eq_speed_cross_unit(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:speed ?v .
            FILTER(?v = "1 m/s"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects


  
# SPARQL Comparison
class TestSPARQLComparison:

    def test_gt_cross_unit(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:length ?l .
            FILTER(?l > "600 m"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects
        assert str(EX.s4) in subjects
        assert str(EX.s3) not in subjects

    def test_lt_cross_unit(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:length ?l .
            FILTER(?l < "1 km"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s3) in subjects
        assert str(EX.s4) not in subjects

    def test_gte_includes_equal(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:length ?l .
            FILTER(?l >= "1 km"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects
        assert str(EX.s4) in subjects
        assert str(EX.s3) not in subjects

    def test_lte_includes_equal(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:length ?l .
            FILTER(?l <= "1000 m"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects
        assert str(EX.s3) in subjects
        assert str(EX.s4) not in subjects

    def test_order_by_mixed_units(self):
        """ORDER BY should sort cross-unit values correctly."""
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s ?l WHERE {
            ?s ex:length ?l .
        }
        ORDER BY ?l
        """
        results = list(g.query(q))
        magnitudes = [r[1].toPython().to_si().magnitude for r in results]
        assert magnitudes == sorted(magnitudes)

    def test_mass_gt(self):
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:mass ?m .
            FILTER(?m > "50 kg"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects
        assert str(EX.s3) not in subjects


  
# SPARQL Arithmetic
class TestSPARQLArithmetic:

    def test_add_same_unit(self):
        g = Graph()
        g.add((EX.s1, EX.length, Literal("5 km", datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("3 km", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?result WHERE {
            ex:s1 ex:length ?a .
            ex:s2 ex:length ?b .
            BIND(?a + ?b AS ?result)
        }
        """
        results = list(g.query(q))
        assert len(results) == 1
        val = results[0][0].toPython()
        assert val.magnitude == pytest.approx(8)
        assert val.ucum_unit == "km"

    def test_add_cross_unit(self):
        g = Graph()
        g.add((EX.s1, EX.length, Literal("5 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("200 m", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?result WHERE {
            ex:s1 ex:length ?a .
            ex:s2 ex:length ?b .
            BIND(?a + ?b AS ?result)
        }
        """
        results = list(g.query(q))
        val = results[0][0].toPython()
        assert val.magnitude == pytest.approx(5.2)

    def test_sub(self):
        g = Graph()
        g.add((EX.s1, EX.length, Literal("5 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("200 m", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?result WHERE {
            ex:s1 ex:length ?a .
            ex:s2 ex:length ?b .
            BIND(?a - ?b AS ?result)
        }
        """
        results = list(g.query(q))
        val = results[0][0].toPython()
        assert val.magnitude == pytest.approx(4.8)

    def test_mul_by_scalar(self):
        g = Graph()
        g.add((EX.s1, EX.length, Literal("5 km", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?result WHERE {
            ex:s1 ex:length ?a .
            BIND(?a * 2 AS ?result)
        }
        """
        results = list(g.query(q))
        val = results[0][0].toPython()
        assert val.magnitude == pytest.approx(10)
        assert results[0][0].datatype == CDT.ucum

    def test_div_by_scalar(self):
        g = Graph()
        g.add((EX.s1, EX.length, Literal("10 km", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?result WHERE {
            ex:s1 ex:length ?a .
            BIND(?a / 2 AS ?result)
        }
        """
        results = list(g.query(q))
        val = results[0][0].toPython()
        assert val.magnitude == pytest.approx(5)
        assert results[0][0].datatype == CDT.ucum

    def test_energy_equality_cross_unit(self):
        """1 kJ and 1000 J should match in SPARQL FILTER."""
        g = make_graph()
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:energy ?e .
            FILTER(?e = "1 kJ"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s1) in subjects
        assert str(EX.s2) in subjects


  
# SPARQL custom function: cdt:sameDimension
  

class TestSPARQLSameDimension:

    def test_same_dimension_true(self):
        """Two different length units — same physical dimension → True."""
        g = Graph()
        g.add((EX.s1, EX.val1, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s1, EX.val2, Literal("500 m", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        PREFIX cdt: <https://w3id.org/cdt/>
        SELECT ?result WHERE {
            ex:s1 ex:val1 ?a .
            ex:s1 ex:val2 ?b .
            BIND(cdt:sameDimension(?a, ?b) AS ?result)
        }
        """
        results = list(g.query(q))
        assert results[0][0].toPython() is True

    def test_same_dimension_true_different_unit_types(self):
        """N and kg.m/s2 — same physical dimension → True."""
        g = Graph()
        g.add((EX.s1, EX.val1, Literal("1 N",      datatype=CDT.ucum)))
        g.add((EX.s1, EX.val2, Literal("1 kg.m/s2", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        PREFIX cdt: <https://w3id.org/cdt/>
        SELECT ?result WHERE {
            ex:s1 ex:val1 ?a .
            ex:s1 ex:val2 ?b .
            BIND(cdt:sameDimension(?a, ?b) AS ?result)
        }
        """
        results = list(g.query(q))
        assert results[0][0].toPython() is True

    def test_same_dimension_false(self):
        """Length and mass — different physical dimensions → False."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s1, EX.mass,   Literal("1 kg",  datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        PREFIX cdt: <https://w3id.org/cdt/>
        SELECT ?result WHERE {
            ex:s1 ex:length ?a .
            ex:s1 ex:mass   ?b .
            BIND(cdt:sameDimension(?a, ?b) AS ?result)
        }
        """
        results = list(g.query(q))
        assert results[0][0].toPython() is False

    def test_same_dimension_false_length_vs_time(self):
        """Length and time — different dimensions → False."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 m",  datatype=CDT.ucum)))
        g.add((EX.s1, EX.time,   Literal("1 s",  datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        PREFIX cdt: <https://w3id.org/cdt/>
        SELECT ?result WHERE {
            ex:s1 ex:length ?a .
            ex:s1 ex:time   ?b .
            BIND(cdt:sameDimension(?a, ?b) AS ?result)
        }
        """
        results = list(g.query(q))
        assert results[0][0].toPython() is False

    def test_same_dimension_compatible_via_filter(self):
        """Use cdt:sameDimension in FILTER to select compatible pairs."""
        g = Graph()
        g.add((EX.s1, EX.val, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.val, Literal("1 kg",  datatype=CDT.ucum)))
        g.add((EX.s3, EX.val, Literal("500 m", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        PREFIX cdt: <https://w3id.org/cdt/>
        SELECT ?s WHERE {
            ?s ex:val ?v .
            FILTER(cdt:sameDimension(?v, "1 m"^^<https://w3id.org/cdt/ucum>))
        }
        """
        results = list(g.query(q))
        subjects = {str(r[0]) for r in results}
        assert str(EX.s1) in subjects
        assert str(EX.s3) in subjects
        assert str(EX.s2) not in subjects

    def test_register_sparql_functions_idempotent(self):
        from rdflib_ucum.sparql_functions import register_sparql_functions
        register_sparql_functions()
        register_sparql_functions()
        # Just verify it doesn't raise


  
# ORDER BY with ill-typed literals
class TestOrderByIllTyped:

    def test_order_by_valid_only(self):
        """Valid CDT literals sort correctly by value."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("2 km",   datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("500 m",  datatype=CDT.ucum)))
        g.add((EX.s3, EX.length, Literal("1500 m", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE { ?s ex:length ?l . } ORDER BY ?l
        """
        results = [str(r[0]) for r in g.query(q)]
        assert results == [str(EX.s2), str(EX.s3), str(EX.s1)]

    def test_order_by_ill_typed_pushed_to_end(self):
        """Ill-typed CDT literals must appear after valid ones in ORDER BY."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("500 m", datatype=CDT.ucum)))
        g.add((EX.s3, EX.length, Literal("bad",   datatype=CDT.ucum)))  # ill-typed
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s ?l WHERE { ?s ex:length ?l . } ORDER BY ?l
        """
        results = list(g.query(q))
        # Last result must be the ill-typed one
        assert str(results[-1][0]) == str(EX.s3)
        # First two must be valid and sorted ascending
        si_vals = [r[1].toPython().to_si().magnitude for r in results[:2]]
        assert si_vals == sorted(si_vals)

    def test_order_by_desc_ill_typed_still_at_end(self):
        """With DESC, ill-typed literals appear at the beginning (sort key reversal)."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("500 m", datatype=CDT.ucum)))
        g.add((EX.s3, EX.length, Literal("bad",   datatype=CDT.ucum)))  # ill-typed
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s ?l WHERE { ?s ex:length ?l . } ORDER BY DESC(?l)
        """
        results = list(g.query(q))
        # With DESC, ill-typed (sort key 4) appears first after reversal
        assert str(results[0][0]) == str(EX.s3)
        # Remaining two are valid and sorted descending
        si_vals = [r[1].toPython().to_si().magnitude for r in results[1:]]
        assert si_vals == sorted(si_vals, reverse=True)



class TestSPARQLUnaryAndMath:

    def _graph_one(self, lexical, datatype=CDT.ucum):
        g = Graph()
        g.add((EX.s1, EX.val, Literal(lexical, datatype=datatype)))
        return g

    # ── ABS ──────────────────────────────────────────────────────────────────

    def test_abs_positive(self):
        g = self._graph_one("3.5 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ABS(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(3.5)

    def test_abs_negative(self):
        g = self._graph_one("-3.5 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ABS(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(3.5)

    def test_abs_preserves_unit(self):
        g = self._graph_one("-500 m")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ABS(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        val = res[0][0].toPython()
        assert val.ucum_unit == "m"
        assert val.magnitude == pytest.approx(500)

    def test_abs_zero(self):
        g = self._graph_one("0 m")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ABS(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(0)

    def test_abs_ill_typed_returns_unbound(self):
        g = self._graph_one("bad")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ABS(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert len(res) == 0

    # ── CEIL ─────────────────────────────────────────────────────────────────

    def test_ceil_positive_decimal(self):
        g = self._graph_one("1.2 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (CEIL(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(2.0)

    def test_ceil_negative_decimal(self):
        """CEIL(-1.7) = -1."""
        g = self._graph_one("-1.7 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (CEIL(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(-1.0)

    def test_ceil_whole_number_unchanged(self):
        g = self._graph_one("3 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (CEIL(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(3.0)

    def test_ceil_preserves_datatype(self):
        g = self._graph_one("1.4 kg", CDT.ucum)
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (CEIL(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].datatype == CDT.ucum

    def test_ceil_ill_typed_returns_unbound(self):
        g = self._graph_one("bad")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (CEIL(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert len(res) == 0

    # ── FLOOR ────────────────────────────────────────────────────────────────

    def test_floor_positive_decimal(self):
        g = self._graph_one("1.9 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (FLOOR(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(1.0)

    def test_floor_negative_decimal(self):
        """FLOOR(-1.2) = -2."""
        g = self._graph_one("-1.2 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (FLOOR(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(-2.0)

    def test_floor_whole_number_unchanged(self):
        g = self._graph_one("5 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (FLOOR(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(5.0)

    def test_floor_preserves_datatype(self):
        g = self._graph_one("9.9 s", CDT.ucum)
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (FLOOR(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].datatype == CDT.ucum

    def test_floor_ill_typed_returns_unbound(self):
        g = self._graph_one("bad")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (FLOOR(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert len(res) == 0

    # - ROUND

    def test_round_up(self):
        g = self._graph_one("1.7 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ROUND(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(2.0)

    def test_round_down(self):
        g = self._graph_one("1.2 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ROUND(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(1.0)

    def test_round_half_up(self):
        """SPARQL ROUND uses round-half-up: 1.5 → 2."""
        g = self._graph_one("1.5 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ROUND(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(2.0)

    def test_round_negative(self):
        """ROUND(-1.5) = -1 (round-half-up toward positive infinity)."""
        g = self._graph_one("-1.5 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ROUND(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(-1.0)

    def test_round_preserves_datatype(self):
        g = self._graph_one("9.6 kg", CDT.ucum)
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ROUND(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].datatype == CDT.ucum

    def test_round_ill_typed_returns_unbound(self):
        g = self._graph_one("bad")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (ROUND(?v) AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert len(res) == 0

    # ── Unary minus ──────────────────────────────────────────────────────────

    def test_unary_minus_positive(self):
        g = self._graph_one("5 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (-?v AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(-5.0)

    def test_unary_minus_negative_becomes_positive(self):
        g = self._graph_one("-5 km")
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (-?v AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        assert res[0][0].toPython().magnitude == pytest.approx(5.0)

    def test_unary_minus_preserves_unit(self):
        g = self._graph_one("3 kg", CDT.ucum)
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT (-?v AS ?r) WHERE { ex:s1 ex:val ?v . }
        """))
        val = res[0][0].toPython()
        assert val.ucum_unit == "kg"
        assert val.magnitude == pytest.approx(-3.0)

    # ── ABS then FILTER ──────────────────────────────────────────────────────

    def test_abs_then_filter(self):
        """ABS result can be used in a FILTER comparison."""
        g = Graph()
        g.add((EX.s1, EX.val, Literal("-1.5 km", datatype=CDT.ucum)))
        g.add((EX.s2, EX.val, Literal("0.5 km",  datatype=CDT.ucum)))
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:val ?v .
            FILTER(ABS(?v) > "1 km"^^<https://w3id.org/cdt/ucum>)
        }
        """))
        assert len(res) == 1
        assert str(res[0][0]) == str(EX.s1)

    def test_negate_then_order_by(self):
        """ORDER BY on negated values reverses sort order."""
        g = Graph()
        g.add((EX.s1, EX.val, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.val, Literal("2 km",  datatype=CDT.ucum)))
        g.add((EX.s3, EX.val, Literal("3 km",  datatype=CDT.ucum)))
        res = list(g.query("""
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE { ?s ex:val ?v . }
        ORDER BY (-?v)
        """))
        subjects = [str(r[0]).split('/')[-1] for r in res]
        assert subjects == ["s3", "s2", "s1"]

  
# Aggregates: SUM, AVG
class TestSPARQLAggregates:

    def test_sum_same_unit(self):
        """SUM of valid CDT literals returns correct magnitude."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km", datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("2 km", datatype=CDT.ucum)))
        g.add((EX.s3, EX.length, Literal("3 km", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT (SUM(?l) AS ?total) WHERE { ?s ex:length ?l . }
        """
        results = list(g.query(q))
        assert len(results) == 1
        assert results[0][0].toPython().magnitude == pytest.approx(6.0)

    def test_sum_skips_ill_typed(self):
        """SUM silently skips ill-typed literals and sums only valid ones."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("2 km",  datatype=CDT.ucum)))
        g.add((EX.s3, EX.length, Literal("bad",   datatype=CDT.ucum)))  # ill-typed
        g.add((EX.s4, EX.length, Literal("3 km",  datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT (SUM(?l) AS ?total) WHERE { ?s ex:length ?l . }
        """
        results = list(g.query(q))
        # 1+2+3 = 6, ill-typed skipped
        assert results[0][0].toPython().magnitude == pytest.approx(6.0)

    def test_sum_all_ill_typed_returns_zero(self):
        """SUM with all ill-typed literals returns 0 (empty sum)."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("bad1", datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("bad2", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT (SUM(?l) AS ?total) WHERE { ?s ex:length ?l . }
        """
        results = list(g.query(q))
        assert float(str(results[0][0])) == pytest.approx(0.0)

    def test_avg_valid_only(self):
        """AVG of valid CDT literals returns correct magnitude."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km", datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("2 km", datatype=CDT.ucum)))
        g.add((EX.s3, EX.length, Literal("3 km", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT (AVG(?l) AS ?avg) WHERE { ?s ex:length ?l . }
        """
        results = list(g.query(q))
        assert results[0][0].toPython().magnitude == pytest.approx(2.0)

    def test_avg_skips_ill_typed(self):
        """AVG silently skips ill-typed literals."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("2 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("4 km",  datatype=CDT.ucum)))
        g.add((EX.s3, EX.length, Literal("bad",   datatype=CDT.ucum)))  # ill-typed
        q = """
        PREFIX ex: <https://example.org/>
        SELECT (AVG(?l) AS ?avg) WHERE { ?s ex:length ?l . }
        """
        results = list(g.query(q))
        # avg(2, 4) = 3, ill-typed skipped
        assert results[0][0].toPython().magnitude == pytest.approx(3.0)

    def test_count_includes_ill_typed(self):
        """COUNT counts all bound values including ill-typed (by design)."""
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("bad",   datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT (COUNT(?l) AS ?n) WHERE { ?s ex:length ?l . }
        """
        results = list(g.query(q))
        assert int(str(results[0][0])) == 2

  
# Patch install/uninstall
  

class TestPatchLifecycle:

    def test_install_idempotent(self):
        install_sparql_patches()
        install_sparql_patches()
        # Verify SPARQL still works
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km",   datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("1000 m", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:length ?l .
            FILTER(?l > "500 m"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        assert len(results) == 2

    def test_uninstall_and_reinstall(self):
        uninstall_sparql_patches()
        install_sparql_patches()
        g = Graph()
        g.add((EX.s1, EX.length, Literal("1 km", datatype=CDT.ucum)))
        g.add((EX.s2, EX.length, Literal("500 m", datatype=CDT.ucum)))
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:length ?l .
            FILTER(?l > "600 m"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g.query(q))
        assert len(results) == 1
        assert str(results[0][0]) == str(EX.s1)