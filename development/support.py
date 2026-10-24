"""Explicit locations for synthetic development data, never product resources."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOT = REPOSITORY_ROOT / "product"
EXAMPLES_ROOT = REPOSITORY_ROOT / "development/examples"
LEGACY_ROOT = REPOSITORY_ROOT / "development/fixtures/legacy-world"
