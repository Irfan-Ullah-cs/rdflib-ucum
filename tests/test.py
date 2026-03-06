"""
ill_typed_behavior.py

Comprehensive investigation of CDT literal behavior across:
  1. Loading from Turtle
  2. Printing / reading back
  3. Equality (SPARQL FILTER =)
  4. Inequality (SPARQL FILTER !=)
  5. Comparison (SPARQL FILTER <, >, <=, >=)
  6. Arithmetic (SPARQL BIND +, -, *, /)
  7. ORDER BY — mixed valid CDT types + ill-typed + XSD types

Run with:
    python ill_typed_behavior.py
"""
import rdflib_ucum
from rdflib import Graph, Literal as RDFLiteral

SEP = "=" * 60
CDT_NS = "https://w3id.org/cdt/"

TTL = """
@prefix ex:  <https://example.org/> .
@prefix cdt: <https://w3id.org/cdt/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# --- Valid CDT literals (different units, same dimension: length) ---
ex:v1  ex:length  "500 m"^^cdt:length .
ex:v2  ex:length  "1 km"^^cdt:length .
ex:v3  ex:length  "2 km"^^cdt:length .
ex:v4  ex:length  "1500 m"^^cdt:length .

# --- Valid CDT literals (mass dimension) ---
ex:m1  ex:mass    "70 kg"^^cdt:mass .
ex:m2  ex:mass    "70000 g"^^cdt:mass .

# --- Ill-typed CDT literals ---
ex:b1  ex:length  ""^^cdt:length .
ex:b2  ex:length  "1.4"^^cdt:length .
ex:b3  ex:length  "1m"^^cdt:length .
ex:b4  ex:length  "m"^^cdt:length .
ex:b5  ex:length  "something"^^cdt:length .

# --- XSD numeric literals ---
ex:x1  ex:score   "42"^^xsd:integer .
ex:x2  ex:score   "7"^^xsd:integer .
ex:x3  ex:score   "100"^^xsd:integer .

# --- Arithmetic operands ---
ex:a1  ex:dist    "10 km"^^cdt:length .
ex:a2  ex:dist    "3 km"^^cdt:length .
ex:a3  ex:dist    "500 m"^^cdt:length .
ex:a4  ex:dur     "2 h"^^cdt:time .
"""

g = Graph()

# ---------------------------------------------------------------------------
print(SEP)
print("STEP 1 — Loading Turtle")
print(SEP)
g.parse(data=TTL, format="turtle")
print(f"  Loaded {len(g)} triples — no exception raised.")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 2 — Printing each CDT literal (valid + ill-typed)")
print(SEP)
print(f"  {'subject':10}  {'value':20}  {'ill_typed':10}  toPython()")
print(f"  {'-'*10}  {'-'*20}  {'-'*10}  {'-'*35}")
rows = []
for s, p, o in g:
    if isinstance(o, RDFLiteral) and o.datatype and str(o.datatype).startswith(CDT_NS):
        rows.append((str(s).split("/")[-1], o))
for name, o in sorted(rows):
    val = str(o) if str(o) else "(empty)"
    print(f"  {name:10}  {val:20}  {str(o.ill_typed):10}  {o.toPython()!r}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 3 — SPARQL FILTER = (cross-unit equality)")
print(SEP)
results = list(g.query("""
    SELECT ?s WHERE {
        ?s <https://example.org/length> ?l .
        FILTER(?l = "1000 m"^^<https://w3id.org/cdt/length>)
    }
"""))
print(f"  FILTER(?l = '1000 m')  matched {len(results)} subject(s):")
for r in results:
    print(f"    -> {str(r[0]).split('/')[-1]}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 4 — SPARQL FILTER != (inequality)")
print(SEP)
results = list(g.query("""
    SELECT ?s ?l WHERE {
        ?s <https://example.org/length> ?l .
        FILTER(?l != "1 km"^^<https://w3id.org/cdt/length>)
    }
"""))
print(f"  FILTER(?l != '1 km')  matched {len(results)} subject(s):")
for r in results:
    name = str(r[0]).split("/")[-1]
    val  = str(r[1]) if str(r[1]) else "(empty)"
    print(f"    -> {name:10}  {val}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 5 — SPARQL FILTER comparisons (<, >, <=, >=)")
print(SEP)
for op, threshold in [
    (">",  "600 m"),
    ("<",  "1 km"),
    (">=", "1 km"),
    ("<=", "1500 m"),
]:
    results = list(g.query(f"""
        SELECT ?s WHERE {{
            ?s <https://example.org/length> ?l .
            FILTER(?l {op} "{threshold}"^^<https://w3id.org/cdt/length>)
        }}
    """))
    subjects = ", ".join(str(r[0]).split("/")[-1] for r in results)
    print(f"  FILTER(?l {op:2} '{threshold}')  ->  [{subjects}]")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 6 — SPARQL Arithmetic (BIND)")
