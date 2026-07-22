"""Allow ``python -m investhome_api.db.demo`` as an alias for the CLI."""

from investhome_api.db.demo.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
