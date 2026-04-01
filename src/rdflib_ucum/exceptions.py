"""
Custom exceptions for rdflib-ucum.

Hierarchy
---------
UCUMError               (base, inherits ValueError)
├── UCUMParseError      bad lexical form,   e.g. "1m", ""
├── UCUMUnitError       invalid unit code,  e.g. "KM", "Newton"
├── UCUMDimensionError  incompatible dims,  e.g. km + kg
└── UCUMArithmeticError arithmetic failure, e.g. division by zero

All inherit from ValueError so existing ``except ValueError`` blocks
in user code and in RDFLib's term.py continue to work unchanged.
"""

__all__ = [
    "UCUMError",
    "UCUMParseError",
    "UCUMUnitError",
    "UCUMDimensionError",
    "UCUMArithmeticError",
]


class UCUMError(ValueError):
    """Base exception for rdflib-ucum."""


class UCUMParseError(UCUMError):
    """Lexical form could not be parsed (e.g. '1m', '')."""


class UCUMUnitError(UCUMError):
    """Unit code is invalid or unknown (e.g. 'KM', 'Newton')."""


class UCUMDimensionError(UCUMError):
    """Incompatible dimensions in operation (e.g. km + kg)."""


class UCUMArithmeticError(UCUMError):
    """Arithmetic error such as division by zero."""