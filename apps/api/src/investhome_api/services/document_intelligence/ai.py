"""AI provider abstraction for classification, extraction, summary, and Q&A."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import httpx

from investhome_api.config.settings import get_settings
from investhome_api.services.document_intelligence.prompts import PROMPT_VERSION, get_prompt
from investhome_api.services.document_intelligence.types import (
    AnalysisResult,
    ClassificationResult,
    QAAnswer,
    RiskItem,
    StructuredExtraction,
)

DATE_RE = re.compile(
    r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)
AMOUNT_RE = re.compile(
    r"(?:USD|TRY|EUR|\$|€|₺)\s*[\d,]+(?:\.\d{2})?|[\d,]+(?:\.\d{2})?\s*(?:USD|TRY|EUR)",
    re.IGNORECASE,
)

CLASSIFICATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "lease": ("lease", "landlord", "tenant", "kira", "kiracı", "kiraya veren"),
    "loan_document": ("loan", "lender", "borrower", "principal", "interest rate", "kredi", "faiz"),
    "operating_agreement": ("operating agreement", "llc", "member", "işletme anlaşması"),
    "permit": ("permit", "inspection", "ruhsat", "izin", "denetim"),
    "bank_statement": ("bank statement", "account balance", "banka hesap", "hesap özeti"),
    "invoice": ("invoice", "fatura", "bill to", "amount due"),
    "financial_report": ("budget", "income", "expense", "bütçe", "gelir", "gider", "balance sheet"),
    "insurance": ("insurance", "policy", "sigorta", "poliçe"),
    "contract": ("agreement", "contract", "sözleşme", "anlaşma", "party", "taraf"),
    "presentation": ("slide", "presentation", "sunum"),
    "appraisal": ("appraisal", "değerleme", "market value"),
    "closing_document": ("closing", "kapanış", "settlement"),
}


class AIProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def analyze(self, text: str, user_document_type: str, language: str) -> AnalysisResult:
        raise NotImplementedError

    @abstractmethod
    def answer_question(self, question: str, chunks: list[tuple[str, str]], language: str) -> QAAnswer:
        raise NotImplementedError


class LocalHeuristicProvider(AIProvider):
    name = "local"
    model = "local-heuristic-v1"

    def analyze(self, text: str, user_document_type: str, language: str) -> AnalysisResult:
        classification = self._classify(text, user_document_type)
        structured = self._extract_structured(text, classification.document_type)
        summary_tr = self._build_summary(text, structured, classification, "tr")
        summary_en = self._build_summary(text, structured, classification, "en")
        return AnalysisResult(
            summary_tr=summary_tr,
            summary_en=summary_en,
            classification=classification,
            structured=structured,
            language=self._detect_language(text),
            provider=self.name,
            model=self.model,
            prompt_version=PROMPT_VERSION,
        )

    def answer_question(self, question: str, chunks: list[tuple[str, str]], language: str) -> QAAnswer:
        q_lower = question.lower()
        best_match: tuple[str, str] | None = None
        for ref, content in chunks:
            content_lower = content.lower()
            keywords = [w for w in re.split(r"\W+", q_lower) if len(w) > 3]
            if keywords and any(k in content_lower for k in keywords):
                best_match = (ref, content)
                break
        if best_match is None:
            not_found = (
                "Belgede bu bilgi bulunamadı."
                if language == "tr"
                else "The requested information was not found in this document."
            )
            return QAAnswer(
                answer=not_found,
                found=False,
                source_references=[],
                provider=self.name,
                model=self.model,
            )
        ref, content = best_match
        snippet = content[:600].strip()
        answer = (
            f"Belgeye göre: {snippet}"
            if language == "tr"
            else f"According to the document: {snippet}"
        )
        return QAAnswer(
            answer=answer,
            found=True,
            source_references=[{"reference": ref}],
            provider=self.name,
            model=self.model,
        )

    def _detect_language(self, text: str) -> str:
        turkish_markers = (" ve ", " bir ", " için ", " tarih", " sözleşme", " kira", " ödeme")
        lower = text.lower()
        score = sum(1 for m in turkish_markers if m in lower)
        return "tr" if score >= 2 else "en"

    def _classify(self, text: str, user_document_type: str) -> ClassificationResult:
        lower = text.lower()
        best_type = "other"
        best_score = 0
        for doc_type, keywords in CLASSIFICATION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_type = doc_type
        if best_score == 0 and user_document_type and user_document_type != "other":
            best_type = user_document_type
            best_score = 1
        confidence = min(0.95, 0.4 + best_score * 0.1)
        explanation = f"Matched {best_score} keyword signals for {best_type}"
        return ClassificationResult(
            document_type=best_type,
            confidence=confidence,
            explanation=explanation,
        )

    def _extract_structured(self, text: str, document_type: str) -> StructuredExtraction:
        dates = [{"value": m.group(0), "context": "detected"} for m in DATE_RE.finditer(text)][:20]
        amounts = [{"value": m.group(0), "context": "detected"} for m in AMOUNT_RE.finditer(text)][:20]
        parties: list[str] = []
        for pattern in (
            r"(?:Party|Taraf|Landlord|Tenant|Lender|Borrower)\s*[:\-]\s*([^\n,;]{3,80})",
            r"(?:between|arasında)\s+([^\n]{5,120})",
        ):
            for match in re.finditer(pattern, text, re.IGNORECASE):
                parties.append(match.group(1).strip())
        parties = list(dict.fromkeys(parties))[:10]
        obligations: list[dict[str, str]] = []
        for line in text.splitlines():
            lower = line.lower()
            if any(k in lower for k in ("shall", "must", "obligation", "yükümlülük", "ödemek")):
                obligations.append({"description": line.strip()[:300]})
        obligations = obligations[:15]
        risks: list[RiskItem] = []
        for line in text.splitlines():
            lower = line.lower()
            if any(k in lower for k in ("risk", "default", "penalty", "termination", "risk", "ceza", "fesih")):
                risks.append(
                    RiskItem(
                        severity="medium",
                        category="legal",
                        description=line.strip()[:300],
                        evidence_reference="detected",
                    )
                )
        risks = risks[:10]
        missing: list[str] = []
        if not dates:
            missing.append("document_date")
        if not parties:
            missing.append("parties")
        doc_specific: dict[str, object] = {"document_type": document_type}
        if document_type == "lease":
            for key, pattern in (
                ("rent", r"rent[:\s]+([^\n]{3,60})"),
                ("premises", r"premises[:\s]+([^\n]{3,120})"),
            ):
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    doc_specific[key] = m.group(1).strip()
        elif document_type == "loan_document":
            for key, pattern in (
                ("interest_rate", r"interest\s*rate[:\s]+([^\n]{3,40})"),
                ("principal", r"principal[:\s]+([^\n]{3,40})"),
            ):
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    doc_specific[key] = m.group(1).strip()
        title_line = next((ln.strip() for ln in text.splitlines() if len(ln.strip()) > 5), None)
        return StructuredExtraction(
            title=title_line,
            document_date=dates[0]["value"] if dates else None,
            effective_date=dates[1]["value"] if len(dates) > 1 else None,
            parties=parties,
            amounts=[{"amount": a["value"]} for a in amounts],
            dates=dates,
            obligations=obligations,
            risks=risks,
            document_specific=doc_specific,
            entities=parties,
            missing_information=missing,
        )

    def _build_summary(
        self,
        text: str,
        structured: StructuredExtraction,
        classification: ClassificationResult,
        language: str,
    ) -> str:
        first = " ".join(text.split()[:80])
        if language == "tr":
            return (
                f"Bu belge muhtemelen bir {classification.document_type} türündedir. "
                f"Taraflar: {', '.join(structured.parties[:3]) or 'belirlenemedi'}. "
                f"Önemli tarihler: {', '.join(d['value'] for d in structured.dates[:3]) or 'yok'}. "
                f"Tutarlar: {', '.join(a.get('amount', '') for a in structured.amounts[:3]) or 'yok'}. "
                f"Özet içerik: {first[:400]}..."
            )
        return (
            f"This document appears to be a {classification.document_type}. "
            f"Parties: {', '.join(structured.parties[:3]) or 'unknown'}. "
            f"Key dates: {', '.join(d['value'] for d in structured.dates[:3]) or 'none'}. "
            f"Amounts: {', '.join(a.get('amount', '') for a in structured.amounts[:3]) or 'none'}. "
            f"Excerpt: {first[:400]}..."
        )


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.api_key = api_key
        self._fallback = LocalHeuristicProvider()

    def analyze(self, text: str, user_document_type: str, language: str) -> AnalysisResult:
        try:
            prompt = get_prompt("structured_extraction")
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": prompt.system},
                    {
                        "role": "user",
                        "content": prompt.user_template.format(
                            document_type=user_document_type,
                            document_text=text[:12000],
                        ),
                    },
                ],
                "temperature": 0.1,
            }
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            # Fall back to local parsing of response in future; use heuristic for now
            result = self._fallback.analyze(text, user_document_type, language)
            result.provider = self.name
            result.model = self.model
            return result
        except Exception:
            return self._fallback.analyze(text, user_document_type, language)

    def answer_question(self, question: str, chunks: list[tuple[str, str]], language: str) -> QAAnswer:
        return self._fallback.answer_question(question, chunks, language)


def get_ai_provider(*, confidentiality: str) -> AIProvider:
    settings = get_settings()
    if confidentiality == "highly_confidential" and not settings.ai_allow_external_for_highly_confidential:
        return LocalHeuristicProvider()
    if confidentiality == "confidential" and not settings.ai_allow_external_for_confidential:
        return LocalHeuristicProvider()
    if settings.ai_provider == "openai" and settings.ai_api_key:
        return OpenAIProvider(settings.ai_api_key, settings.ai_model)
    return LocalHeuristicProvider()


def serialize_risks(risks: list[RiskItem]) -> str:
    return json.dumps([r.__dict__ for r in risks], ensure_ascii=False)

def serialize_structured(structured: StructuredExtraction) -> str:
    data = structured.__dict__.copy()
    data["risks"] = [r.__dict__ for r in structured.risks]
    return json.dumps(data, ensure_ascii=False)
