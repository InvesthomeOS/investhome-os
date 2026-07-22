"""CLI entry for integrated demo seed: seed | reset | validate."""

from __future__ import annotations

import argparse
import json
import sys

from investhome_api.db.demo.cleanup import cleanup_integrated_demo
from investhome_api.db.demo.integrated import seed_integrated_demo
from investhome_api.db.demo.safety import DemoSeedSafetyError, assert_demo_seed_allowed
from investhome_api.db.demo.validate import validate_integrated_demo


def _cmd_seed(*, run_foundational: bool = True) -> int:
    assert_demo_seed_allowed()
    if run_foundational:
        # seed.main() already invokes seed_integrated_demo() at the end
        from investhome_api.db.seed import main as foundational_seed

        foundational_seed()
    else:
        counts = seed_integrated_demo()
        print("Integrated demo layers:")
        print(json.dumps(counts, indent=2, default=str))
    return validate_integrated_demo(print_report=True)


def _cmd_reset() -> int:
    assert_demo_seed_allowed()
    deleted = cleanup_integrated_demo()
    print("Cleanup deleted:")
    print(json.dumps(deleted, indent=2, default=str))
    return _cmd_seed(run_foundational=True)


def _cmd_validate() -> int:
    return validate_integrated_demo(print_report=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="investhome-demo",
        description="Integrated demo data seed for Investhome OS",
    )
    parser.add_argument(
        "command",
        choices=("seed", "reset", "validate"),
        help="seed: foundational + integrated; reset: cleanup demo then seed; validate: count checks",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "seed":
            return _cmd_seed()
        if args.command == "reset":
            return _cmd_reset()
        if args.command == "validate":
            return _cmd_validate()
    except DemoSeedSafetyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    parser.error(f"Unknown command: {args.command}")
    return 2


def console_main() -> None:
    """Setuptools/hatch console entrypoint."""
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
