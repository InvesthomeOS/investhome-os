"""Resolve Bitrix source/user labels. Read-only. Does not print webhook or file URLs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    sources = client.call("crm.status.list", {"filter[ENTITY_ID]": "SOURCE"}).get("result") or []
    wanted = {"UC_37VR5B", "UC_LPEQFO"}
    source_names = {}
    if isinstance(sources, list):
        for row in sources:
            if isinstance(row, dict) and str(row.get("STATUS_ID")) in wanted:
                source_names[str(row.get("STATUS_ID"))] = row.get("NAME")
    users = {}
    for user_id in ("1", "92"):
        result = client.call("user.get", {"ID": user_id}).get("result")
        row = result[0] if isinstance(result, list) and result else result
        if isinstance(row, dict):
            users[user_id] = " ".join(
                str(row.get(key) or "") for key in ("NAME", "LAST_NAME")
            ).strip() or row.get("EMAIL")
    print(json.dumps({"sources": source_names, "users": users, "calls": client.call_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
