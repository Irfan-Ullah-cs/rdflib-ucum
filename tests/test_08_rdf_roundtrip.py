"""
test_08_rdf_roundtrip.py

Tests for RDF serialization/deserialization roundtrips:
- Turtle serialize → parse → toPython() value preserved
- N-Triples roundtrip
- Compound unit roundtrip
- Graph query after roundtrip
"""
import pytest
from rdflib import Graph, Literal, Namespace

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.quantity import UCUMQuantity

EX = Namespace("https://example.org/")


def roundtrip(g: Graph, fmt: str) -> Graph:
    """Serialize graph to format and parse back."""
    data = g.serialize(format=fmt)
    g2 = Graph()
    g2.parse(data=data, format=fmt)
    return g2


# Turtle roundtrip
class TestTurtleRoundtrip:

    def test_length_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("1.5 km", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert isinstance(val, UCUMQuantity)
        assert val.magnitude == pytest.approx(1.5)
        assert val.ucum_unit == "km"

    def test_mass_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("70 kg", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(70)

    def test_time_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("3600 s", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(3600)

    def test_temperature_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("100 Cel", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(100)

    def test_speed_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("3.6 km/h", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(3.6)
        assert val.ucum_unit == "km/h"

    def test_acceleration_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("9.8 m/s2", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(9.8)

    def test_compound_unit_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("1 kg.m/s2", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(1.0)

    def test_energy_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("1 kJ", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(1.0)
        assert val.ucum_unit == "kJ"

    def test_pressure_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("101.325 kPa", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(101.325)

    def test_frequency_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("50 Hz", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(50)

    def test_electric_current_turtle(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("2.5 A", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(2.5)

    def test_multiple_triples_turtle(self):
        g = Graph()
        g.add((EX.s1, EX.val, Literal("1 km",  datatype=CDT.ucum)))
        g.add((EX.s2, EX.val, Literal("70 kg", datatype=CDT.ucum)))
        g.add((EX.s3, EX.val, Literal("1 h",   datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        assert len(g2) == 3
        for subj, _, obj in g2:
            assert isinstance(obj.toPython(), UCUMQuantity)


   
# N-Triples roundtrip
class TestNTriplesRoundtrip:

    def test_length_ntriples(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("1.5 km", datatype=CDT.ucum)))
        g2 = roundtrip(g, "nt")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert isinstance(val, UCUMQuantity)
        assert val.magnitude == pytest.approx(1.5)

    def test_compound_unit_ntriples(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("9.8 m/s2", datatype=CDT.ucum)))
        g2 = roundtrip(g, "nt")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(9.8)
        assert val.ucum_unit == "m/s2"

    def test_scientific_notation_ntriples(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("1.5e3 m", datatype=CDT.ucum)))
        g2 = roundtrip(g, "nt")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(1500.0)

    def test_negative_value_ntriples(self):
        g = Graph()
        g.add((EX.s, EX.val, Literal("-10 Cel", datatype=CDT.ucum)))
        g2 = roundtrip(g, "nt")
        val = list(g2.objects(EX.s, EX.val))[0].toPython()
        assert val.magnitude == pytest.approx(-10)


   
# Value preservation after roundtrip
class TestValuePreservationAfterRoundtrip:

    def test_equality_preserved_after_turtle_roundtrip(self):
        """1 km and 1000 m should still be equal after roundtrip."""
        g = Graph()
        g.add((EX.s1, EX.val, Literal("1 km",   datatype=CDT.ucum)))
        g.add((EX.s2, EX.val, Literal("1000 m", datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        vals = list(g2.objects(predicate=EX.val))
        assert len(vals) == 2
        a = vals[0].toPython()
        b = vals[1].toPython()
        assert a == b

    def test_sparql_query_after_turtle_roundtrip(self):
        """SPARQL FILTER should still work on a roundtripped graph."""
        g = Graph()
        g.add((EX.s1, EX.val, Literal("1 km",   datatype=CDT.ucum)))
        g.add((EX.s2, EX.val, Literal("500 m",  datatype=CDT.ucum)))
        g2 = roundtrip(g, "turtle")
        q = """
        PREFIX ex: <https://example.org/>
        SELECT ?s WHERE {
            ?s ex:val ?l .
            FILTER(?l > "600 m"^^<https://w3id.org/cdt/ucum>)
        }
        """
        results = list(g2.query(q))
        assert len(results) == 1
        assert str(results[0][0]) == str(EX.s1)


   

