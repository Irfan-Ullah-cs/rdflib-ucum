"""
Custom SPARQL functions registered under the ``cdt:`` namespace.

These supplement the native operator support:
  - ``cdt:sameDimension(?a, ?b)``                         → check compatibility
"""
from __future__ import annotations

from rdflib import Literal, URIRef, XSD
from rdflib.plugins.sparql.operators import register_custom_function

from .namespace import CDT_NS
from .quantity import UCUMQuantity
from .unit import UCUMUnit


# Helper
def _to_qty(lit: Literal) -> UCUMQuantity:
    """Extract UCUMQuantity from a Literal, or raise."""
    val = lit.toPython()
    if isinstance(val, UCUMQuantity):
        return val
    raise TypeError(f"Expected CDT quantity literal, got {type(val)}: {lit!r}")


# Function implementations
def _fn_sameDimension(a_lit: Literal, b_lit: Literal) -> Literal:
    """``cdt:sameDimension(?a, ?b)`` → xsd:boolean."""
    a = _to_qty(a_lit)
    b = _to_qty(b_lit)
    return Literal(a.same_dimension(b), datatype=XSD.boolean)


# Registration
_registered = False


def register_sparql_functions() -> None:
    """Register all CDT SPARQL functions. Safe to call multiple times."""
    global _registered
    if _registered:
        return
    _registered = True

    ns = CDT_NS
   
    register_custom_function(URIRef(f"{ns}sameDimension"), _fn_sameDimension)
