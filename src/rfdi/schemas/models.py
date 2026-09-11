"""Strict dependency-free canonical types; API adapters may wrap these in Pydantic."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class DocumentState(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    PARSED = "PARSED"
    EXTRACTED = "EXTRACTED"
    RECONCILED = "RECONCILED"
    RISK_SCORED = "RISK_SCORED"
    AUTO_ACCEPTED = "AUTO_ACCEPTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"
    FINALIZED = "FINALIZED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    QUARANTINED = "QUARANTINED"


class ReviewDecision(str, Enum):
    ACCEPT = "ACCEPT"
    EDIT = "EDIT"
    REJECT = "REJECT"


@dataclass(frozen=True)
class BBox:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        values = (self.left, self.top, self.right, self.bottom)
        if not all(0 <= value <= 1 for value in values):
            raise ValueError("bbox coordinates must be normalized to [0,1]")
        if self.right < self.left or self.bottom < self.top:
            raise ValueError("bbox has inverted coordinates")


@dataclass(frozen=True)
class Provenance:
    document_hash: str
    source_dataset: str
    extractor: str
    model_revision: str
    prompt_revision: str | None = None


@dataclass(frozen=True)
class Field:
    field_type: str
    raw_value: str
    normalized_value: str | None
    page: int
    bbox: BBox | None
    confidence: float
    source_model: str
    validation_state: str
    criticality: float
    provenance: Provenance

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be in [0,1]")
        if self.page < 0:
            raise ValueError("page must be nonnegative")
        if self.criticality < 0:
            raise ValueError("criticality must be nonnegative")


@dataclass(frozen=True)
class LineItem:
    line_item_id: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    page: int = 0


@dataclass(frozen=True)
class Relation:
    relation_type: str
    source_id: str
    target_id: str
    confidence: float


@dataclass(frozen=True)
class Page:
    number: int
    image_path: str | None = None
    ocr_words: tuple[str, ...] = ()
    ocr_boxes: tuple[BBox, ...] = ()
    ocr_confidence: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if self.number < 0:
            raise ValueError("page number must be nonnegative")
        if self.ocr_boxes and len(self.ocr_boxes) != len(self.ocr_words):
            raise ValueError("OCR words and boxes length mismatch")


@dataclass
class Document:
    document_id: str
    source_dataset: str
    split: str
    document_type: str
    vendor_group: str
    layout_cluster: str
    pages: list[Page]
    fields: list[Field]
    line_items: list[LineItem] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    quality_features: dict[str, float] = field(default_factory=dict)
    ood_metadata: dict[str, Any] = field(default_factory=dict)
    corruption_metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def encode(value: Any) -> Any:
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, dict):
                return {key: encode(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [encode(item) for item in value]
            return value
        return encode(asdict(self))


@dataclass(frozen=True)
class Prediction:
    document_id: str
    raw_fields: tuple[Field, ...]
    normalized_fields: tuple[Field, ...]
    warnings: tuple[str, ...]
    risk_score: float
    decision: str
    schema_valid: bool
