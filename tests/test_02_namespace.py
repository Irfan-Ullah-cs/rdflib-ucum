"""
test_02_namespace.py

Tests for CDT namespace definitions:
- is_cdt_datatype() membership
- Base URI correctness
"""
from rdflib import URIRef, XSD

import rdflib_ucum
from rdflib_ucum.namespace import (
    CDT, CDT_NS,
    ALL_CDT_TYPES,
    ucum, ucumunit,
    is_cdt_datatype

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




class TestCDTTypeCounts:

    def test_all_cdt_types_count(self):
        assert len(ALL_CDT_TYPES) == 2


    def test_all_types_are_uriref(self):
        for uri in ALL_CDT_TYPES:
            assert isinstance(uri, URIRef), f"{uri} is not a URIRef"

    def test_ucum_and_ucumunit_in_all_cdt_types(self):
        assert ucum in ALL_CDT_TYPES
        assert ucumunit in ALL_CDT_TYPES




class TestIsCdtDatatype:

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

    def test_true_for_ucum(self):
        assert is_cdt_datatype(ucum)

    def test_true_for_ucumunit(self):
        assert is_cdt_datatype(ucumunit)
