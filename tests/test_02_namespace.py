"""
test_02_namespace.py

Tests for CDT namespace definitions:
- All 35 datatype URIs exist and are distinct
- is_cdt_datatype() membership
- Base URI correctness
"""
import pytest
from rdflib import URIRef, XSD

import rdflib_ucum
from rdflib_ucum.namespace import (
    CDT, CDT_NS,
    ALL_CDT_TYPES, ALL_QUANTITY_TYPES,
    ucum, ucumunit,
    is_cdt_datatype,
    # All 33 quantity URIs
    acceleration, amountOfSubstance, angle, area, catalyticActivity,
    dimensionless, electricCapacitance, electricCharge, electricConductance,
    electricCurrent, electricInductance, electricPotential, electricResistance,
    energy, force, frequency, illuminance, length, luminousFlux,
    luminousIntensity, magneticFlux, magneticFluxDensity, mass, power,
    pressure, radiationDoseAbsorbed, radiationDoseEffective, radioactivity,
    solidAngle, speed, temperature, time, volume,
)


class TestCDTNamespaceURI:

    def test_base_uri(self):
        assert CDT_NS == "https://w3id.org/cdt/"

    def test_namespace_object(self):
        assert str(CDT) == "https://w3id.org/cdt/"

    def test_ucum_uri(self):
        assert str(ucum) == "https://w3id.org/cdt/ucum"

    def test_ucumunit_uri(self):
        assert str(ucumunit) == "https://w3id.org/cdt/ucumunit"

    def test_length_uri(self):
        assert str(length) == "https://w3id.org/cdt/length"

    def test_mass_uri(self):
        assert str(mass) == "https://w3id.org/cdt/mass"


class TestCDTTypeCounts:

    def test_all_cdt_types_count(self):
        assert len(ALL_CDT_TYPES) == 35

    def test_all_quantity_types_count(self):
        assert len(ALL_QUANTITY_TYPES) == 33

    def test_all_types_are_uriref(self):
        for uri in ALL_CDT_TYPES:
            assert isinstance(uri, URIRef), f"{uri} is not a URIRef"

    def test_all_types_distinct(self):
        assert len(set(ALL_CDT_TYPES)) == len(ALL_CDT_TYPES)

    def test_ucum_and_ucumunit_not_in_quantity_types(self):
        assert ucum not in ALL_QUANTITY_TYPES
        assert ucumunit not in ALL_QUANTITY_TYPES

    def test_ucum_and_ucumunit_in_all_cdt_types(self):
        assert ucum in ALL_CDT_TYPES
        assert ucumunit in ALL_CDT_TYPES


class TestAllQuantityURIs:
    """Verify each of the 33 quantity URIs is in ALL_QUANTITY_TYPES."""

    @pytest.mark.parametrize("uri", [
        acceleration, amountOfSubstance, angle, area, catalyticActivity,
        dimensionless, electricCapacitance, electricCharge, electricConductance,
        electricCurrent, electricInductance, electricPotential, electricResistance,
        energy, force, frequency, illuminance, length, luminousFlux,
        luminousIntensity, magneticFlux, magneticFluxDensity, mass, power,
        pressure, radiationDoseAbsorbed, radiationDoseEffective, radioactivity,
        solidAngle, speed, temperature, time, volume,
    ])
    def test_quantity_uri_in_all_quantity_types(self, uri):
        assert uri in ALL_QUANTITY_TYPES

    @pytest.mark.parametrize("uri", [
        acceleration, amountOfSubstance, angle, area, catalyticActivity,
        dimensionless, electricCapacitance, electricCharge, electricConductance,
        electricCurrent, electricInductance, electricPotential, electricResistance,
        energy, force, frequency, illuminance, length, luminousFlux,
        luminousIntensity, magneticFlux, magneticFluxDensity, mass, power,
        pressure, radiationDoseAbsorbed, radiationDoseEffective, radioactivity,
        solidAngle, speed, temperature, time, volume,
    ])
    def test_quantity_uri_starts_with_cdt_ns(self, uri):
        assert str(uri).startswith(CDT_NS)


class TestIsCdtDatatype:

    def test_true_for_all_35(self):
        for uri in ALL_CDT_TYPES:
            assert is_cdt_datatype(uri), f"Expected True for {uri}"

    def test_false_for_xsd_string(self):
        assert not is_cdt_datatype(XSD.string)

    def test_false_for_xsd_integer(self):
        assert not is_cdt_datatype(XSD.integer)

    def test_false_for_xsd_double(self):
        assert not is_cdt_datatype(XSD.double)

    def test_false_for_none(self):
        assert not is_cdt_datatype(None)

    def test_false_for_arbitrary_uri(self):
        assert not is_cdt_datatype(URIRef("https://example.org/mytype"))

    def test_false_for_similar_uri_wrong_ns(self):
        assert not is_cdt_datatype(URIRef("http://w3id.org/cdt/length"))  # http not https

    def test_true_for_ucum(self):
        assert is_cdt_datatype(ucum)

    def test_true_for_ucumunit(self):
        assert is_cdt_datatype(ucumunit)

    def test_true_for_length(self):
        assert is_cdt_datatype(length)
