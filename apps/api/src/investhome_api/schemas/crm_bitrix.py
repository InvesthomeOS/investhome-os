"""Bitrix dry-run request/response schemas. No commit path in Phase 2."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

BitrixFileRole = Literal[
    "active_customers",
    "junk",
    "active_comments",
    "junk_comments",
    "agents",
    "agreements",
    "unknown",
]


class BitrixDryRunRow(BaseModel):
    source_file: str
    role: BitrixFileRole | None = None
    bitrix_id: str | None = None
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    comment: str | None = None
    project_hint: str | None = None
    agreement_date: date | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
    parse_error: str | None = None


class BitrixDryRunRequest(BaseModel):
    rows: list[BitrixDryRunRow] = Field(default_factory=list)
    read_db: bool = False


class BitrixDryRunResponse(BaseModel):
    contacts: dict[str, Any]
    active_junk: dict[str, Any]
    comments: dict[str, Any]
    agents: dict[str, Any]
    agreements: dict[str, Any]
    data_quality: dict[str, Any]
    writes: dict[str, Any]
    files: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    console: str
