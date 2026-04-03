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

  5. SPARQL ``-?x``, ``+?x``, ``ABS``, ``CEIL``, ``FLOOR``, ``ROUND``:
     Blocked by ``numeric()`` which rejects non-XSD datatypes.
     → Patch: intercept CDT types and reconstruct a valid CDT Literal.

Patching strategy
-----------------
For expressions that ARE module-level names in ``parser.py``
(RelationalExpression, AdditiveExpression, MultiplicativeExpression):
  - Patch ``operators.XXX`` AND ``_parser.XXX.evalfn``.

For expressions that are ANONYMOUS ``Comp`` objects embedded inside grammar
rules (UnaryMinus, UnaryPlus, Builtin_ABS, Builtin_CEIL, Builtin_FLOOR,
Builtin_ROUND):
  - Patch ``operators.XXX`` (for direct callers) AND find the ``Comp`` object
    by traversing the pyparsing grammar tree and update its ``evalfn``.
    This is required because each ``g.query(q)`` re-parses the query and
    creates new ``Expr`` objects with the ``evalfn`` captured at that moment.

All patches are applied by ``install_sparql_patches()`` and can be reverted
by ``uninstall_sparql_patches()``.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_DOWN, ROUND_HALF_UP, Decimal

from rdflib import Literal
from rdflib.plugins.sparql import operators
from rdflib.plugins.sparql.evalutils import SPARQLError

from .namespace import is_cdt_datatype
from .quantity import UCUMQuantity
from .exceptions import UCUMDimensionError, UCUMArithmeticError

    
# Original references (saved on install, restored on uninstall)   
_orig_relational = None
_orig_additive = None
_orig_multiplicative = None
_orig_unary_minus = None
_orig_unary_plus = None
_orig_abs = None
_orig_ceil = None
_orig_floor = None
_orig_round = None
_orig_agg_numeric = None
_orig_agg_type_promotion = None
_orig_avg_get_value = None
_orig_Sum_update = None
_orig_Sum_get_value = None
_orig_Avg_update = None
_orig_Avg_get_value = None
_orig_evalOrderBy = None
_installed = False


    
# Grammar traversal helper
def _find_comp_in_grammar(root, target_name, _visited=None):
    """
    Depth-first search through the pyparsing grammar tree for a ``Comp``
    object whose ``.name`` matches ``target_name``.

    pyparsing elements expose sub-expressions via:
    - ``.exprs``  — list (And, Or, MatchFirst, …)
    - ``.expr``   — single (Optional, ZeroOrMore, Suppress, TokenConverter, …)
    """
    from rdflib.plugins.sparql.parserutils import Comp

    if _visited is None:
        _visited = set()

    node_id = id(root)
    if node_id in _visited:
        return None
    _visited.add(node_id)

    if isinstance(root, Comp) and root.name == target_name:
        return root

    # Multi-child nodes
    children = getattr(root, "exprs", None)
    if children:
        for child in children:
            result = _find_comp_in_grammar(child, target_name, _visited)
            if result is not None:
                return result

    # Single-child nodes
    child = getattr(root, "expr", None)
    if child is not None:
        result = _find_comp_in_grammar(child, target_name, _visited)
        if result is not None:
            return result

    return None


def _patch_grammar_comp(parser_module, comp_name, new_fn):
    """
    Find the Comp object named ``comp_name`` in the parser grammar and set
    its ``evalfn`` to ``new_fn``.  Returns the old evalfn for later restore.
    """
    comp = _find_comp_in_grammar(parser_module.QueryUnit, comp_name)
    if comp is not None:
        old = comp.evalfn
        comp.evalfn = new_fn
        return old
    return None


    
# Patched RelationalExpression  (handles  <  >  <=  >= )
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
        except (TypeError, UCUMDimensionError, UCUMArithmeticError) as te:
            raise SPARQLError(*te.args)

    return _orig_relational(e, ctx)


    
