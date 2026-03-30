"""
rdflib-ucum — UCUM custom datatypes for RDFLib
===============================================

Usage::

    import rdflib_ucum          # <- auto-registers everything
    from rdflib import Graph, Literal, Namespace

    CDT = Namespace("https://w3id.org/cdt/")

    # Create quantity literals
    a = Literal("1 km", datatype=CDT.ucum)
    b = Literal("1000 m", datatype=CDT.ucum)

    # Unit-aware equality  (works in both Python and SPARQL)
    assert a.eq(b)          # True — SPARQL path
    assert a.toPython() == b.toPython()  # True — Python path

Architecture
------------
On ``import rdflib_ucum``:

1. ``register_datatypes()`` calls ``rdflib.term.bind()`` for CDT types.
   This makes ``Literal.value`` return ``UCUMQuantity`` objects, enabling
   value-space equality, ordering, and arithmetic.

2. ``install_sparql_patches()`` monkey-patches RDFLib's SPARQL engine for
   native ``<``, ``>``, ``+``, ``-``, ``*``, ``/`` operators on CDT types.

3. ``register_sparql_functions()`` adds utility functions: ``cdt:sameDimension``.
"""

__version__ = "0.1.0"

# Public API
from .namespace import CDT, CDT_NS, is_cdt_datatype, ALL_CDT_TYPES
from .quantity import UCUMQuantity
from .unit import UCUMUnit
from .unit_mapping import get_ureg
from .registration import register_datatypes
from .sparql_operators import install_sparql_patches, uninstall_sparql_patches
from .sparql_functions import register_sparql_functions

__all__ = [
    # Namespace
    "CDT", "CDT_NS", "is_cdt_datatype", "ALL_CDT_TYPES", 
    # Value types
    "UCUMQuantity", "UCUMUnit", "get_ureg",
    # Registration
    "register_datatypes",
    # SPARQL
    "install_sparql_patches", "uninstall_sparql_patches", "register_sparql_functions",
]

# ---------------------------------------------------------------------------
# AUTO-REGISTER on import  (like Jena's ServiceLoader auto-discovery)
# ---------------------------------------------------------------------------

register_datatypes()
install_sparql_patches()
register_sparql_functions()
