"""
UCUM ↔ Pint unit translation layer.

Provides the shared PintUcumRegistry singleton and parsing/serialization
helpers used by both UCUMQuantity and UCUMUnit.

Requires ``ucumvert`` — install with::

    pip install rdflib-ucum[ucumvert]
    # or directly: pip install ucumvert

This module is a pure utility layer with no RDFLib dependency.
"""
from __future__ import annotations

import re
from functools import lru_cache

import pint

from rdflib_ucum.exceptions import UCUMUnitError

     
# Singleton PintUcumRegistry
_ureg: pint.UnitRegistry | None = None


def get_ureg() -> pint.UnitRegistry:
    """Return the shared PintUcumRegistry singleton.

    Raises
    ------
    ImportError
        If ``ucumvert`` is not installed.
    """
    global _ureg
    if _ureg is None:
        try:
            from ucumvert import PintUcumRegistry  # type: ignore[import-untyped]
            _ureg = PintUcumRegistry()
        except ImportError as e:
            raise ImportError(
                "rdflib-ucum requires 'ucumvert' for UCUM unit parsing. "
                "Install it with: pip install ucumvert"
            ) from e
    return _ureg


# Regex to split "1.2 km" → ("1.2", "km")
# Note: (.+?) with \s*$ ensures trailing whitespace is NOT captured in group 2
LEXICAL_RE = re.compile(
    r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\ +(.+?)$"
)


     
# Parsing helpers
def ucum_to_pint_unit(ucum_code: str) -> pint.Unit:
    """Convert a UCUM unit code to a Pint Unit via ucumvert."""
    ureg = get_ureg()

    # Strip any accidental whitespace before passing to ucumvert
    ucum_code = ucum_code.strip()

    # Special case: UCUM dimensionless unit "1"
    # ucumvert returns int(1) for from_ucum("1"), not a Quantity
    if ucum_code == "1":
        return ureg.parse_units("dimensionless")

    try:
        result = ureg.from_ucum(ucum_code)
        return result.units
    except Exception as e:
        raise UCUMUnitError(f"Cannot parse UCUM unit code: {ucum_code!r}") from e


@lru_cache(maxsize=512)
def cached_parse_unit(ucum_code: str) -> pint.Unit:
    """Cached version of :func:`ucum_to_pint_unit` for performance."""
    return ucum_to_pint_unit(ucum_code)


def pint_unit_to_ucum(unit: pint.Unit) -> str:
    """Convert a Pint Unit back to its UCUM code string.

    Since PintUcumRegistry parses units from UCUM codes, ``str(unit)``
    preserves the original UCUM representation.
    """
    return str(unit)