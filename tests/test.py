"""
end_user_simulation.py

Simulates what an end user sees when loading a Turtle file
containing both valid and invalid CDT literals, then running
common SPARQL queries on it.

Run with:
    python end_user_simulation.py
"""
import rdflib_ucum
from rdflib import Graph

TTL = """
@prefix ex:  <https://example.org/> .
@prefix cdt: <https://w3id.org/cdt/> .

ex:alice  ex:length  "1 km"^^cdt:length .
ex:bob    ex:length  "500 m"^^cdt:length .
ex:carol  ex:length  "2 km"^^cdt:length .
ex:bad1   ex:length  ""^^cdt:length .
ex:bad2   ex:length  "1.4"^^cdt:length .
ex:bad3   ex:length  "km"^^cdt:length .
ex:bad4   ex:length  "1m"^^cdt:length .
"""

SEP = "=" * 60

# ---------------------------------------------------------------------------
print(SEP)
print("STEP 1 — Loading the Turtle file")
print(SEP)
g = Graph()
g.parse(data=TTL, format="turtle")
print(f"Loaded {len(g)} triples — no error raised.")
print("(Any 'Failed to convert' warnings above came from RDFLib internally)")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 2 — Reading all values back")
print(SEP)
for s, p, o in sorted(g, key=lambda x: str(x[0])):
    val = o.toPython()
    ill = getattr(o, "ill_typed", False)
    print(f"  {str(s).split('/')[-1]:8}  value={str(val):30}  ill_typed={ill}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 3 — FILTER equality: who has length = 1 km ?")
print("(User expects: alice, because 1 km = 1000 m not 500 m)")
print(SEP)
results = list(g.query("""
    SELECT ?s WHERE {
        ?s <https://example.org/length> ?l .
        FILTER(?l = "1 km"^^<https://w3id.org/cdt/length>)
    }
"""))
if results:
    for r in results:
        print(f"  → {str(r[0]).split('/')[-1]}")
else:
    print("  → No results")
print(f"  (bad1..bad4 silently excluded — no error, just missing)")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 4 — FILTER comparison: who has length > 600 m ?")
print("(User expects: alice=1km, carol=2km)")
print(SEP)
results = list(g.query("""
    SELECT ?s WHERE {
        ?s <https://example.org/length> ?l .
        FILTER(?l > "600 m"^^<https://w3id.org/cdt/length>)
    }
"""))
if results:
    for r in results:
        print(f"  → {str(r[0]).split('/')[-1]}")
else:
    print("  → No results")
print(f"  (bad1..bad4 silently excluded — no error, just missing)")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 5 — ORDER BY length")
print("(User expects: bob=500m, alice=1km, carol=2km, then bad ones somewhere)")
print(SEP)
results = list(g.query("""
    SELECT ?s ?l WHERE {
        ?s <https://example.org/length> ?l .
    }
    ORDER BY ?l
"""))
for r in results:
    name = str(r[0]).split('/')[-1]
    val  = r[1].toPython()
    print(f"  → {name:8}  {str(val)}")
print(f"  (bad subjects appear at unpredictable positions — no error)")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 6 — ARITHMETIC: alice length + bob length")
print("(User expects: 1 km + 500 m = 1.5 km)")
print(SEP)
try:
    results = list(g.query("""
        SELECT ?result WHERE {
            <https://example.org/alice> <https://example.org/length> ?a .
            <https://example.org/bob>   <https://example.org/length> ?b .
            BIND(?a + ?b AS ?result)
        }
    """))
    for r in results:
        print(f"  → {r[0].toPython()}")
except Exception as e:
    print(f"  → ERROR: {type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
print()
print(SEP)
print("STEP 7 — ARITHMETIC with a bad literal: bad4 length + alice length")
print("(User expects: a result or a clear error)")
print(SEP)
try:
    results = list(g.query("""
        SELECT ?result WHERE {
            <https://example.org/bad4>  <https://example.org/length> ?a .
            <https://example.org/alice> <https://example.org/length> ?b .
            BIND(?a + ?b AS ?result)
        }
    """))
    if results:
        for r in results:
            print(f"  → {r[0]}")
    else:
        print("  → No results (silent failure)")
except Exception as e:
    print(f"  → ERROR: {type(e).__name__}: {e}")