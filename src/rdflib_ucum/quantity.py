"""
UCUMQuantity — Python value type for CDT quantity literals.

Wraps ``pint.Quantity`` with UCUM-string parsing, serialization,
and all operator overloads needed for RDFLib Literal integration.

After ``bind()``, RDFLib stores a UCUMQuantity as the ``.value``
of every ``Literal("1.2 km", datatype=CDT.length)``.

Operator chain (from source investigation):
  - Literal.eq()     → self.value == other.value  → UCUMQuantity.__eq__
  - Literal.__gt__   → self.value >  other.value  → UCUMQuantity.__gt__
  - Literal.__add__  → self.toPython() + …        → UCUMQuantity.__add__
"""
from __future__ import annotations

from typing import Union

import pint

from .unit_mapping import (
    get_ureg,
    cached_parse_unit,
    pint_unit_to_ucum,
    LEXICAL_RE,
)


class UCUMQuantity:
    """
    A physical quantity with a numeric value and a UCUM unit.

    This is the Python type that ``rdflib.term.bind()`` maps CDT literals to.
    All operator overloads here are what RDFLib delegates to when comparing,
    adding, or ordering CDT Literals.

    Parameters
    ----------
    value : float | int | str | pint.Quantity
        Numeric magnitude, a full UCUM lexical string like ``"1.2 km"``,
        or an existing Pint Quantity.
    unit : str | None
        UCUM unit code.  Required when *value* is numeric.
    """

    __slots__ = ("_pint_qty", "_ucum_unit")

    def __init__(
        self,
        value: Union[float, int, str, "pint.Quantity"],
        unit: str | None = None,
    ):
        ureg = get_ureg()

        if isinstance(value, pint.Quantity):
            self._pint_qty: pint.Quantity = value
            self._ucum_unit: str = unit or pint_unit_to_ucum(value.units)
            return

        if isinstance(value, str):
            m = LEXICAL_RE.match(value)
            if m:
                mag_str, ucum_code = m.group(1), m.group(2)
                mag = float(mag_str) if ("." in mag_str or "e" in mag_str.lower()) else int(mag_str)
                self._pint_qty = ureg.Quantity(mag, cached_parse_unit(ucum_code))
                self._ucum_unit = ucum_code
                return
            try:
                mag = float(value) if ("." in value or "e" in value.lower()) else int(value)
            except ValueError:
                raise ValueError(f"Cannot parse UCUM quantity: {value!r}")
            if unit is None:
                raise ValueError(f"No unit provided for value: {value!r}")
            self._pint_qty = ureg.Quantity(mag, cached_parse_unit(unit))
            self._ucum_unit = unit
            return

        if unit is None:
            raise ValueError("unit is required when value is numeric")
        self._pint_qty = ureg.Quantity(value, cached_parse_unit(unit))
        self._ucum_unit = unit

    # ---- Properties   ----------

    @property
    def magnitude(self) -> float:
        return float(self._pint_qty.magnitude)

    @property
    def units(self) -> pint.Unit:
        return self._pint_qty.units

    @property
    def ucum_unit(self) -> str:
        return self._ucum_unit

    @property
    def pint_quantity(self) -> pint.Quantity:
        return self._pint_qty

    @property
    def dimensionality(self) -> dict:
        return dict(self._pint_qty.dimensionality)

    # ---- Serialization   -------

    def to_lexical(self) -> str:
        """Serialize back to UCUM lexical form: ``"1.2 km"``."""
        mag = self._pint_qty.magnitude
        if isinstance(mag, float) and mag == int(mag) and "e" not in f"{mag}".lower():
            mag_str = str(int(mag))
        else:
            mag_str = str(mag)
        return f"{mag_str} {self._ucum_unit}"

    def __str__(self) -> str:
        return self.to_lexical()

    def __repr__(self) -> str:
        return f"UCUMQuantity({self._pint_qty.magnitude!r}, '{self._ucum_unit}')"

    # ---- Unit conversion   -----

    def to(self, target_ucum_unit: str) -> UCUMQuantity:
        """Convert to another compatible UCUM unit."""
        converted = self._pint_qty.to(cached_parse_unit(target_ucum_unit))
        return UCUMQuantity(converted, unit=target_ucum_unit)

    def to_si(self) -> UCUMQuantity:
        """Convert to SI base units."""
        return UCUMQuantity(self._pint_qty.to_base_units())

    def same_dimension(self, other: UCUMQuantity) -> bool:
        """Check if two quantities have the same physical dimension."""
        return self._pint_qty.dimensionality == other._pint_qty.dimensionality

    def get_value(self) -> float:
        return self.magnitude

    def get_unit(self) -> str:
        return self._ucum_unit

    # ---- Equality (SPARQL = via Literal.eq → value.__eq__) ----------------

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UCUMQuantity):
            try:
                return bool(self._pint_qty == other._pint_qty)
            except pint.DimensionalityError:
                return False
        return NotImplemented

    def __hash__(self) -> int:
        try:
            si = self._pint_qty.to_base_units()
            return hash((round(float(si.magnitude), 9), str(si.units)))
        except Exception:
            return hash(self.to_lexical())

    # ---- Comparison (SPARQL <, >, <=, >= and ORDER BY) --------------------

    def __lt__(self, other: object) -> bool:
        if isinstance(other, UCUMQuantity):
            try:
                return bool(self._pint_qty < other._pint_qty)
            except pint.DimensionalityError:
                raise TypeError(
                    f"Cannot compare {self._ucum_unit} with {other._ucum_unit}: "
                    f"incompatible dimensions"
                )
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, UCUMQuantity):
            return self.__lt__(other) or self.__eq__(other)
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, UCUMQuantity):
            try:
                return bool(self._pint_qty > other._pint_qty)
            except pint.DimensionalityError:
                raise TypeError(
                    f"Cannot compare {self._ucum_unit} with {other._ucum_unit}: "
                    f"incompatible dimensions"
                )
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, UCUMQuantity):
            return self.__gt__(other) or self.__eq__(other)
        return NotImplemented

    # ---- Arithmetic (SPARQL +, -, *, / and Python ops) --------------------

    def __add__(self, other: object) -> UCUMQuantity:
        if isinstance(other, UCUMQuantity):
            try:
                result = self._pint_qty + other._pint_qty.to(self._pint_qty.units)
                return UCUMQuantity(result, unit=self._ucum_unit)
            except pint.DimensionalityError:
                raise TypeError(
                    f"Cannot add {self._ucum_unit} and {other._ucum_unit}: "
                    f"incompatible dimensions"
                )
        return NotImplemented

    def __sub__(self, other: object) -> UCUMQuantity:
        if isinstance(other, UCUMQuantity):
            try:
                result = self._pint_qty - other._pint_qty.to(self._pint_qty.units)
                return UCUMQuantity(result, unit=self._ucum_unit)
            except pint.DimensionalityError:
                raise TypeError(
                    f"Cannot subtract {other._ucum_unit} from {self._ucum_unit}: "
                    f"incompatible dimensions"
                )
        return NotImplemented

    def __mul__(self, other: object) -> UCUMQuantity:
        if isinstance(other, UCUMQuantity):
            result_pint = self._pint_qty * other._pint_qty
            result_ucum = f"{self._ucum_unit}.{other._ucum_unit}"
            return UCUMQuantity(result_pint, unit=result_ucum)
        if isinstance(other, (int, float)):
            return UCUMQuantity(self._pint_qty * other, unit=self._ucum_unit)
        return NotImplemented

    def __rmul__(self, other: object) -> UCUMQuantity:
        return self.__mul__(other)

    def __truediv__(self, other: object) -> UCUMQuantity:
        if isinstance(other, UCUMQuantity):
            result_pint = self._pint_qty / other._pint_qty
            result_ucum = f"{self._ucum_unit}/{other._ucum_unit}"
            return UCUMQuantity(result_pint, unit=result_ucum)
        if isinstance(other, (int, float)):
            return UCUMQuantity(self._pint_qty / other, unit=self._ucum_unit)
        return NotImplemented

    def __neg__(self) -> UCUMQuantity:
        return UCUMQuantity(-self._pint_qty, unit=self._ucum_unit)

    def __abs__(self) -> UCUMQuantity:
        return UCUMQuantity(abs(self._pint_qty), unit=self._ucum_unit)
