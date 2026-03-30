"""
test_01_parsing_and_registration.py

Tests for:
- UCUMQuantity lexical parsing (valid and invalid forms)
- RDFLib bind() registration for all 35 CDT types
- Literal.toPython() returns correct Python types
"""
import math

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
        assert q.dimensionality == {"[length]": 1}

    def test_decimal_value(self):
        q = UCUMQuantity("1.5 km")
        assert q.magnitude == 1.5
        assert q.ucum_unit == "km"

    def test_negative_value(self):
        q = UCUMQuantity("-1.5 km")
        assert q.magnitude == -1.5
        assert q.ucum_unit == "km"


    def test_large_magnitude(self):
        q = UCUMQuantity("1e308 m")
        assert math.isfinite(q.magnitude)  # sanity check: not inf or nan
        assert q.magnitude == 100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000.0
        assert q.ucum_unit == "m"   

    def test_small_magnitude(self):
        q = UCUMQuantity("5e-324 m")
        assert math.isfinite(q.magnitude)  # sanity check: not inf or nan
        assert q.magnitude == 5e-324
        assert q.ucum_unit == "m"

    @pytest.mark.xfail(reason="1e309 exceeds sys.float_info.max, overflows to inf")
    def test_large_magnitude(self):
        q = UCUMQuantity("1e309 m")
        assert math.isfinite(q.magnitude)  # sanity check: not inf or nan
        assert q.magnitude == 100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000.0
        assert q.ucum_unit == "m"

    def test_smallest_subnormal(self):
        q = UCUMQuantity("5e-324 m")
        assert math.isfinite(q.magnitude)
        assert q.magnitude > 0.0        # did not underflow to zero
        assert q.ucum_unit == "m"

    def test_underflow_to_zero(self):
        q = UCUMQuantity("1e-325 m")
        assert q.magnitude == 0.0       # underflows to zero

    def test_compound_unit_division(self):
        q = UCUMQuantity("9.8 m/s2")
        assert q.magnitude == 9.8
        assert q.ucum_unit == "m/s2"

    def test_compound_unit_dot(self):
        q = UCUMQuantity("1 kg.m/s2")
        assert q.magnitude == 1.0
        assert q.ucum_unit == "kg.m/s2"
        assert q.dimensionality == {"[mass]": 1, "[length]": 1, "[time]": -2}

    def test_inverse_unit(self):
        q = UCUMQuantity("60 s-1")
        assert q.magnitude == 60.0
        assert q.ucum_unit == "s-1"

    @pytest.mark.xfail(reason="NM is not a valid UCUM unit")
    def test_invalid_unit(self):
        q = UCUMQuantity("60 NM")  # NM is not a valid UCUM unit
        assert q.magnitude == 60.0
        assert q.ucum_unit == "NM"  

    def test_radom_combination_of_ucum_unit(self):
        q = UCUMQuantity("1 s.cd/kg") # s.cd/kg is a valid combination of UCUM units (second × candela / kilogram)
        assert q.magnitude == 1.0
        assert q.ucum_unit == "s.cd/kg"

    def test_radom_combination_of_ucum_unit2(self):
        q = UCUMQuantity("1 [ly].s/[ft_i]") # [ly].s/[ft_i] is a valid combination of UCUM units (light-year × second / foot (international))
        assert q.magnitude == 1.0
        assert q.ucum_unit == "[ly].s/[ft_i]"
        assert q.dimensionality == { "[time]": 1}

    def test_radom_combination_of_ucum_unit3(self):
        """Apothecaries dram per minim squared times speed of light -
        valid UCUM syntax, physically meaningless."""
        q = UCUMQuantity("1 [dr_ap]/[min_us]2.[c]")
        assert q.magnitude == 1
        assert q.ucum_unit == "[dr_ap]/[min_us]2.[c]"

    def test_compound_constant_unit(self):
        """[pi].[c]/[h] — valid UCUM expression combining physical constants."""
        q = UCUMQuantity("1 [pi].[c]/[h]")
        assert q.magnitude == 1
        assert q.ucum_unit == "[pi].[c]/[h]"
        assert math.isfinite(q.magnitude)

    def test_temperature_kelvin(self):
        q = UCUMQuantity("273.15e33 K")
        assert q.magnitude == 273.15e33 
        assert q.ucum_unit == "K"


    def test_dimensionless(self):
        q = UCUMQuantity("1 1")
        assert q.magnitude == 1.0

    def test_no_unit_considered_dimensionless(self):
            UCUMQuantity("1.2")
  

    def test_no_unit_dimensionless(self):
        q = UCUMQuantity("1.2 m/m")
        assert q.magnitude == 1.2
        assert q.ucum_unit == "m/m"
        assert q.dimensionality == {}  # empty dict means dimensionless in pint



# Invalid lexical forms
class TestInvalidLexicalForms:

    @pytest.mark.xfail(reason="Spaces is not allowed at the beginning and end")
    def test_leading_trailing_whitespace(self):
        q = UCUMQuantity("  1.5 km  ")
        assert q.magnitude == 1.5   
        assert q.ucum_unit == "km"


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


# RDFLib bind() registration
class TestRegistration:


    def test_cdt_ucum_returns_ucum_quantity(self):
        lit = Literal("1 m", datatype=ucum)
        assert isinstance(lit.toPython(), UCUMQuantity)

    def test_cdt_ucumunit_returns_ucum_unit(self):
        lit = Literal("km", datatype=ucumunit)
        assert isinstance(lit.toPython(), UCUMUnit)


    def test_ill_typed_literal_falls_back_to_literal(self):
        """Invalid lexical form: RDFLib cannot convert, toPython returns the Literal itself."""
        lit = Literal("not_a_quantity", datatype=CDT.ucum)
        result = lit.toPython()
        assert str(result) == "not_a_quantity"
        assert lit.ill_typed

    def test_register_datatypes_idempotent(self):
        """Calling register_datatypes() multiple times must not raise."""
        from rdflib_ucum.registration import register_datatypes
        register_datatypes()
        register_datatypes()
        lit = Literal("1 km", datatype=CDT.ucum)
        assert isinstance(lit.toPython(), UCUMQuantity)


    def test_toPython_permeability_of_vacuum(self):
        lit = Literal("70 H/m", datatype=CDT.ucum)
        q = lit.toPython()
        assert q.magnitude == 70
        assert q.ucum_unit == "H/m"
        assert q.dimensionality == {"[mass]": 1, "[length]": 1, "[time]": -2, "[current]": -2}

    def test_twice_speed_of_light(self):
        q = UCUMQuantity("2 [c]")
        assert q.magnitude == 2
        assert q.ucum_unit == "[c]"
        assert q.dimensionality == {"[length]": 1, "[time]": -1}

    def test_astronomical_unit(self):
        q = UCUMQuantity("1 au")
        assert q.magnitude == 1
        assert q.ucum_unit == "au"
        assert q.dimensionality == {}
        assert q.to_si().magnitude == 149597870700