# Patched AdditiveExpression  (handles  +  - )
def _patched_AdditiveExpression(e, ctx) -> Literal:
    """
    Drop-in replacement for ``operators.AdditiveExpression``.

    Handles two cases:
    - CDT-first:   ``?cdt_var + ?cdt_var``
    - Numeric-first: ``0 - ?cdt_var``  (e.g. poor-man's negation)
    """
    expr = e.expr
    other = e.other

    if other is None:
        return expr

    # CDT-first operand
    if isinstance(expr, Literal) and is_cdt_datatype(expr.datatype):
        result_qty = expr.toPython()
        result_dt = expr.datatype

        for op, term in zip(e.op, other):
            if not isinstance(term, Literal) or not is_cdt_datatype(term.datatype):
                raise SPARQLError(
                    f"Cannot do arithmetic between CDT literal and non-CDT term: "
                    f"{expr!r} {op} {term!r}"
                )
            term_qty = term.toPython()
            try:
                if op == "+":
                    result_qty = result_qty + term_qty
                else:
                    result_qty = result_qty - term_qty
            except (TypeError, UCUMDimensionError, UCUMArithmeticError) as te:
                raise SPARQLError(*te.args)

        return Literal(result_qty.to_lexical(), datatype=result_dt)

    # Numeric-first operand (e.g. 0 - ?cdt_var)
    if (
        other
        and isinstance(other[0], Literal)
        and is_cdt_datatype(other[0].datatype)
        and isinstance(expr, Literal)
        and not is_cdt_datatype(expr.datatype)
    ):
        try:
            num_val = expr.toPython()
            if not isinstance(num_val, (int, float)):
                return _orig_additive(e, ctx)
            cdt_qty = other[0].toPython()
            first_op = e.op[0]
            if first_op == "+":
                result_qty = UCUMQuantity(num_val + cdt_qty.magnitude, cdt_qty.ucum_unit)
            else:
                result_qty = UCUMQuantity(num_val - cdt_qty.magnitude, cdt_qty.ucum_unit)

            result_dt = other[0].datatype
            for op, term in zip(e.op[1:], other[1:]):
                if isinstance(term, Literal) and is_cdt_datatype(term.datatype):
                    tq = term.toPython()
                    result_qty = result_qty + tq if op == "+" else result_qty - tq
                else:
                    raise SPARQLError(f"Cannot mix CDT and non-CDT in additive chain")

            return Literal(result_qty.to_lexical(), datatype=result_dt)
        except (TypeError, AttributeError):
            pass

    return _orig_additive(e, ctx)


    
# Patched MultiplicativeExpression  (handles  *  / )
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
                except (TypeError, UCUMDimensionError, UCUMArithmeticError) as te:
                    raise SPARQLError(*te.args)
            elif isinstance(term_val, (int, float)):
                try:
                    if op == "*":
                        result_qty = result_qty * term_val
                    else:
                        result_qty = result_qty / term_val
                except (TypeError, ZeroDivisionError, UCUMArithmeticError) as ex:
                    raise SPARQLError(str(ex))
            else:
                raise SPARQLError(
                    f"Cannot do {op} between CDT literal and {type(term_val)}: "
                    f"{expr!r} {op} {term!r}"
                )

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


    
# Shared helper for unary CDT operations
def _cdt_unary(lit, magnitude_op):
    """
    Apply ``magnitude_op`` to the magnitude of a CDT literal, returning a new
    CDT Literal with the same datatype and unit, or ``None`` if ``lit`` is not
    a valid CDT literal.
    """
    if (
        isinstance(lit, Literal)
        and is_cdt_datatype(lit.datatype)
        and not lit.ill_typed
    ):
        qty = lit.toPython()
        if isinstance(qty, UCUMQuantity):
            new_mag = magnitude_op(qty.magnitude)
            result = UCUMQuantity(new_mag, qty.ucum_unit)
            return Literal(result.to_lexical(), datatype=lit.datatype)
    return None


    
# Patched UnaryMinus  (handles  -?x )
def _patched_UnaryMinus(e, ctx) -> Literal:
    r = _cdt_unary(e.expr, lambda m: -m)
    if r is not None:
        return r
    return _orig_unary_minus(e, ctx)


    