print(SEP)

def sparql_bind(g, expr_triple, bind_expr):
    """Helper: run a BIND query and return the result value or a message."""
    q = f"""
    SELECT ?result WHERE {{
        {expr_triple}
        BIND({bind_expr} AS ?result)
    }}
    """
    results = list(g.query(q))
    if results and results[0][0] is not None:
        return str(results[0][0])
    return "NO RESULT"

DIST   = "<https://example.org/dist>"
LENGTH = "<https://example.org/length>"
DUR    = "<https://example.org/dur>"

print(f"  {'operation':35}  result")
print(f"  {'-'*35}  {'-'*25}")

# addition same unit
r = sparql_bind(g,
    f"<https://example.org/a1> {DIST} ?a . <https://example.org/a2> {DIST} ?b .",
    "?a + ?b")
print(f"  {'10 km + 3 km':35}  {r}")

# addition cross unit
r = sparql_bind(g,
    f"<https://example.org/a1> {DIST} ?a . <https://example.org/a3> {DIST} ?b .",
    "?a + ?b")
print(f"  {'10 km + 500 m':35}  {r}")

# subtraction
r = sparql_bind(g,
    f"<https://example.org/a1> {DIST} ?a . <https://example.org/a3> {DIST} ?b .",
    "?a - ?b")
print(f"  {'10 km - 500 m':35}  {r}")

# multiply by scalar
r = sparql_bind(g,
    f"<https://example.org/a1> {DIST} ?a .",
    "?a * 3")
print(f"  {'10 km * 3':35}  {r}")

# divide by scalar
r = sparql_bind(g,
    f"<https://example.org/a1> {DIST} ?a .",
    "?a / 4")
print(f"  {'10 km / 4':35}  {r}")

# incompatible dimensions — length + time
r = sparql_bind(g,
    f"<https://example.org/a1> {DIST} ?a . <https://example.org/a4> {DUR} ?b .",
    "?a + ?b")
print(f"  {'10 km + 2 h (incompatible)':35}  {r if r != 'NO RESULT' else 'NO RESULT (correct — incompatible dimensions)'}")

# arithmetic with ill-typed literal
r = sparql_bind(g,
    f"<https://example.org/a1> {DIST} ?a . <https://example.org/b2> {LENGTH} ?b .",
    "?a + ?b")
print(f"  {'10 km + ill-typed':35}  {r if r != 'NO RESULT' else 'NO RESULT (correct — ill-typed guard)'}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 7 — ORDER BY ASC: valid CDT length + ill-typed mixed")
print(SEP)
results = list(g.query("""
    SELECT ?s ?l WHERE {
        ?s <https://example.org/length> ?l .
    }
    ORDER BY ?l
"""))
print(f"  {'Pos':4}  {'Subject':10}  {'Value':25}  ill_typed")
print(f"  {'-'*4}  {'-'*10}  {'-'*25}  {'-'*9}")
for i, r in enumerate(results, 1):
    name = str(r[0]).split("/")[-1]
    val  = str(r[1]) if str(r[1]) else "(empty)"
    ill  = str(r[1].ill_typed)
    print(f"  {i:<4}  {name:10}  {val:25}  {ill}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 8 — ORDER BY DESC: valid CDT length only")
print(SEP)
results = list(g.query("""
    SELECT ?s ?l WHERE {
        ?s <https://example.org/length> ?l .
        FILTER(?l >= "0 m"^^<https://w3id.org/cdt/length>)
    }
    ORDER BY DESC(?l)
"""))
print(f"  {'Pos':4}  {'Subject':10}  Value")
print(f"  {'-'*4}  {'-'*10}  {'-'*20}")
for i, r in enumerate(results, 1):
    name = str(r[0]).split("/")[-1]
    print(f"  {i:<4}  {name:10}  {r[1]}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 9 — ORDER BY: XSD integers (baseline)")
print(SEP)
results = list(g.query("""
    SELECT ?s ?score WHERE {
        ?s <https://example.org/score> ?score .
    }
    ORDER BY ?score
"""))
print(f"  {'Pos':4}  {'Subject':10}  Value")
print(f"  {'-'*4}  {'-'*10}  {'-'*10}")
for i, r in enumerate(results, 1):
    name = str(r[0]).split("/")[-1]
    print(f"  {i:<4}  {name:10}  {r[1]}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 10 — ORDER BY: CDT mass cross-unit")
print(SEP)
results = list(g.query("""
    SELECT ?s ?m WHERE {
        ?s <https://example.org/mass> ?m .
    }
    ORDER BY ?m
"""))
print(f"  {'Pos':4}  {'Subject':10}  Value")
print(f"  {'-'*4}  {'-'*10}  {'-'*15}")
for i, r in enumerate(results, 1):
    name = str(r[0]).split("/")[-1]
    print(f"  {i:<4}  {name:10}  {r[1]}")