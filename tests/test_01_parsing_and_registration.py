"""
test_01_parsing_and_registration.py

Tests for:
- UCUMQuantity lexical parsing (valid and invalid forms)
- RDFLib bind() registration for all 35 CDT types
- Literal.toPython() returns correct Python types
"""
import pytest
from rdflib import Literal

import rdflib_ucum
from rdflib_ucum import CDT
from rdflib_ucum.namespace import ALL_QUANTITY_TYPES, ucum, ucumunit
from rdflib_ucum.quantity import UCUMQuantity
from rdflib_ucum.unit import UCUMUnit

# Valid lexical forms
class TestValidLexicalForms:

    def test_integer_value(self):
        q = UCUMQuantity("1 m")
        assert q.magnitude == 1
        assert q.ucum_unit == "m"

    def test_decimal_value(self):
        q = UCUMQuantity("1.5 km")
        assert q.magnitude == pytest.approx(1.5)
        assert q.ucum_unit == "km"

    def test_negative_value(self):
        q = UCUMQuantity("-1.5 km")
        assert q.magnitude == pytest.approx(-1.5)

    def test_scientific_notation_lower(self):
        q = UCUMQuantity("1e3 m")
        assert q.magnitude == pytest.approx(1000.0)

    def test_scientific_notation_upper(self):
        q = UCUMQuantity("1E3 m")
        assert q.magnitude == pytest.approx(1000.0)

    def test_scientific_notation_negative_exp(self):
        q = UCUMQuantity("1e-3 m")
        assert q.magnitude == 0.001

    def test_large_value(self):
        q = UCUMQuantity("1e20 m")
        assert q.magnitude == pytest.approx(1e20)

    def test_small_value(self):
        q = UCUMQuantity("1e-20 m")
        assert q.magnitude == pytest.approx(1e-20)

    def test_compound_unit_division(self):
        q = UCUMQuantity("9.8 m/s2")
        assert q.magnitude == pytest.approx(9.8)
        assert q.ucum_unit == "m/s2"

    def test_compound_unit_dot(self):
        q = UCUMQuantity("1 kg.m/s2")
        assert q.magnitude == pytest.approx(1.0)
        assert q.ucum_unit == "kg.m/s2"

    def test_inverse_unit(self):
        q = UCUMQuantity("60 s-1")
        assert q.magnitude == pytest.approx(60.0)
        assert q.ucum_unit == "s-1"

    def test_leading_trailing_whitespace(self):
        q = UCUMQuantity("  1.5 km  ")
        assert q.magnitude == pytest.approx(1.5)
        assert q.ucum_unit == "km"

    def test_temperature_kelvin(self):
        q = UCUMQuantity("273.15 K")
        assert q.magnitude == pytest.approx(273.15)

    def test_temperature_celsius(self):
        q = UCUMQuantity("0 Cel")
        assert q.magnitude == pytest.approx(0)

    def test_dimensionless(self):
        q = UCUMQuantity("1 1")
        assert q.magnitude == pytest.approx(1.0)


  
# Invalid lexical forms
class TestInvalidLexicalForms:

    def test_missing_unit(self):
        with pytest.raises(ValueError):
            UCUMQuantity("1.2")

    def test_unit_only(self):
        with pytest.raises(ValueError):
            UCUMQuantity("km")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            UCUMQuantity("")

    def test_no_space(self):
        with pytest.raises(ValueError):
            UCUMQuantity("1km")

    def test_whitespace_only(self):
        with pytest.raises(ValueError):
            UCUMQuantity("   ")

    def test_numeric_no_unit_raises(self):
        with pytest.raises(ValueError):
            UCUMQuantity(1.5)  # numeric without unit kwarg

# RDFLib bind() registration
class TestRegistration:

    def test_all_33_quantity_types_return_ucum_quantity(self):
        for dt_uri in ALL_QUANTITY_TYPES:
            lit = Literal("1 m", datatype=dt_uri)
            val = lit.toPython()
            assert isinstance(val, UCUMQuantity), (
                f"Expected UCUMQuantity for {dt_uri}, got {type(val)}"
            )

    def test_cdt_ucum_returns_ucum_quantity(self):
        lit = Literal("1 m", datatype=ucum)
        assert isinstance(lit.toPython(), UCUMQuantity)

    def test_cdt_ucumunit_returns_ucum_unit(self):
        lit = Literal("km", datatype=ucumunit)
        assert isinstance(lit.toPython(), UCUMUnit)

    def test_literal_value_not_none(self):
        lit = Literal("1 km", datatype=CDT.length)
        assert lit.toPython() is not None

    def test_ill_typed_literal_falls_back_to_literal(self):
        """Invalid lexical form: RDFLib cannot convert, toPython returns the Literal itself."""
        lit = Literal("not_a_quantity", datatype=CDT.length)
        result = lit.toPython()
        assert str(result) == "not_a_quantity"
        assert lit.ill_typed

    def test_register_datatypes_idempotent(self):
        """Calling register_datatypes() multiple times must not raise."""
        from rdflib_ucum.registration import register_datatypes
        register_datatypes()
        register_datatypes()
        lit = Literal("1 km", datatype=CDT.length)
        assert isinstance(lit.toPython(), UCUMQuantity)

    def test_toPython_length(self):
        lit = Literal("1.5 km", datatype=CDT.length)
        q = lit.toPython()
        assert q.magnitude == pytest.approx(1.5)
        assert q.ucum_unit == "km"

    def test_toPython_mass(self):
        lit = Literal("70 kg", datatype=CDT.mass)
        q = lit.toPython()
        assert q.magnitude == pytest.approx(70)

    def test_toPython_time(self):
        lit = Literal("3600 s", datatype=CDT.time)
        q = lit.toPython()
        assert q.magnitude == pytest.approx(3600)

    def test_toPython_temperature(self):
        lit = Literal("100 Cel", datatype=CDT.temperature)
        q = lit.toPython()
        assert q.magnitude == pytest.approx(100)

    def test_toPython_acceleration(self):
        lit = Literal("9.8 m/s2", datatype=CDT.acceleration)
        q = lit.toPython()
        assert q.magnitude == pytest.approx(9.8)
        assert q.ucum_unit == "m/s2"

    def test_serialization_roundtrip(self):
        """UCUMQuantity.to_lexical() must reproduce original lexical form."""
        original = "1.5 km"
        q = UCUMQuantity(original)
        assert q.to_lexical() == original

    def test_str_repr(self):
        q = UCUMQuantity("1 m")
        assert str(q) == "1 m"
        assert "UCUMQuantity" in repr(q)