# Patched UnaryPlus  (handles  +?x )
def _patched_UnaryPlus(e, ctx) -> Literal:
    r = _cdt_unary(e.expr, lambda m: +m)
    if r is not None:
        return r
    return _orig_unary_plus(e, ctx)


    
# Patched Builtin_ABS  (handles  ABS(?x) )
def _patched_Builtin_ABS(e, ctx) -> Literal:
    r = _cdt_unary(e.arg, abs)
    if r is not None:
        return r
    return _orig_abs(e, ctx)


    
# Patched Builtin_CEIL  (handles  CEIL(?x) )
def _patched_Builtin_CEIL(e, ctx) -> Literal:
    r = _cdt_unary(e.arg, lambda m: float(math.ceil(m)))
    if r is not None:
        return r
    return _orig_ceil(e, ctx)


    
# Patched Builtin_FLOOR  (handles  FLOOR(?x) )
def _patched_Builtin_FLOOR(e, ctx) -> Literal:
    r = _cdt_unary(e.arg, lambda m: float(math.floor(m)))
    if r is not None:
        return r
    return _orig_floor(e, ctx)


    
# Patched Builtin_ROUND  (handles  ROUND(?x) )
def _patched_Builtin_ROUND(e, ctx) -> Literal:
    def _round(m):
        v = float(m)
        return float(int(Decimal(v).quantize(1, ROUND_HALF_UP if v > 0 else ROUND_HALF_DOWN)))

    r = _cdt_unary(e.arg, _round)
    if r is not None:
        return r
    return _orig_round(e, ctx)


    
# Patch 4 — SUM / AVG aggregates
    
# aggregates.py imports `numeric` and `type_promotion` at module load time as
# local names, so patching operators.numeric alone has no effect there.
# We must patch the local references inside the aggregates module.
#
# numeric(CDT_literal) → return magnitude as float (unit is dropped — documented)
# type_promotion(CDT, CDT) → CDT datatypes are unknown to XSD promotion table;
#   return the non-None operand unchanged instead of raising KeyError.

def _patched_agg_numeric(expr):
    if isinstance(expr, Literal) and is_cdt_datatype(expr.datatype):
        if expr.ill_typed:
            # Sum.update only catches NotBoundError; raise it to skip this row
            from rdflib.plugins.sparql.sparql import NotBoundError
            raise NotBoundError
        qty = expr.toPython()
        if isinstance(qty, UCUMQuantity):
            return qty.magnitude
    return _orig_agg_numeric(expr)


def _patched_agg_type_promotion(t1, t2):
    if is_cdt_datatype(t1) or is_cdt_datatype(t2):
        # Both CDT or one CDT + None — return the CDT type
        return t1 if t1 is not None else t2
    return _orig_agg_type_promotion(t1, t2)


# Average.get_value() builds Literal(Decimal/Decimal) with no datatype argument,
# so CDT datatype is always lost.  Fix: pass datatype through for CDT.
def _patched_avg_get_value(self):
    if is_cdt_datatype(self.datatype):
        if self.counter == 0:
            return Literal(0)
        return Literal(self.sum / self.counter, datatype=self.datatype)
    return _orig_avg_get_value(self)



# Patch 6 — Sum.update / Sum.get_value
# Accumulate UCUMQuantity objects so the unit is preserved in the result.
def _patched_Sum_update(self, row, aggregator):
    from rdflib.plugins.sparql.aggregates import _eval
    from rdflib.plugins.sparql.sparql import NotBoundError
    try:
        value = _eval(self.expr, row)
        if isinstance(value, Literal) and is_cdt_datatype(value.datatype):
            if value.ill_typed:
                return
            qty = value.toPython()
            if isinstance(qty, UCUMQuantity):
                if self.distinct and value in self.seen:
                    return
                self._cdt_acc = getattr(self, '_cdt_acc', None)
                self._cdt_acc = qty if self._cdt_acc is None else self._cdt_acc + qty
                self.datatype = value.datatype
                if self.distinct:
                    self.seen.add(value)
                return
    except NotBoundError:
        return
    _orig_Sum_update(self, row, aggregator)

