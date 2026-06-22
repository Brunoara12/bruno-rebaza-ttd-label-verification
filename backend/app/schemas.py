from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FieldStatus = Literal["PASS", "FAIL"]
OverallVerdict = Literal["APPROVED", "NEEDS_REVIEW"]
BatchItemStatus = Literal["COMPLETED", "ERROR"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApplicationData(StrictModel):
    brand_name: str = Field(min_length=1)
    class_type: str = Field(min_length=1)
    abv: str = Field(min_length=1)
    net_contents: str = Field(min_length=1)
    producer: str = Field(min_length=1)
    country_of_origin: str = Field(min_length=1)
    government_warning: str = Field(min_length=1)


class ExtractedLabel(StrictModel):
    brand_name: str | None = None
    class_type: str | None = None
    abv: str | None = None
    net_contents: str | None = None
    producer: str | None = None
    country_of_origin: str | None = None
    government_warning: str | None = None
    raw_text: str | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class FieldResult(StrictModel):
    field: str
    match_type: str
    expected: str | None
    found: str | None
    status: FieldStatus
    reason_code: str | None = None


class VerificationResult(StrictModel):
    results: list[FieldResult]
    overall_verdict: OverallVerdict
    latency_ms: int = Field(default=0, ge=0)


class ErrorField(StrictModel):
    field: str
    code: str
    message: str


class ItemError(StrictModel):
    code: str
    message: str
    fields: list[ErrorField] = Field(default_factory=list)


class BatchItemResult(StrictModel):
    client_id: str
    index: int = Field(ge=0)
    filename: str | None = None
    status: BatchItemStatus
    result: VerificationResult | None = None
    error: ItemError | None = None


class BatchSummary(StrictModel):
    passed: int = Field(ge=0)
    needs_review: int = Field(ge=0)
    total: int = Field(ge=0)


class BatchVerificationResult(StrictModel):
    items: list[BatchItemResult]
    summary: BatchSummary
    latency_ms: int = Field(default=0, ge=0)
