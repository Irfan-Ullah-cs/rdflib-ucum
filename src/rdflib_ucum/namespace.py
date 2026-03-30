"""
CDT Namespace — https://w3id.org/cdt/

Defines URIRefs for ucum + ucumunit).
"""
from rdflib import Namespace, URIRef

CDT_NS = "https://w3id.org/cdt/"
CDT = Namespace(CDT_NS)

 
# All 35 datatype URIs  (33 quantity types + ucum + ucumunit)

# Generic UCUM types (accept any UCUM unit)
ucum = CDT.ucum                                     # "value unit"^^cdt:ucum
ucumunit = CDT.ucumunit                             # "unit"^^cdt:ucumunit  (unit-only, no value)


ALL_CDT_TYPES: list[URIRef] = [ucum, ucumunit] 

# Set for fast membership testing (used by SPARQL monkey-patches)
CDT_DATATYPE_URIS: set[URIRef] = set(ALL_CDT_TYPES)


def is_cdt_datatype(dt: URIRef | None) -> bool:
    """Check whether a datatype URI belongs to the CDT namespace."""
    if dt is None:
        return False
    return dt in CDT_DATATYPE_URIS