def _patched_Sum_get_value(self):
    acc = getattr(self, '_cdt_acc', None)
    if acc is not None and is_cdt_datatype(self.datatype):
        return Literal(acc.to_lexical(), datatype=self.datatype)
    return _orig_Sum_get_value(self)


# Patch 6 — Average.update / Average.get_value
def _patched_Avg_update(self, row, aggregator):
    from rdflib.plugins.sparql.aggregates import _eval
    from rdflib.plugins.sparql.sparql import NotBoundError
    try:
        value = _eval(self.expr, row)
        if isinstance(value, Literal) and is_cdt_datatype(value.datatype):
            if value.ill_typed:
                return
            qty = value.toPython()
            if isinstance(qty, UCUMQuantity):
                if self.distinct and value in self.seen:
                    return
                self._cdt_acc = getattr(self, '_cdt_acc', None)
                self._cdt_acc = qty if self._cdt_acc is None else self._cdt_acc + qty
                self.datatype = value.datatype
                self.counter += 1
                if self.distinct:
                    self.seen.add(value)
                return
    except Exception:
        return
    _orig_Avg_update(self, row, aggregator)

def _patched_Avg_get_value(self):
    acc = getattr(self, '_cdt_acc', None)
    if acc is not None and is_cdt_datatype(self.datatype):
        if self.counter == 0:
            return Literal(0)
        result = acc / self.counter
        return Literal(result.to_lexical(), datatype=self.datatype)
    return _orig_Avg_get_value(self)

# ---- ORDER BY sort-key wrapper ----

class _CDTSortKey:
    """
    Wrapper that provides a total ordering for CDT literals in ORDER BY.

    Sorts by (dimension_string, SI_magnitude), so mixed-dimension queries
    group by dimension and sort by converted value within each group.
    Python-level operators on UCUMQuantity still raise on incompatible
    dimensions — this wrapper is only used inside evalOrderBy.
    """
    __slots__ = ("_dim", "_si_mag")

    def __init__(self, literal):
        qty = literal.toPython()
        if isinstance(qty, UCUMQuantity):
            self._dim = str(qty.pint_quantity.dimensionality)
            try:
                self._si_mag = float(qty.pint_quantity.to_base_units().magnitude)
            except Exception:
                self._si_mag = float(qty.magnitude)
        else:
            self._dim = ""
            self._si_mag = 0.0

    def __lt__(self, other):
        if isinstance(other, _CDTSortKey):
            if self._dim != other._dim:
                return self._dim < other._dim
            return self._si_mag < other._si_mag
        return True   # CDT sorts before non-CDT within same _val rank

    def __gt__(self, other):
        if isinstance(other, _CDTSortKey):
            if self._dim != other._dim:
                return self._dim > other._dim
            return self._si_mag > other._si_mag
        return False

    def __eq__(self, other):
        if isinstance(other, _CDTSortKey):
            return self._dim == other._dim and self._si_mag == other._si_mag
        return False

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)


def _patched_evalOrderBy(ctx, part):
    """
    Drop-in replacement for ``evaluate.evalOrderBy``.

    Wraps CDT literals in ``_CDTSortKey`` so that mixed-dimension
    ORDER BY produces a deterministic total ordering instead of crashing.
    """
    from rdflib.plugins.sparql.evaluate import evalPart, _val, value

    res = evalPart(ctx, part.p)

    for e in reversed(part.expr):
        reverse = bool(e.order and e.order == "DESC")

        def _safe_key(x, _e=e):
            v = _val(value(x, _e.expr, variables=True))
            # v is (rank, node) — wrap CDT literals for safe sorting
            if isinstance(v, tuple) and len(v) >= 2:
                inner = v[-1]
                if (
                    isinstance(inner, Literal)
                    and is_cdt_datatype(inner.datatype)
                    and not inner.ill_typed
                ):
                    return (v[0], _CDTSortKey(inner))
            return v

        res = sorted(res, key=_safe_key, reverse=reverse)

    return res

