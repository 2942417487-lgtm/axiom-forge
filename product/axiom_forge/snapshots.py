"""Self-contained snapshots. These helpers never apply Canon changes."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .ids import new_id
from .validation import DataError, SchemaStore, collect_world, digest, read_json, validate_dataset


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canon_version(world_id: str, files: list[dict]) -> str:
    manifest = [{"path": record["path"], "sha256": record["sha256"]} for record in files]
    return "CANON-" + digest({"world_id": world_id, "files": manifest})


def build_snapshot(files: dict[str, dict], schemas: SchemaStore) -> dict:
    dataset = validate_dataset(files, schemas)
    records = [{"path": path, "sha256": digest(data), "data": data}
               for path, data in sorted(files.items())]
    world_id = dataset["world"]["world_id"]
    snapshot = {"schema_version": "1.0", "snapshot_id": new_id("snapshot"),
                "world_id": world_id, "canon_version": canon_version(world_id, records),
                "created_at": utc_now(), "files": records}
    # Deep-copy input data so an in-process live edit cannot change the snapshot.
    snapshot = json.loads(json.dumps(snapshot, ensure_ascii=False, allow_nan=False))
    verify_snapshot(snapshot, schemas)
    return snapshot


def verify_snapshot(snapshot: dict, schemas: SchemaStore) -> dict:
    schemas.validate("canon_snapshot", snapshot)
    files = {}
    for record in snapshot["files"]:
        if record["path"] in files:
            raise DataError(f"Duplicate snapshot path: {record['path']}")
        if digest(record["data"]) != record["sha256"]:
            raise DataError(f"Snapshot content hash mismatch: {record['path']}")
        files[record["path"]] = record["data"]
    if list(files) != sorted(files):
        raise DataError("Snapshot manifest must be sorted by path")
    if canon_version(snapshot["world_id"], snapshot["files"]) != snapshot["canon_version"]:
        raise DataError("Snapshot Canon version hash mismatch")
    dataset = validate_dataset(files, schemas)
    if dataset["world"]["world_id"] != snapshot["world_id"]:
        raise DataError("Snapshot and embedded world identity differ")
    return dataset


def create_snapshot(repo: Path, schemas: SchemaStore) -> Path:
    repo = repo.resolve()
    snapshot = build_snapshot(collect_world(repo, schemas), schemas)
    directory = repo / "world/snapshots"
    if directory.exists() and not directory.resolve().is_relative_to(repo):
        raise DataError("Snapshot directory escapes repository")
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{snapshot['canon_version']}.json"
    if not destination.resolve().is_relative_to(repo):
        raise DataError("Snapshot file escapes repository")
    temporary = None
    try:
        # Windows rename and POSIX hard-link publication both fail if a destination
        # exists. Readers see only complete files, without replacing old snapshots.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=directory, suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
            output.flush()
            os.fsync(output.fileno())
        try:
            if os.name == "nt":
                os.rename(temporary, destination)
            else:
                os.link(temporary, destination)
        except FileExistsError:
            if not destination.resolve().is_relative_to(repo):
                raise DataError("Existing snapshot file escapes repository")
            existing = read_json(destination)
            verify_snapshot(existing, schemas)
            if existing["canon_version"] != snapshot["canon_version"]:
                raise DataError("Existing snapshot filename/version mismatch")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
