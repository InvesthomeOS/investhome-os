"""Shared types for document intelligence pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceReference:
    page: int | None = None
    sheet: str | None = None
    slide: int | None = None
    section: str | None = None

    def label(self) -> str:
        parts: list[str] = []
        if self.page is not None:
            parts.append(f"page:{self.page}")
        if self.sheet:
            parts.append(f"sheet:{self.sheet}")
        if self.slide is not None:
            parts.append(f"slide:{self.slide}")
        if self.section:
            parts.append(f"section:{self.section}")
        return " | ".join(parts) if parts else "document"


@dataclass
class TextSegment:
    text: str
    source: SourceReference
    confidence: float | None = None
    needs_ocr: bool = False


@dataclass
class ExtractionResult:
    segments: list[TextSegment] = field(default_factory=list)
    method: str = "unknown"
    page_count: int | None = None
    full_text: str = ""

    def build_full_text(self) -> str:
        if self.full_text:
            return self.full_text
        blocks: list[str] = []
        for seg in self.segments:
            ref = seg.source.label()
            blocks.append(f"[{ref}]\n{seg.text.strip()}")
        self.full_text = "\n\n".join(blocks).strip()
        return self.full_text


@dataclass
class OCRPageResult:
    text: str
    source: SourceReference
    confidence: float | None = None


@dataclass
class ClassificationResult:
    document_type: str
    confidence: float
    explanation: str


@dataclass
class RiskItem:
    severity: str
    category: str
    description: str
    evidence_reference: str | None = None
    recommended_action: str | None = None
    due_date: str | None = None
    related_party: str | None = None


@dataclass
class StructuredExtraction:
    title: str | None = None
    document_date: str | None = None
    effective_date: str | None = None
    expiration_date: str | None = None
    parties: list[str] = field(default_factory=list)
    amounts: list[dict[str, str]] = field(default_factory=list)
    dates: list[dict[str, str]] = field(default_factory=list)
    obligations: list[dict[str, str]] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    document_specific: dict[str, object] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    summary_tr: str
    summary_en: str
    classification: ClassificationResult
    structured: StructuredExtraction
    language: str
    provider: str
    model: str
    prompt_version: str


@dataclass
class QAAnswer:
    answer: str
    found: bool
    source_references: list[dict[str, str | int | None]]
    provider: str
    model: str
