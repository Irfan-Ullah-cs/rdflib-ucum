# rdflib-ucum

**UCUM custom datatypes for RDFLib** - unit-aware equality, comparison, arithmetic, and SPARQL operator support.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

## Overview

`rdflib-ucum` extends [RDFLib](https://rdflib.readthedocs.io/) with support for the CDT (Custom Datatypes) quantity vocabulary defined by Lefrançois & Zimmermann. The CDT specification defines `cdt:ucum` and related datatypes as `rdfs:Datatype` instances with a formal lexical space: a decimal number (with optional scientific notation), at least one space, and a UCUM unit expression. The value space is pairs `(v, u)` where v is a real number and u is a UCUM unit, with the lexical-to-value mapping normalising to SI base units internally. The full specification is published at [ci.mines-stetienne.fr/lindt/v4/custom_datatypes](https://ci.mines-stetienne.fr/lindt/v4/custom_datatypes).

`import rdflib_ucum` and RDFLib gains the ability to store, compare, sort, and compute with physical quantities both in Python and inside SPARQL queries.

The unit parsing and conversion pipeline is built on two libraries:

- **[ucumvert](https://github.com/dalito/ucumvert)** parses [UCUM](https://ucum.org/) unit codes (e.g. `km/h`, `kg.m/s2`, `eV`, `kPa`) into a Pint-compatible registry via `PintUcumRegistry`.
- **[Pint](https://pint.readthedocs.io/)** handles all dimensional analysis, unit conversion, and arithmetic, tracking physical dimensions through every operation so that `2 kg * 3 m/s2` knows it equals `6 N`.

On `import rdflib_ucum`, three things happen automatically:

1. **`register_datatypes()`** calls `rdflib.term.bind()` for all CDT types, so `Literal.toPython()` returns a `UCUMQuantity` instead of a raw string, enabling value-space equality, ordering, and arithmetic through the standard Literal API.
2. **`install_sparql_patches()`** monkey-patches RDFLib's SPARQL engine to intercept CDT-typed literals before the XSD-only guards block them, unlocking native `<`, `>`, `<=`, `>=`, `+`, `-`, `*`, `/` in FILTER and BIND expressions.
3. **`register_sparql_functions()`** registers utility functions under the `cdt:` namespace such as `cdt:sameDimension`.

Parsed units are cached via `lru_cache` for performance.

## Installation

```bash
pip install "rdflib-ucum @ git+https://github.com/Irfan-Ullah-cs/rdflib-ucum.git"
```

**Dependencies:** `rdflib >= 7.0.0`, `pint >= 0.23`, `ucumvert`

## Quick Start

```python
import rdflib_ucum  # auto-registers everything on import
from rdflib import Literal
from rdflib_ucum import CDT

a = Literal("1 km",   datatype=CDT.length)
b = Literal("1000 m", datatype=CDT.length)

assert a.toPython() == b.toPython()  # True - unit-aware equality
assert a.toPython() > Literal("500 m", datatype=CDT.length).toPython()
```

## Python API

`UCUMQuantity` is the core value type, created automatically when you call `.toPython()` on a CDT Literal, or directly:

```python
from rdflib_ucum.quantity import UCUMQuantity

q = UCUMQuantity("3.6 km/h")
q.magnitude    # 3.6
q.ucum_unit    # 'km/h'

q.to("m/s").magnitude                                          # 1.0
UCUMQuantity("1 eV").to_si().magnitude                         # 1.602176634e-19
UCUMQuantity("1 N").same_dimension(UCUMQuantity("1 kg.m/s2"))  # True
```

Arithmetic tracks and transforms physical dimensions through Pint, producing compound units automatically:

```python
# Addition and subtraction - cross-unit, result in left operand's unit
UCUMQuantity("5 km")  + UCUMQuantity("200 m")    # 5.2 km
UCUMQuantity("1 h")   + UCUMQuantity("30 min")   # 1.5 h
UCUMQuantity("1 kPa") + UCUMQuantity("500 Pa")   # 1.5 kPa

# Multiplication and division - dimension-changing
UCUMQuantity("100 m") / UCUMQuantity("10 s")     # 10.0 m/s
UCUMQuantity("2 kg")  * UCUMQuantity("3 m/s2")   # 6.0 kg.m/s2  (== 6 N)
UCUMQuantity("10 N")  * UCUMQuantity("5 m")      # 50.0 N.m     (== 50 J)
UCUMQuantity("100 J") / UCUMQuantity("10 s")     # 10.0 J/s     (== 10 W)
UCUMQuantity("10 V")  * UCUMQuantity("2 A")      # 20.0 V.A     (== 20 W)
UCUMQuantity("10 V")  / UCUMQuantity("2 A")      # 5.0 V/A      (== 5 Ohm)

# Chained physics - kinetic energy: KE = 0.5 * m * v^2
m  = UCUMQuantity("2 kg")
v  = UCUMQuantity("3 m/s")
ke = UCUMQuantity("0.5 1") * m * v * v           # 9.0 J
```

UCUM's full notation is supported including SI prefixes, compound units, derived equivalences, and negative exponents:

```python
UCUMQuantity("1 N")   == UCUMQuantity("1 kg.m/s2")        # True
UCUMQuantity("1 Pa")  == UCUMQuantity("1 kg/(m.s2)")       # True
UCUMQuantity("1 Ohm") == UCUMQuantity("1 kg.m2/(A2.s3)")   # True
UCUMQuantity("1 V")   == UCUMQuantity("1 kg.m2/(A.s3)")    # True
UCUMQuantity("1 s-1") == UCUMQuantity("1 Hz")              # True
UCUMQuantity("1 m/s") == UCUMQuantity("1 m.s-1")           # True
UCUMQuantity("1 MJ")  == UCUMQuantity("1000 kJ")           # True
```

Incompatible dimensions fail loudly:

```python
UCUMQuantity("1 m") + UCUMQuantity("1 kg")  # TypeError: incompatible dimensions
UCUMQuantity("1 m").to("kg")                # pint.DimensionalityError
```

## SPARQL Support

SPARQL operators work natively on CDT quantity literals with no custom functions needed for comparisons and arithmetic.

```sparql
PREFIX cdt: <https://w3id.org/cdt/>
PREFIX ex:  <https://example.org/>

# FILTER with cross-unit comparison - matches "1 km"^^cdt:length because 1 km > 500 m
SELECT ?sensor WHERE {
    ?sensor ex:distance ?d .
    FILTER(?d > "500 m"^^cdt:length)
}
```

```sparql
# ORDER BY across mixed units sorts correctly by physical value
SELECT ?s ?length WHERE {
    ?s ex:length ?length .
}
ORDER BY ?length
```

```sparql
# Arithmetic in BIND - "5 km" + "200 m" produces 5.2 km
SELECT ?total WHERE {
    ex:s1 ex:length ?a .
    ex:s2 ex:length ?b .
    BIND(?a + ?b AS ?total)
}
```

The `cdt:sameDimension` function filters by physical compatibility regardless of the unit stored:

```sparql
PREFIX cdt: <https://w3id.org/cdt/>

SELECT ?s WHERE {
    ?s ex:measurement ?v .
    FILTER(cdt:sameDimension(?v, "1 m"^^cdt:length))
}
```

## RDF Roundtrip

CDT literals survive serialization and deserialization cycles with their lexical form and type fully preserved:

```python
from rdflib import Graph, Literal, Namespace
import rdflib_ucum
from rdflib_ucum import CDT

EX = Namespace("https://example.org/")
g  = Graph()
g.add((EX.sensor, EX.speed, Literal("3.6 km/h", datatype=CDT.speed)))

g2  = Graph().parse(data=g.serialize(format="turtle"), format="turtle")
val = list(g2.objects(EX.sensor, EX.speed))[0].toPython()

assert val.magnitude == 3.6
assert val.ucum_unit == "km/h"
```

## Testing the Installation

Create a fresh virtual environment in any folder on your machine:

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
```

Install directly from GitHub:

```bash
pip install "rdflib-ucum[dev] @ git+https://github.com/Irfan-Ullah-cs/rdflib-ucum.git"
```

Verify it installed correctly:

```bash
python -c "import rdflib_ucum; print(rdflib_ucum.__version__)"
```

To run the full test suite, clone the repo and run pytest from inside it:

```bash
git clone https://github.com/Irfan-Ullah-cs/rdflib-ucum.git
cd rdflib-ucum
pip install -e ".[dev]"
pytest
```

## References

- Lefrançois, M. & Zimmermann, A. (2018). *The Unified Code for Units of Measure in RDF: cdt:ucum and other UCUM Datatypes*. ESWC 2018 (Demo).
- Lefrançois, M. & Zimmermann, A. (2016). *Supporting Arbitrary Custom Datatypes in RDF and SPARQL*. ESWC 2016.
- [CDT specification v4](https://ci.mines-stetienne.fr/lindt/v4/custom_datatypes) - formal definition of the `cdt:ucum` datatype and related quantity types
- [UCUM specification](https://ucum.org/ucum) - the standard for unit codes
- [Pint documentation](https://pint.readthedocs.io/) - dimensional analysis and unit conversion engine
- [ucumvert](https://github.com/dalito/ucumvert) - UCUM parser and Pint registry bridge