# Install / Uninstall
def install_sparql_patches() -> None:
    global _orig_relational, _orig_additive, _orig_multiplicative
    global _orig_unary_minus, _orig_unary_plus
    global _orig_abs, _orig_ceil, _orig_floor, _orig_round
    global _orig_agg_numeric, _orig_agg_type_promotion
    global _orig_avg_get_value
    global _orig_Sum_update, _orig_Sum_get_value
    global _orig_Avg_update, _orig_Avg_get_value
    global _orig_evalOrderBy
    global _installed

    if _installed:
        return
    _installed = True

    # ---- Save originals ----
    _orig_relational = operators.RelationalExpression
    _orig_additive = operators.AdditiveExpression
    _orig_multiplicative = operators.MultiplicativeExpression
    _orig_unary_minus = operators.UnaryMinus
    _orig_unary_plus = operators.UnaryPlus
    _orig_abs = operators.Builtin_ABS
    _orig_ceil = operators.Builtin_CEIL
    _orig_floor = operators.Builtin_FLOOR
    _orig_round = operators.Builtin_ROUND

    # ---- Layer 1: patch operators module ----
    operators.RelationalExpression = _patched_RelationalExpression
    operators.AdditiveExpression = _patched_AdditiveExpression
    operators.MultiplicativeExpression = _patched_MultiplicativeExpression
    operators.UnaryMinus = _patched_UnaryMinus
    operators.UnaryPlus = _patched_UnaryPlus
    operators.Builtin_ABS = _patched_Builtin_ABS
    operators.Builtin_CEIL = _patched_Builtin_CEIL
    operators.Builtin_FLOOR = _patched_Builtin_FLOOR
    operators.Builtin_ROUND = _patched_Builtin_ROUND

    # ---- Patch 4+5+6: aggregates module ----
    try:
        import rdflib.plugins.sparql.aggregates as _agg
        _orig_agg_numeric = _agg.numeric
        _orig_agg_type_promotion = _agg.type_promotion
        _orig_avg_get_value = _agg.Average.get_value
        _orig_Sum_update = _agg.Sum.update
        _orig_Sum_get_value = _agg.Sum.get_value
        _orig_Avg_update = _agg.Average.update
        _orig_Avg_get_value = _agg.Average.get_value
        _agg.numeric = _patched_agg_numeric
        _agg.type_promotion = _patched_agg_type_promotion
        _agg.Sum.update = _patched_Sum_update
        _agg.Sum.get_value = _patched_Sum_get_value
        _agg.Average.update = _patched_Avg_update
        _agg.Average.get_value = _patched_Avg_get_value
    except (ImportError, AttributeError):
        pass

    # ---- Patch evalOrderBy for mixed-dimension ORDER BY ----
    try:
        import rdflib.plugins.sparql.evaluate as _eval_mod
        _orig_evalOrderBy = _eval_mod.evalOrderBy
        _eval_mod.evalOrderBy = _patched_evalOrderBy
    except (ImportError, AttributeError):
        pass

    # ---- Layer 2: patch Comp.evalfn in parser grammar tree ----
    try:
        from rdflib.plugins.sparql import parser as _parser

        for attr, fn in [
            ("RelationalExpression", _patched_RelationalExpression),
            ("AdditiveExpression",   _patched_AdditiveExpression),
            ("MultiplicativeExpression", _patched_MultiplicativeExpression),
        ]:
            if hasattr(_parser, attr):
                getattr(_parser, attr).evalfn = fn

        for comp_name, fn in [
            ("UnaryMinus",   _patched_UnaryMinus),
            ("UnaryPlus",    _patched_UnaryPlus),
            ("Builtin_ABS",  _patched_Builtin_ABS),
            ("Builtin_CEIL", _patched_Builtin_CEIL),
            ("Builtin_FLOOR",_patched_Builtin_FLOOR),
            ("Builtin_ROUND",_patched_Builtin_ROUND),
        ]:
            _patch_grammar_comp(_parser, comp_name, fn)

    except ImportError:
        pass


