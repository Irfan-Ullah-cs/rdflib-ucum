"""
SPARQL Operator Patches — Enable native operators for CDT quantity types.

From the RDFLib source code investigation:

  1. SPARQL ``=`` / ``!=``:  Already works via ``Literal.eq()`` → value comparison.
     No patch needed.

  2. SPARQL ``<``, ``>``, ``<=``, ``>=``:  Blocked by guard in ``RelationalExpression``
     that rejects non-XSD datatypes.  → Patch: intercept CDT types before the guard.

  3. SPARQL ``+``, ``-``:  Blocked by ``numeric()`` check in ``AdditiveExpression``.
     → Patch: intercept CDT types before ``numeric()`` is called.

  4. SPARQL ``*``, ``/``:  Same ``numeric()`` block in ``MultiplicativeExpression``.
     → Patch: intercept CDT types before ``numeric()`` is called.

All patches are applied by ``install_sparql_patches()`` and can be reverted
by ``uninstall_sparql_patches()``.
"""
from __future__ import annotations

from rdflib import Literal
from rdflib.plugins.sparql import operators
from rdflib.plugins.sparql.evalutils import SPARQLError

from .namespace import is_cdt_datatype, CDT
from .quantity import UCUMQuantity


# ---------------------------------------------------------------------------
# Keep references to the originals so we can (a) delegate and (b) uninstall
# ---------------------------------------------------------------------------
_orig_relational = None
_orig_additive = None
_orig_multiplicative = None
_orig_val = None
_installed = False


# ---------------------------------------------------------------------------
# Patched RelationalExpression  (handles  =  !=  <  >  <=  >= )
# ---------------------------------------------------------------------------

def _patched_RelationalExpression(e, ctx) -> Literal:
    """
    Drop-in replacement for ``operators.RelationalExpression``.

    When both operands are CDT-typed Literals and the operator is an
    ordering operator, skip the XSD guard and delegate to UCUMQuantity
    comparison operators.  Everything else falls through to original.
    """
    expr = e.expr
    other = e.other
    op = e.op

    if other is None:
        return expr

    if (
        op not in ("=", "!=", "IN", "NOT IN")
        and isinstance(expr, Literal)
        and isinstance(other, Literal)
        and is_cdt_datatype(expr.datatype)
        and is_cdt_datatype(other.datatype)
        and not expr.ill_typed  
        and not other.ill_typed 
    ):
        ops = {
            ">":  lambda x, y: x.__gt__(y),
            "<":  lambda x, y: x.__lt__(y),
            ">=": lambda x, y: x.__ge__(y),
            "<=": lambda x, y: x.__le__(y),
        }
        try:
            r = ops[op](expr, other)
            if r is NotImplemented:
                raise SPARQLError(
                    f"Cannot compare CDT literals: {expr!r} {op} {other!r}"
                )
            return Literal(r)
        except TypeError as te:
            raise SPARQLError(*te.args)

    return _orig_relational(e, ctx)


# ---------------------------------------------------------------------------
# Patched AdditiveExpression  (handles  +  - )
# ---------------------------------------------------------------------------

def _patched_AdditiveExpression(e, ctx) -> Literal:
    """
    Drop-in replacement for ``operators.AdditiveExpression``.

    When the first operand is a CDT Literal, perform quantity arithmetic
    via UCUMQuantity instead of calling ``numeric()``.
    """
    expr = e.expr
    other = e.other

    if other is None:
        return expr

    if isinstance(expr, Literal) and is_cdt_datatype(expr.datatype):
        result_qty = expr.toPython()
        if not isinstance(result_qty, UCUMQuantity):
            raise SPARQLError(f"Ill-typed CDT literal: {expr!r}")
        result_dt = expr.datatype

        for op, term in zip(e.op, other):
            if not isinstance(term, Literal) or not is_cdt_datatype(term.datatype):
                raise SPARQLError(
                    f"Cannot do arithmetic between CDT literal and non-CDT term: "
                    f"{expr!r} {op} {term!r}"
                )
            term_qty = term.toPython()
            if not isinstance(term_qty, UCUMQuantity):
                raise SPARQLError(f"Ill-typed CDT literal: {term!r}")
            try:
                if op == "+":
                    result_qty = result_qty + term_qty
                else:
                    result_qty = result_qty - term_qty
            except TypeError as te:
                raise SPARQLError(*te.args)

        return Literal(result_qty.to_lexical(), datatype=result_dt)

    return _orig_additive(e, ctx)


# ---------------------------------------------------------------------------
# Patched MultiplicativeExpression  (handles  *  / )
# ---------------------------------------------------------------------------

