"""
METACOD GLP-1 — minimal FHIR R4 Pydantic models.

Covers the FHIR resource subset emitted by `services/fhir_mapper.py`:
  - Bundle (transaction collection)
  - MedicationStatement (one per patient medication)
  - ServiceRequest (one per de-duplicated lab plan item)
  - Observation (triage banner + one per InteractionFinding)
  - ClinicalImpression (forecast summary, GLP-1 decision, future risks)

Plus supporting data types: Reference, CodeableConcept, Coding, Identifier,
Period, Annotation, Quantity, Timing.

Why hand-rolled instead of the `fhir.resources` package:
  - Full FHIR R4 is ~150 resources × ~30 fields = heavy dependency
  - We need 5 resources × ~10 fields = manageable to maintain
  - Clinic deployments often restrict package installs
  - JSON output is byte-identical to canonical FHIR R4 JSON when populated correctly
  - Validation can be added later via `fhir.resources` or `jsonschema` if needed

The intent is to emit valid FHIR R4 JSON that any HL7-conformant EHR can ingest.
Each model uses `model_config = {"extra": "allow"}` so adopters can add resource
extensions without forking this file.

Author: METACOD team
License: proprietary
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Primitive / supporting data types
# ============================================================================

class _FhirBase(BaseModel):
    """Common base allowing extension fields without subclass churn."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Coding(_FhirBase):
    """A single coded value from a coding system."""
    system: Optional[str] = None  # URI of the coding system, e.g. "http://loinc.org"
    code: Optional[str] = None
    display: Optional[str] = None
    version: Optional[str] = None


class CodeableConcept(_FhirBase):
    """A concept that can be coded in one or more systems, optionally with free text."""
    coding: list[Coding] = Field(default_factory=list)
    text: Optional[str] = None


class Identifier(_FhirBase):
    system: Optional[str] = None
    value: Optional[str] = None


class Reference(_FhirBase):
    """Pointer to another resource. Either `reference` (logical/relative URL) or `identifier`."""
    reference: Optional[str] = None  # e.g. "Patient/P-001"
    type: Optional[str] = None        # FHIR resource type
    identifier: Optional[Identifier] = None
    display: Optional[str] = None


class Period(_FhirBase):
    start: Optional[str] = None  # ISO 8601
    end: Optional[str] = None


class Quantity(_FhirBase):
    value: Optional[float] = None
    unit: Optional[str] = None
    system: Optional[str] = None
    code: Optional[str] = None


class Annotation(_FhirBase):
    """Text annotation, used by `note` arrays on many resources."""
    text: str
    time: Optional[str] = None  # ISO 8601
    authorString: Optional[str] = None


class Duration(_FhirBase):
    value: Optional[float] = None
    unit: Optional[str] = None
    system: Optional[str] = None  # "http://unitsofmeasure.org" for UCUM
    code: Optional[str] = None     # UCUM code, e.g. "wk"


class TimingRepeat(_FhirBase):
    boundsDuration: Optional[Duration] = None
    count: Optional[int] = None
    frequency: Optional[int] = None
    period: Optional[float] = None
    periodUnit: Optional[str] = None  # 's' | 'min' | 'h' | 'd' | 'wk' | 'mo' | 'a'


class Timing(_FhirBase):
    repeat: Optional[TimingRepeat] = None
    code: Optional[CodeableConcept] = None


class Meta(_FhirBase):
    versionId: Optional[str] = None
    lastUpdated: Optional[str] = None  # ISO 8601 with timezone
    source: Optional[str] = None
    profile: list[str] = Field(default_factory=list)
    tag: list[Coding] = Field(default_factory=list)


# ============================================================================
# Resources
# ============================================================================

class _Resource(_FhirBase):
    """Common resource fields. Subclasses set `resourceType` as a Literal."""
    id: Optional[str] = None
    meta: Optional[Meta] = None
    language: Optional[str] = None  # e.g. "ru" | "en" | "he"


class MedicationStatement(_Resource):
    """A record of medication being taken by a patient (FHIR R4)."""
    resourceType: Literal["MedicationStatement"] = "MedicationStatement"
    status: str = "active"  # active | completed | entered-in-error | intended | stopped | on-hold | unknown | not-taken
    medicationCodeableConcept: CodeableConcept
    subject: Reference
    effectivePeriod: Optional[Period] = None
    effectiveDateTime: Optional[str] = None
    dateAsserted: Optional[str] = None
    note: list[Annotation] = Field(default_factory=list)
    reasonCode: list[CodeableConcept] = Field(default_factory=list)
    dosage: list[dict[str, Any]] = Field(default_factory=list)  # accepts FHIR Dosage shape


class ServiceRequest(_Resource):
    """An order or request for a clinical service — used for lab plan items."""
    resourceType: Literal["ServiceRequest"] = "ServiceRequest"
    status: str = "active"   # draft | active | on-hold | revoked | completed | entered-in-error | unknown
    intent: str = "order"    # proposal | plan | directive | order | original-order | reflex-order | filler-order | instance-order | option
    category: list[CodeableConcept] = Field(default_factory=list)
    code: CodeableConcept
    subject: Reference
    authoredOn: Optional[str] = None
    occurrenceTiming: Optional[Timing] = None
    reasonCode: list[CodeableConcept] = Field(default_factory=list)
    note: list[Annotation] = Field(default_factory=list)


class Observation(_Resource):
    """A measurement, assertion, or finding — used for triage banner and rule findings."""
    resourceType: Literal["Observation"] = "Observation"
    status: str = "final"  # registered | preliminary | final | amended | corrected | cancelled | entered-in-error | unknown
    category: list[CodeableConcept] = Field(default_factory=list)
    code: CodeableConcept
    subject: Reference
    effectiveDateTime: Optional[str] = None
    issued: Optional[str] = None
    valueString: Optional[str] = None
    valueCodeableConcept: Optional[CodeableConcept] = None
    valueQuantity: Optional[Quantity] = None
    interpretation: list[CodeableConcept] = Field(default_factory=list)
    note: list[Annotation] = Field(default_factory=list)
    derivedFrom: list[Reference] = Field(default_factory=list)


class ClinicalImpressionFinding(_FhirBase):
    """One finding under a ClinicalImpression."""
    itemCodeableConcept: Optional[CodeableConcept] = None
    itemReference: Optional[Reference] = None
    basis: Optional[str] = None


class ClinicalImpression(_Resource):
    """A clinician's assessment for a specific encounter — used to summarize forecast + GLP-1 decision."""
    resourceType: Literal["ClinicalImpression"] = "ClinicalImpression"
    status: str = "completed"  # in-progress | completed | entered-in-error
    subject: Reference
    date: Optional[str] = None
    summary: Optional[str] = None
    finding: list[ClinicalImpressionFinding] = Field(default_factory=list)
    note: list[Annotation] = Field(default_factory=list)


# ============================================================================
# Bundle
# ============================================================================

class BundleEntry(_FhirBase):
    fullUrl: Optional[str] = None  # urn:uuid:... or absolute URL
    resource: dict[str, Any]       # We serialize sub-resources via .model_dump() to dicts before assembling
    # (request and response sub-fields omitted — only needed for transaction submission, not document)


class Bundle(_FhirBase):
    """A transaction or document bundling multiple resources together."""
    resourceType: Literal["Bundle"] = "Bundle"
    id: Optional[str] = None
    meta: Optional[Meta] = None
    type: str = "collection"  # document | message | transaction | transaction-response | batch | batch-response | history | searchset | collection
    timestamp: Optional[str] = None
    total: Optional[int] = None
    entry: list[BundleEntry] = Field(default_factory=list)
