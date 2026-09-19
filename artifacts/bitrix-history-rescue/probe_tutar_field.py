"""Find Bitrix field labeled Tutar ve para birimi. Read-only."""
from __future__ import annotations

import json

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore


def labels(spec: dict) -> list[str]:
    out = []
    for key in ("formLabel", "listLabel", "filterLabel", "title", "editFormLabel"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip():
            out.append(val.strip())
        elif isinstance(val, dict):
            out.extend(str(v).strip() for v in val.values() if v)
    return out


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    hits = []
    for method, entity in (
        ("crm.deal.fields", "deal"),
        ("crm.contact.fields", "contact"),
        ("crm.lead.fields", "lead"),
    ):
        body = client.call(method, {})
        fields = body.get("result") if isinstance(body.get("result"), dict) else {}
        for fid, spec in fields.items():
            if not isinstance(spec, dict):
                continue
            labs = labels(spec)
            blob = " ".join(labs + [fid]).casefold()
            if "tutar" in blob or "para birimi" in blob or "currency" in blob or fid in {"OPPORTUNITY", "CURRENCY_ID", "OPPORTUNITY_WITH_CURRENCY"}:
                hits.append({"entity": entity, "id": fid, "type": spec.get("type"), "labels": labs})
    print(json.dumps({"hits": hits, "calls": client.call_count}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