def uninstall_sparql_patches() -> None:
    global _orig_relational, _orig_additive, _orig_multiplicative
    global _orig_unary_minus, _orig_unary_plus
    global _orig_abs, _orig_ceil, _orig_floor, _orig_round
    global _orig_agg_numeric, _orig_agg_type_promotion
    global _orig_avg_get_value
    global _orig_Sum_update, _orig_Sum_get_value
    global _orig_Avg_update, _orig_Avg_get_value
    global _orig_evalOrderBy
    global _installed

    if not _installed:
        return
    _installed = False

    # ---- Layer 1: restore operators module ----
    if _orig_relational:
        operators.RelationalExpression = _orig_relational
    if _orig_additive:
        operators.AdditiveExpression = _orig_additive
    if _orig_multiplicative:
        operators.MultiplicativeExpression = _orig_multiplicative
    if _orig_unary_minus:
        operators.UnaryMinus = _orig_unary_minus
    if _orig_unary_plus:
        operators.UnaryPlus = _orig_unary_plus
    if _orig_abs:
        operators.Builtin_ABS = _orig_abs
    if _orig_ceil:
        operators.Builtin_CEIL = _orig_ceil
    if _orig_floor:
        operators.Builtin_FLOOR = _orig_floor
    if _orig_round:
        operators.Builtin_ROUND = _orig_round

    # ---- Layer 2: restore Comp.evalfn ----
    try:
        from rdflib.plugins.sparql import parser as _parser

        for attr, orig in [
            ("RelationalExpression",    _orig_relational),
            ("AdditiveExpression",      _orig_additive),
            ("MultiplicativeExpression",_orig_multiplicative),
        ]:
            if orig and hasattr(_parser, attr):
                getattr(_parser, attr).evalfn = orig

        for comp_name, orig in [
            ("UnaryMinus",   _orig_unary_minus),
            ("UnaryPlus",    _orig_unary_plus),
            ("Builtin_ABS",  _orig_abs),
            ("Builtin_CEIL", _orig_ceil),
            ("Builtin_FLOOR",_orig_floor),
            ("Builtin_ROUND",_orig_round),
        ]:
            if orig:
                _patch_grammar_comp(_parser, comp_name, orig)

    except ImportError:
        pass

    # ---- Restore aggregates module ----
    try:
        import rdflib.plugins.sparql.aggregates as _agg
        if _orig_agg_numeric:
            _agg.numeric = _orig_agg_numeric
        if _orig_agg_type_promotion:
            _agg.type_promotion = _orig_agg_type_promotion
        if _orig_avg_get_value:
            _agg.Average.get_value = _orig_avg_get_value
        if _orig_Sum_update:
            _agg.Sum.update = _orig_Sum_update
        if _orig_Sum_get_value:
            _agg.Sum.get_value = _orig_Sum_get_value
        if _orig_Avg_update:
            _agg.Average.update = _orig_Avg_update
        if _orig_Avg_get_value:
            _agg.Average.get_value = _orig_Avg_get_value
    except ImportError:
        pass

    # ---- Restore evalOrderBy ----
    try:
        import rdflib.plugins.sparql.evaluate as _eval_mod
        if _orig_evalOrderBy:
            _eval_mod.evalOrderBy = _orig_evalOrderBy
    except ImportError:
        pass

    _orig_relational = None
    _orig_additive = None
    _orig_multiplicative = None
    _orig_unary_minus = None
    _orig_unary_plus = None
    _orig_abs = None
    _orig_ceil = None
    _orig_floor = None
    _orig_round = None
    _orig_agg_numeric = None
    _orig_agg_type_promotion = None
    _orig_avg_get_value = None
    _orig_Sum_update = None
    _orig_Sum_get_value = None
    _orig_Avg_update = None
    _orig_Avg_get_value = None
    _orig_evalOrderBy = None