def _patched_MultiplicativeExpression(e, ctx) -> Literal:
    """
    Drop-in replacement for ``operators.MultiplicativeExpression``.

    When the first operand is a CDT Literal, perform quantity arithmetic
    via UCUMQuantity instead of calling ``numeric()``.
    """
    expr = e.expr
    other = e.other

    if other is None:
        return expr

    # CDT * something
    if isinstance(expr, Literal) and is_cdt_datatype(expr.datatype):
        result_qty = expr.toPython()

        for op, term in zip(e.op, other):
            term_val = term.toPython() if isinstance(term, Literal) else term
            if isinstance(term_val, UCUMQuantity):
                try:
                    if op == "*":
                        result_qty = result_qty * term_val
                    else:
                        result_qty = result_qty / term_val
                except TypeError as te:
                    raise SPARQLError(*te.args)
            elif isinstance(term_val, (int, float)):
                try:
                    if op == "*":
                        result_qty = result_qty * term_val
                    else:
                        result_qty = result_qty / term_val
                except (TypeError, ZeroDivisionError) as ex:
                    raise SPARQLError(str(ex))
            else:
                raise SPARQLError(
                    f"Cannot do {op} between CDT literal and {type(term_val)}: "
                    f"{expr!r} {op} {term!r}"
                )

        original_dim = expr.toPython().pint_quantity.dimensionality
        result_dim = result_qty.pint_quantity.dimensionality
        if original_dim != result_dim:
            return Literal(result_qty.to_lexical(), datatype=CDT.ucum)
        else:
            return Literal(result_qty.to_lexical(), datatype=expr.datatype)

    # number * CDT  (reverse order)
    if (
        other
        and isinstance(other[0], Literal)
        and is_cdt_datatype(getattr(other[0], "datatype", None))
        and isinstance(expr, Literal)
        and not is_cdt_datatype(expr.datatype)
    ):
        try:
            num_val = expr.toPython()
            if not isinstance(num_val, (int, float)):
                return _orig_multiplicative(e, ctx)

            result_qty = other[0].toPython()
            first_op = e.op[0]
            if first_op == "*":
                result_qty = num_val * result_qty
            else:
                result_qty = UCUMQuantity(num_val / result_qty.pint_quantity)

            for op, term in zip(e.op[1:], other[1:]):
                term_val = term.toPython() if isinstance(term, Literal) else term
                if isinstance(term_val, UCUMQuantity):
                    result_qty = result_qty * term_val if op == "*" else result_qty / term_val
                elif isinstance(term_val, (int, float)):
                    result_qty = result_qty * term_val if op == "*" else result_qty / term_val

            return Literal(result_qty.to_lexical(), datatype=other[0].datatype)
        except Exception:
            pass

    return _orig_multiplicative(e, ctx)

def _patched_val(v):
    if isinstance(v, Literal) and is_cdt_datatype(v.datatype) and v.ill_typed:
        return (4, v)
    return _orig_val(v)


# ---------------------------------------------------------------------------
# Install / Uninstall
# ---------------------------------------------------------------------------

def install_sparql_patches() -> None:
    """
    Monkey-patch RDFLib's SPARQL operator handlers to support CDT types.

    We must patch THREE places:
    1. ``operators.XXXExpression`` — the module-level function
    2. ``parser.XXXExpression.evalfn`` — the Comp object that stores
       function references at module load time via ``Comp.setEvalFn()``.
    3. ``evaluate._val`` — the sort key function used by ORDER BY.
       Must patch evaluate._val directly because evaluate.py imports _val
       with ``from evalutils import _val``, creating its own local reference.

    Safe to call multiple times.
    """
    global _orig_relational, _orig_additive, _orig_multiplicative, _orig_val, _installed

    if _installed:
        return
    _installed = True

    # Save originals
    _orig_relational = operators.RelationalExpression
    _orig_additive = operators.AdditiveExpression
    _orig_multiplicative = operators.MultiplicativeExpression

    # Patch 1: Module-level function references
    operators.RelationalExpression = _patched_RelationalExpression
    operators.AdditiveExpression = _patched_AdditiveExpression
    operators.MultiplicativeExpression = _patched_MultiplicativeExpression

    # Patch 2: Parser Comp objects (store evalfn at module load time)
    try:
        from rdflib.plugins.sparql import parser as _parser
        if hasattr(_parser, "RelationalExpression"):
            _parser.RelationalExpression.evalfn = _patched_RelationalExpression
        if hasattr(_parser, "AdditiveExpression"):
            _parser.AdditiveExpression.evalfn = _patched_AdditiveExpression
        if hasattr(_parser, "MultiplicativeExpression"):
            _parser.MultiplicativeExpression.evalfn = _patched_MultiplicativeExpression
    except ImportError:
        pass

    # Patch 3: _val in evaluate.py for ORDER BY sort key
    from rdflib.plugins.sparql import evaluate as _evaluate
    _orig_val = _evaluate._val
    _evaluate._val = _patched_val


def uninstall_sparql_patches() -> None:
    """Remove the monkey-patches and restore original behavior."""
    global _orig_relational, _orig_additive, _orig_multiplicative, _orig_val, _installed

    if not _installed:
        return
    _installed = False

    if _orig_relational is not None:
        operators.RelationalExpression = _orig_relational
    if _orig_additive is not None:
        operators.AdditiveExpression = _orig_additive
    if _orig_multiplicative is not None:
        operators.MultiplicativeExpression = _orig_multiplicative

    try:
        from rdflib.plugins.sparql import parser as _parser
        if _orig_relational and hasattr(_parser, "RelationalExpression"):
            _parser.RelationalExpression.evalfn = _orig_relational
        if _orig_additive and hasattr(_parser, "AdditiveExpression"):
            _parser.AdditiveExpression.evalfn = _orig_additive
        if _orig_multiplicative and hasattr(_parser, "MultiplicativeExpression"):
            _parser.MultiplicativeExpression.evalfn = _orig_multiplicative
    except ImportError:
        pass

    if _orig_val is not None:
        from rdflib.plugins.sparql import evaluate as _evaluate
        _evaluate._val = _orig_val

    _orig_relational = None
    _orig_additive = None
    _orig_multiplicative = None
    _orig_val = None