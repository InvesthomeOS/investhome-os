"""Queue + Open Channel dialog owner for Beyza WhatsApp lines. No downloads."""
from __future__ import annotations

import json

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    calls = []
    payloads = [
        ("imopenlines.config.getqueue", {"CONFIG_ID": "18"}),
        ("imopenlines.config.getqueue", {"CONFIG_ID": 18}),
        ("imopenlines.config.getqueue", {"CONFIG_ID": "24"}),
        ("imopenlines.config.get", {"CONFIG_ID": "18"}),
        ("imopenlines.config.get", {"CONFIG_ID": "24"}),
        ("imopenlines.dialog.get", {"CHAT_ID": 13496}),
        ("imopenlines.dialog.get", {"CHAT_ID": 12068}),
        ("imopenlines.dialog.get", {"USER_CODE": "bitrix_whatcrm_net_70680444|18|chat.905304150866|10784"}),
        ("imopenlines.dialog.get", {"USER_CODE": "bitrix_whatcrm_net_70680444|24|chat.905304150866|10784"}),
        ("imopenlines.session.history.get", {"CHAT_ID": 13496}),
        ("user.get", {"ID": "92"}),
        ("user.search", {"FILTER": {"ID": "92"}}),
    ]
    for method, payload in payloads:
        body = client.call(method, payload)
        result = body.get("result")
        slim = result
        if isinstance(result, dict):
            slim = {
                k: result.get(k)
                for k in (
                    "ID",
                    "OPERATOR_ID",
                    "OPERATOR",
                    "QUEUE",
                    "USERS",
                    "CHAT_ID",
                    "SESSION_ID",
                    "CONFIG_ID",
                    "LINE_NAME",
                    "USER_CODE",
                    "STATUS",
                    "CLOSED",
                    "OWNER_ID",
                    "RESPONSIBLE_ID",
                )
                if k in result or k.lower() in {x.lower() for x in result}
            }
            if not slim:
                slim = {k: v for k, v in result.items() if "url" not in k.lower() and "token" not in k.lower()}
                if len(json.dumps(slim, default=str)) > 2500:
                    slim = {"keys": sorted(result.keys()), "subset": {k: result.get(k) for k in list(result)[:25]}}
        calls.append(
            {
                "method": method,
                "payload": payload,
                "error": body.get("error"),
                "error_description": body.get("error_description"),
                "result": slim,
            }
        )
    print(json.dumps({"bitrix_calls": client.call_count, "calls": calls}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
