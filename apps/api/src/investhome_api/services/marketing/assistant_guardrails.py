"""Centralized safety / Fair Housing guardrails for Marketing AI Assistant."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Unsupported financial / legal claim patterns
UNSUPPORTED_CLAIM_PATTERNS: list[tuple[str, str]] = [
    (r"\bguaranteed\s+(returns?|roi|profits?|rental|income|yield)\b", "guaranteed_returns"),
    (r"\bgaranti(?:li)?\s+(getiri|kâr|kazanç|kira)\b", "guaranteed_returns"),
    (r"\brisk[\s-]?free\s+(investment|return)\b", "guaranteed_returns"),
    (r"\blegal\s+advice\b", "legal_advice"),
    (r"\btax\s+advice\b|\btax[\s-]?free\s+guarantee\b", "tax_advice"),
    (r"\bhukuki\s+tavsiye\b|\bvergi\s+tavsiyesi\b", "legal_tax_advice"),
    (r"\bonly\s+\d+\s+(units?|homes?|apartments?)\s+left\b", "false_scarcity"),
    (r"\bson\s+\d+\s+(daire|konut|birim)\b", "false_scarcity"),
    (r"\bfake\s+testimonial|\binvented\s+award|\bfabricated\s+statistic\b", "fake_social_proof"),
    (r"\b\d{1,3}\s*%\s*(guaranteed|assured)\b", "guaranteed_returns"),
]

# Protected-class / Fair Housing targeting language
FAIR_HOUSING_PATTERNS: list[tuple[str, str]] = [
    (r"\b(no|exclude|excluding|only)\s+(families|children|kids|pregnant)\b", "familial_status"),
    (r"\b(christians?|muslims?|jews?|hindus?)\s+only\b", "religion"),
    (r"\b(whites?|blacks?|asians?)\s+only\b", "race"),
    (r"\bno\s+(disabled|handicap)\b", "disability"),
    (r"\b(single\s+men|single\s+women)\s+only\b", "sex"),
    (r"\b(nationals?\s+only|citizens?\s+only)\b", "national_origin"),
    (r"\b(aileler|çocuklar)\s+hariç\b", "familial_status"),
    (r"\bsadece\s+(müslüman|hristiyan|yahudi)\b", "religion"),
]


@dataclass
class GuardrailResult:
    blocked: bool = False
    flags: list[str] = field(default_factory=list)
    message: str | None = None
    sanitized_instruction: str | None = None


def _scan(text: str, patterns: list[tuple[str, str]]) -> list[str]:
    flags: list[str] = []
    for pattern, flag in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            if flag not in flags:
                flags.append(flag)
    return flags


def check_user_instruction(instruction: str | None, *, language: str = "en") -> GuardrailResult:
    if not instruction or not instruction.strip():
        return GuardrailResult(sanitized_instruction=instruction)

    text = instruction.strip()
    flags = _scan(text, UNSUPPORTED_CLAIM_PATTERNS) + _scan(text, FAIR_HOUSING_PATTERNS)
    if not flags:
        return GuardrailResult(sanitized_instruction=text)

    if language == "tr":
        message = (
            "İstek desteklenmeyen veya adil konut kurallarına aykırı talepler içeriyor. "
            "Bu kısım reddedildi. Doğrulanmış proje/kampanya verisi sağlayın; "
            "korunan sınıflara göre hedefleme yapılamaz."
        )
    else:
        message = (
            "The request includes unsupported claims or Fair Housing violations. "
            "That portion was refused. Provide verified project/campaign data; "
            "protected-class targeting is not allowed."
        )
    return GuardrailResult(
        blocked=True,
        flags=flags,
        message=message,
        sanitized_instruction=None,
    )


def check_generated_content(content: str | None, *, language: str = "en") -> GuardrailResult:
    if not content:
        return GuardrailResult()
    flags = _scan(content, UNSUPPORTED_CLAIM_PATTERNS) + _scan(content, FAIR_HOUSING_PATTERNS)
    if not flags:
        return GuardrailResult()
    if language == "tr":
        message = (
            "Üretilen içerik güvenlik kontrolünden geçemedi. "
            "İçerik taslak olarak işaretlendi ve sorunlu kısımlar engellendi."
        )
    else:
        message = (
            "Generated content failed safety checks. "
            "Output was marked draft and unsafe portions were blocked."
        )
    return GuardrailResult(blocked=True, flags=flags, message=message)


def redact_unsafe_content(content: str, flags: list[str], *, language: str = "en") -> str:
    notice = (
        "[REMOVED: unsupported or unsafe claim — verification required]"
        if language != "tr"
        else "[KALDIRILDI: desteklenmeyen veya güvensiz ifade — doğrulama gerekli]"
    )
    redacted = content
    for pattern, flag in UNSUPPORTED_CLAIM_PATTERNS + FAIR_HOUSING_PATTERNS:
        if flag in flags:
            redacted = re.sub(pattern, notice, redacted, flags=re.IGNORECASE)
    return redacted
