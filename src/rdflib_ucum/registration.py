"""
Datatype registration - calls ``rdflib.term.bind()`` for all CDT types.

After ``register_datatypes()`` runs:
  - ``Literal("1.2 km", datatype=CDT.ucum).toPython()`` → ``UCUMQuantity``
  - ``Literal.eq()`` uses ``UCUMQuantity.__eq__`` → unit-aware SPARQL ``=``
  - ``Literal.__gt__`` uses ``UCUMQuantity.__gt__`` → unit-aware ORDER BY
  - ``Literal.__add__`` uses ``UCUMQuantity.__add__`` → Python-level arithmetic
"""
from __future__ import annotations

from rdflib.term import bind

from .namespace import  ucum, ucumunit
from .quantity import UCUMQuantity
from .unit import UCUMUnit


   
# Constructor / Lexicalizer functions  (passed to bind())
def _parse_quantity(lexical: str) -> UCUMQuantity:
    """Constructor: UCUM lexical string → UCUMQuantity."""
    return UCUMQuantity(lexical)


def _serialize_quantity(q: UCUMQuantity) -> str:
    """Lexicalizer: UCUMQuantity → UCUM lexical string."""
    return q.to_lexical()


def _parse_unit(lexical: str) -> UCUMUnit:
    """Constructor for cdt:ucumunit."""
    return UCUMUnit(lexical)


def _serialize_unit(u: UCUMUnit) -> str:
    """Lexicalizer for cdt:ucumunit."""
    return u.to_lexical()


   
# Registration
_registered = False


def register_datatypes() -> None:
    """
    Register datatypes with RDFLib via ``bind()``.

    Safe to call multiple times — only registers once.

    After this call, every ``Literal("...", datatype=cdt:XXX)`` will
    automatically parse its lexical form into a ``UCUMQuantity`` stored
    in ``Literal._value``, enabling value-space equality, ordering, and
    arithmetic through the standard Literal API.
    """
    global _registered
    if _registered:
        return
    _registered = True

    # cdt:ucum  (generic — accepts any UCUM unit)
    bind(
        datatype=ucum,
        pythontype=UCUMQuantity,
        constructor=_parse_quantity,
        lexicalizer=_serialize_quantity,
        datatype_specific=True,
    )

    # cdt:ucumunit  (unit-only datatype)
    bind(
        datatype=ucumunit,
        pythontype=UCUMUnit,
        constructor=_parse_unit,
        lexicalizer=_serialize_unit,
        datatype_specific=True,
    )
