"""Test crm.controller.item.getFile download. Do not print URLs."""
from __future__ import annotations

from recover_remaining_66 import ENV_PATH, BitrixClient, load_env, try_download, webhook_base, is_binary


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    item = client.call("crm.item.get", {"entityTypeId": 3, "id": 390}).get("result") or {}
    inner = (item.get("item") or {})
    uf = inner.get("ufCrm_1692366477437") or inner.get("ufCrm1692366477437") or {}
    url = uf.get("url") if isinstance(uf, dict) else None
    url_machine = uf.get("urlMachine") if isinstance(uf, dict) else None
    results = {}
    for label, target in (("url", url), ("urlMachine", url_machine)):
        content, mime, err = try_download(client, target or "")
        results[label] = {
            "ok": bool(content and is_binary(content, mime)),
            "bytes": len(content or b""),
            "mime": mime,
            "err": err,
            "magic": content[:16] if content else None,
            "is_pdf": bool(content and content.startswith(b"%PDF")),
            "is_jpeg": bool(content and content[:3] == b"\xff\xd8\xff"),
            "is_png": bool(content and content.startswith(b"\x89PNG")),
        }
    # lead entityTypeId 1? contact 3, lead 1
    print(__import__("json").dumps({"uf_keys": list(uf.keys()) if isinstance(uf, dict) else type(uf).__name__, "downloads": results}, default=lambda o: o.decode("latin1", "replace") if isinstance(o, (bytes, bytearray)) else o, indent=2))


if __name__ == "__main__":
    main()
