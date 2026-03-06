# rdflib-ucum

**UCUM custom datatypes for RDFLib** — unit-aware equality, comparison, arithmetic, and SPARQL operator support for physical quantity literals.

```python
import rdflib_ucum  # auto-registers everything
from rdflib import Literal, Graph, Namespace

CDT = Namespace("https://w3id.org/cdt/")

# Unit-aware equality: 1 km == 1000 m ✅
a = Literal("1 km", datatype=CDT.length)
b = Literal("1000 m", datatype=CDT.length)
assert a.eq(b)  # True
```

## What This Does

A **standalone pip-installable package** that adds 35 CDT (Custom DataTypes) to RDFLib, enabling physical quantity support in RDF graphs and SPARQL queries. Mirrors the [jena-ucum-lib](https://github.com/Irfan-Ullah-cs/jena-ucum) for Apache Jena.

### Comparison with Jena

| Feature | Jena (2018 fork) | jena-ucum-lib (2024) | **rdflib-ucum** |
|---|---|---|---|
| Datatype registration | ✅ TypeMapper | ✅ TypeMapper | ✅ `bind()` |
| SPARQL `=` equality | ❌ Required fork | ✅ Custom function | ✅ **Native** via `Literal.eq()` |
| SPARQL `<`, `>`, `<=`, `>=` | ❌ Required fork | ✅ Custom function | ✅ **Native operators** |
| SPARQL `+`, `-`, `*`, `/` | ❌ Required fork | ✅ Custom function | ✅ **Native operators** |
| Python operators | N/A (Java) | N/A (Java) | ✅ `+`, `-`, `>`, `<` on Literals |
| ORDER BY | ❌ Required fork | ⚠️ Workaround | ✅ **Native** |
| Standalone package | ❌ No | ✅ Yes | ✅ **Yes** |

**Key advantage over Jena**: In Jena, operator overloading (`=`, `<`, `>`, `+`) was impossible standalone and required forking the Jena core. In RDFLib, ALL operators work standalone.

## Installation

```bash
pip install -e .
```

Dependencies: `rdflib>=7.0.0`, `pint>=0.23`. Optional: `ucumvert` for full UCUM grammar support.

## Usage

### Basic: Create and Parse Quantity Literals

```python
import rdflib_ucum
from rdflib import Literal, Namespace

CDT = Namespace("https://w3id.org/cdt/")

lit = Literal("1.2 km", datatype=CDT.length)
q = lit.toPython()  # UCUMQuantity(1.2, 'km')
print(q.magnitude)  # 1.2
print(q.ucum_unit)  # 'km'
```

### Python Operators

```python
a = Literal("5 km", datatype=CDT.length)
b = Literal("200 m", datatype=CDT.length)

c = a + b           # Literal("5.2 km", datatype=CDT.length)
d = a - b           # Literal("4.8 km", datatype=CDT.length)
a > b               # True  (unit-aware)
a.eq(b)             # False (value-aware SPARQL equality)
```

### SPARQL: Native Operators

```python
from rdflib import Graph, URIRef, Namespace

CDT = Namespace("https://w3id.org/cdt/")
EX = Namespace("http://example.org/")

g = Graph()
g.bind("cdt", "https://w3id.org/cdt/")
g.add((EX.bridge, EX.length, Literal("1.2 km", datatype=CDT.length)))
g.add((EX.road,   EX.length, Literal("500 m",  datatype=CDT.length)))

# Equality (unit-aware)
results = g.query('''
    PREFIX cdt: <https://w3id.org/cdt/>
    SELECT ?s WHERE {
        ?s <http://example.org/length> ?len .
        FILTER(?len = "1200 m"^^cdt:length)
    }
''')  # Finds bridge (1.2 km == 1200 m)

# Comparison
results = g.query('''
    PREFIX cdt: <https://w3id.org/cdt/>
    SELECT ?s WHERE {
        ?s <http://example.org/length> ?len .
        FILTER(?len > "1 km"^^cdt:length)
    }
''')  # Finds bridge

# Arithmetic
results = g.query('''
    PREFIX cdt: <https://w3id.org/cdt/>
    SELECT ?total WHERE {
        ?s <http://example.org/length> ?a .
        ?s2 <http://example.org/length> ?b .
        FILTER(?s != ?s2)
        BIND(?a + ?b AS ?total)
    }
''')

# ORDER BY (unit-aware sorting)
results = g.query('''
    SELECT ?s ?len WHERE {
        ?s <http://example.org/length> ?len .
    } ORDER BY ?len
''')  # road (500 m), bridge (1.2 km)
```

### SPARQL: Custom Functions

```sparql
PREFIX cdt: <https://w3id.org/cdt/>

# Convert units
BIND(cdt:convert(?len, "m"^^cdt:ucumunit) AS ?meters)

# Convert to SI base units
BIND(cdt:toSI(?len) AS ?si)

# Extract value and unit
BIND(cdt:getValue(?len) AS ?val)   # → xsd:double
BIND(cdt:getUnit(?len) AS ?unit)   # → xsd:string

# Check dimension compatibility
FILTER(cdt:sameDimension(?a, ?b))
```

### Unit Conversion (Python API)

```python
from rdflib_ucum import UCUMQuantity

q = UCUMQuantity("1.5 km")
q.to("m")       # UCUMQuantity(1500.0, 'm')
q.to_si()       # UCUMQuantity(1500.0, 'm')
q.magnitude     # 1.5
q.ucum_unit     # 'km'
```

## Supported Datatypes (35 total)

### Generic Types
- `cdt:ucum` — accepts any UCUM unit  (`"1.2 km"^^cdt:ucum`)
- `cdt:ucumunit` — unit only, no value (`"km"^^cdt:ucumunit`)

### 33 Dimension-Specific Types
`cdt:acceleration`, `cdt:amountOfSubstance`, `cdt:angle`, `cdt:area`,
`cdt:catalyticActivity`, `cdt:dimensionless`, `cdt:electricCapacitance`,
`cdt:electricCharge`, `cdt:electricConductance`, `cdt:electricCurrent`,
`cdt:electricInductance`, `cdt:electricPotential`, `cdt:electricResistance`,
`cdt:energy`, `cdt:force`, `cdt:frequency`, `cdt:illuminance`, `cdt:length`,
`cdt:luminousFlux`, `cdt:luminousIntensity`, `cdt:magneticFlux`,
`cdt:magneticFluxDensity`, `cdt:mass`, `cdt:power`, `cdt:pressure`,
`cdt:radiationDoseAbsorbed`, `cdt:radiationDoseEffective`, `cdt:radioactivity`,
`cdt:solidAngle`, `cdt:speed`, `cdt:temperature`, `cdt:time`, `cdt:volume`

## Architecture

```
import rdflib_ucum  →  auto-registers everything:

1. register_datatypes()          ← bind() for all 35 CDT types
   │  Literal("1.2 km", datatype=CDT.length).toPython()
   │  → UCUMQuantity(1.2, 'km')
   │
   │  This enables:
   │  • Literal.eq()    → UCUMQuantity.__eq__  (SPARQL =)
   │  • Literal.__gt__  → UCUMQuantity.__gt__  (ORDER BY)
   │  • Literal.__add__ → UCUMQuantity.__add__ (Python +)

2. install_sparql_patches()      ← monkey-patches SPARQL engine
   │  • RelationalExpression  → allows <, >, <=, >= for CDT types
   │  • AdditiveExpression    → allows +, - for CDT types
   │  • MultiplicativeExpression → allows *, / for CDT types

3. register_sparql_functions()   ← utility SPARQL functions
      • cdt:convert, cdt:toSI, cdt:getValue, cdt:getUnit, cdt:sameDimension
```

## Tech Stack

```
rdflib-ucum
  ├── rdflib    → RDF framework
  └── pint      → Quantity arithmetic, comparison, conversion
  (optional: ucumvert → full UCUM grammar parser + Pint bridge)
```

## References

- [CDT namespace](https://w3id.org/cdt/)
- [UCUM specification](https://ucum.org/ucum)
- [jena-ucum-lib (Java equivalent)](https://github.com/Irfan-Ullah-cs/jena-ucum)
- [Lefrançois & Zimmermann (2016)](https://doi.org/10.1007/978-3-319-34129-3_22) — Supporting Arbitrary Custom Datatypes in RDF and SPARQL
