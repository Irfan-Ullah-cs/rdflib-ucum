"""
UCUMUnit — Python value type for ``cdt:ucumunit`` literals.

Represents a UCUM unit without a numeric magnitude, e.g.::

    Literal("km", datatype=CDT.ucumunit)  →  UCUMUnit("km")

Used primarily as a target argument for ``cdt:convert(?qty, "m"^^cdt:ucumunit)``.
"""
from __future__ import annotations

import pint

from .unit_mapping import cached_parse_unit, get_ureg


class UCUMUnit:
    """A UCUM unit without a numeric value — for ``cdt:ucumunit`` datatype."""

    __slots__ = ("_pint_unit", "_ucum_code")

    def __init__(self, ucum_code: str):
        self._ucum_code = ucum_code.strip()
        self._pint_unit = cached_parse_unit(self._ucum_code)

    @property
    def ucum_code(self) -> str:
        return self._ucum_code

    @property
    def pint_unit(self) -> pint.Unit:
        return self._pint_unit

    def to_lexical(self) -> str:
        return self._ucum_code

    def __str__(self) -> str:
        return self._ucum_code

    def __repr__(self) -> str:
        return f"UCUMUnit('{self._ucum_code}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UCUMUnit):
            try:
                ureg = get_ureg()
                return bool(
                    ureg.Quantity(1, self._pint_unit)
                    == ureg.Quantity(1, other._pint_unit)
                )
            except Exception:
                return self._ucum_code == other._ucum_code
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._ucum_code)
