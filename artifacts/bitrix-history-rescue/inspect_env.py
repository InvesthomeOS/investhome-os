from pathlib import Path

p = Path("/tmp/.env")
print("exists", p.exists(), "size", p.stat().st_size if p.exists() else None)
text = p.read_text(encoding="utf-8", errors="replace")
print(
    "ALL_KEYS_COUNT",
    sum(
        1
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    ),
)
for line in text.splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    key, value = s.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    interesting = (
        "BITRIX" in key.upper()
        or "WEBHOOK" in key.upper()
        or "BURAYA" in key.upper()
        or "BURAYA" in value
        or "bitrix24" in value.lower()
        or "/rest/" in value.lower()
    )
    if interesting:
        print(
            "KEY",
            key,
            "LEN",
            len(value),
            "ENDSLASH",
            value.endswith("/"),
            "HAS_BURAYA",
            "BURAYA_BITRIX_URL=" in value,
            "HAS_REST",
            "/rest/" in value.lower(),
            "STARTS_HTTP",
            value.lower().startswith("http"),
        )
