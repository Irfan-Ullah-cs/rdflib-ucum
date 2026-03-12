"""
CDT Namespace — https://w3id.org/cdt/

Defines URIRefs for all 35 CDT datatypes (33 physical quantities + ucum + ucumunit).
Mirrors the Java CDT.java class from jena-ucum-lib.
"""
from rdflib import Namespace, URIRef

CDT_NS = "https://w3id.org/cdt/"
CDT = Namespace(CDT_NS)

 
# All 35 datatype URIs  (33 quantity types + ucum + ucumunit)

# Generic UCUM types (accept any UCUM unit)
ucum = CDT.ucum                                     # "value unit"^^cdt:ucum
ucumunit = CDT.ucumunit                             # "unit"^^cdt:ucumunit  (unit-only, no value)

# 33 dimension-specific quantity types
acceleration = CDT.acceleration
amountOfSubstance = CDT.amountOfSubstance
angle = CDT.angle
area = CDT.area
catalyticActivity = CDT.catalyticActivity
dimensionless = CDT.dimensionless
electricCapacitance = CDT.electricCapacitance
electricCharge = CDT.electricCharge
electricConductance = CDT.electricConductance
electricCurrent = CDT.electricCurrent
electricInductance = CDT.electricInductance
electricPotential = CDT.electricPotential
electricResistance = CDT.electricResistance
energy = CDT.energy
force = CDT.force
frequency = CDT.frequency
illuminance = CDT.illuminance
length = CDT.length
luminousFlux = CDT.luminousFlux
luminousIntensity = CDT.luminousIntensity
magneticFlux = CDT.magneticFlux
magneticFluxDensity = CDT.magneticFluxDensity
mass = CDT.mass
power = CDT.power
pressure = CDT.pressure
radiationDoseAbsorbed = CDT.radiationDoseAbsorbed
radiationDoseEffective = CDT.radiationDoseEffective
radioactivity = CDT.radioactivity
solidAngle = CDT.solidAngle
speed = CDT.speed
temperature = CDT.temperature
time = CDT.time
volume = CDT.volume

 
# Complete list for iteration during registration

ALL_QUANTITY_TYPES: list[URIRef] = [
    acceleration, amountOfSubstance, angle, area, catalyticActivity,
    dimensionless, electricCapacitance, electricCharge, electricConductance,
    electricCurrent, electricInductance, electricPotential, electricResistance,
    energy, force, frequency, illuminance, length, luminousFlux,
    luminousIntensity, magneticFlux, magneticFluxDensity, mass, power,
    pressure, radiationDoseAbsorbed, radiationDoseEffective, radioactivity,
    solidAngle, speed, temperature, time, volume,
]

ALL_CDT_TYPES: list[URIRef] = [ucum, ucumunit] + ALL_QUANTITY_TYPES

# Set for fast membership testing (used by SPARQL monkey-patches)
CDT_DATATYPE_URIS: set[URIRef] = set(ALL_CDT_TYPES)


def is_cdt_datatype(dt: URIRef | None) -> bool:
    """Check whether a datatype URI belongs to the CDT namespace."""
    if dt is None:
        return False
    return dt in CDT_DATATYPE_URIS
