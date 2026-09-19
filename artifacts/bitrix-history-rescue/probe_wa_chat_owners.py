"""Read-only Open Channel / chat owner dump for Berk Çimen WhatsApp files. No downloads."""
from __future__ import annotations

import json
from typing import Any

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore


def slim_user(rec: Any) -> dict:
    if not isinstance(rec, dict):
        return {"raw": rec}
    return {
        "id": rec.get("id") or rec.get("ID"),
        "name": rec.get("name") or rec.get("NAME"),
        "last_name": rec.get("last_name") or rec.get("LAST_NAME"),
        "first_name": rec.get("first_name") or rec.get("FIRST_NAME"),
        "work_position": rec.get("work_position") or rec.get("WORK_POSITION"),
        "bot": rec.get("bot") or rec.get("BOT"),
        "connector": rec.get("connector") or rec.get("CONNECTOR"),
        "network": rec.get("network") or rec.get("NETWORK"),
        "extranet": rec.get("extranet") or rec.get("EXTRANET"),
        "external_auth_id": rec.get("external_auth_id") or rec.get("EXTERNAL_AUTH_ID"),
    }


def slim_dict(obj: Any, keep: set[str] | None = None) -> Any:
    if isinstance(obj, dict):
        if keep:
            return {k: slim_dict(v) for k, v in obj.items() if k in keep or k.lower() in {x.lower() for x in keep}}
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ("url", "token", "password", "download", "link")):
                continue
            out[k] = slim_dict(v)
        return out
    if isinstance(obj, list):
        return [slim_dict(x, keep) for x in obj[:30]]
    return obj


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    out: dict[str, Any] = {"calls": []}

    def rec(method: str, payload: dict) -> dict:
        body = client.call(method, payload)
        slim = {
            "method": method,
            "error": body.get("error"),
            "error_description": body.get("error_description"),
            "result_type": type(body.get("result")).__name__,
        }
        result = body.get("result")
        if isinstance(result, dict):
            slim["keys"] = sorted(result.keys())
            slim["result"] = slim_dict(result)
            if "users" in result and isinstance(result["users"], dict):
                slim["users"] = {uid: slim_user(u) for uid, u in list(result["users"].items())[:20]}
            if "userInChat" in result:
                slim["userInChat"] = result.get("userInChat")
        elif isinstance(result, list):
            slim["len"] = len(result)
            slim["result"] = slim_dict(result)
        else:
            slim["result"] = result
        out["calls"].append(slim)
        return body

    rec("user.get", {"ID": "10784"})
    rec("user.get", {"ID": "10"})
    rec("crm.contact.get", {"id": "180"})
    rec("im.chat.get", {"ID": "13496"})
    rec("im.chat.get", {"CHAT_ID": "13496"})
    rec("im.chat.get", {"ID": "12068"})
    rec("im.dialog.get", {"DIALOG_ID": "chat13496"})
    rec("im.dialog.get", {"DIALOG_ID": "chat12068"})
    rec("im.chat.user.list", {"CHAT_ID": "13496"})
    rec("im.chat.user.list", {"ID": "13496"})
    rec("im.dialog.users.get", {"DIALOG_ID": "chat13496"})
    rec("im.dialog.users.get", {"DIALOG_ID": "chat12068"})
    rec("imopenlines.crm.chat.get", {"CRM_ENTITY_TYPE": "CONTACT", "CRM_ENTITY": "180", "ACTIVE_ONLY": "N"})
    rec("imopenlines.crm.chat.get", {"CRM_ENTITY_TYPE": "contact", "CRM_ENTITY": "180", "ACTIVE_ONLY": "N"})
    rec("im.dialog.messages.get", {"DIALOG_ID": "chat13496", "LAST_ID": 2055945, "LIMIT": 3})
    rec("im.dialog.messages.get", {"DIALOG_ID": "chat12068", "LAST_ID": 2026491, "LIMIT": 3})
    rec("disk.file.get", {"id": "89178"})
    rec("im.disk.file.get", {"id": "89178"})
    rec("imopenlines.session.list", {"FILTER": {"CRM": "Y", "CRM_ENTITY_TYPE": "CONTACT", "CRM_ENTITY_ID": 180}, "SELECT": ["ID", "OPERATOR_ID", "STATUS", "CHAT_ID", "DATE_CREATE"]})
    rec("imopenlines.config.list.get", {})

    print(json.dumps({"bitrix_calls": client.call_count, **out}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
