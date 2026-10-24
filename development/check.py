"""Run offline tests with product and development imports kept separate."""

import sys
import os
import argparse
import unittest
from pathlib import Path

DEVELOPMENT = Path(__file__).resolve().parent
sys.path.insert(0, str(DEVELOPMENT.parent / "product"))
sys.path.insert(0, str(DEVELOPMENT))
os.environ["PYTHONPATH"] = os.pathsep.join((str(DEVELOPMENT.parent / "product"), str(DEVELOPMENT)))


def main(argv=None):
    from source_boundary import check_source_boundary
    from axiom_forge.validation import DataError
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--boundary-only", action="store_true")
    options, arguments = parser.parse_known_args(argv)
    try:
        count = check_source_boundary()
    except (DataError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    print(f"OK: source repository boundary checked ({count} tracked paths)", flush=True)
    if options.boundary_only:
        return 0
    result = unittest.main(module=None, argv=[sys.argv[0], "discover", "-s", str(DEVELOPMENT / "tests"),
                                            "-t", str(DEVELOPMENT), *arguments], exit=False)
    return 0 if result.result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
