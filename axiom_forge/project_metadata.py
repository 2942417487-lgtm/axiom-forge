"""Read-only project format and world metadata identity checks.

No workspace registration, Git inspection, sensitive preflight or authorization.
Only trusted engine schemas are used; source field values never enter reports.
"""

import hashlib
from pathlib import Path

from .tools.storage import ToolError, read_bounded, strict_json
from .validation import DataError
from .workspaces import EngineResources, checked_root, disjoint


FIELDS = ("project_format_version", "project_id", "world_id", "display_version")


class ProjectMetadataError(DataError):
    def __init__(self, code, location, message):
        self.code = code
        self.location = location
        self.message = message
        super().__init__(f"{code}: {location}: {message}")

    def diagnostic(self):
        return {"status": self.code, "location": self.location, "message": self.message}


def _read(path, location, *, missing_code="inspection_incomplete"):
    try:
        return read_bounded(path)
    except ToolError as exc:
        # Only classify absence after the reader's link checks; never treat a
        # broken link, directory, permission error or size failure as legacy.
        missing = False
        if exc.code == "file_unavailable":
            try:
                path.lstat()
            except FileNotFoundError:
                missing = True
            except OSError:
                pass
        raise ProjectMetadataError(missing_code if missing else "inspection_incomplete",
                                   location, "Required file is missing" if missing
                                   else "Required file cannot be read within path and size limits") from None
    except OSError as exc:
        raise ProjectMetadataError("inspection_incomplete", location, "Required file cannot be read") from None


def _parse(raw, location, code):
    try:
        # json.loads(bytes) can autodetect UTF-16/32. Decode explicitly so the
        # project contract accepts only UTF-8; strict_json also rejects BOM,
        # duplicate keys, nonfinite numbers and unpaired surrogates.
        data = strict_json(raw.decode("utf-8", errors="strict"))
        if not isinstance(data, dict):
            raise ValueError("Object required")
        return data
    except (DataError, ValueError, TypeError, RecursionError) as exc:
        raise ProjectMetadataError(code, location, "Expected a UTF-8 JSON object with unique keys and valid Unicode") from None


def validate_project_metadata(data, schemas):
    """Validate the four fields without assigning IDs or changing input."""
    if not isinstance(data, dict):
        raise ProjectMetadataError("metadata_invalid", "project.json#", "Expected an object")
    if set(data) - set(FIELDS):
        raise ProjectMetadataError("project_fields_unsupported", "project.json#", "Unknown fields are unsupported")
    for field in FIELDS:
        if field not in data:
            raise ProjectMetadataError("metadata_invalid", "project.json#/" + field, "Required field is missing")
    version = data["project_format_version"]
    if isinstance(version, str) and version != "1.0":
        raise ProjectMetadataError("project_format_unsupported", "project.json#/project_format_version", "Unsupported project format")
    try:
        schemas.validate("project_metadata", data)
    except (DataError, ValueError, TypeError, RecursionError) as exc:
        raise ProjectMetadataError("metadata_invalid", "project.json#", "Invalid project metadata fields") from None


def check_project_file(path, schemas):
    """File-only format check, without world association or source echo."""
    raw = _read(Path(path), "project.json#")
    validate_project_metadata(_parse(raw, "project.json#", "metadata_invalid"), schemas)
    return {"status": "metadata_valid", "scope": "project_metadata_format",
            "project_sha256": hashlib.sha256(raw).hexdigest()}


def check_project(root, engine=None):
    """Check two local files; never construct WorldWorkspace or invoke Git.

    Rereading detects observed changes, not ABA races or an atomic snapshot.
    This output cannot support registration, synchronization or Canon approval.
    """
    engine = engine if isinstance(engine, EngineResources) else EngineResources(engine) if engine else EngineResources.default()
    try:
        root = checked_root(root)
        if not root.is_dir() or not disjoint(root, engine.root):
            raise ValueError("External directory required")
    except (DataError, OSError, ValueError) as exc:
        raise ProjectMetadataError("inspection_incomplete", "project.json#", "Select an external directory without links or engine overlap") from None
    schemas = engine.schemas
    project_path = root / "project.json"
    world_path = root / "world/world.json"
    # Validate world metadata even for legacy projects. This is not a full
    # collect_world/Canon validation, and never writes a workspace descriptor.
    world_raw = _read(world_path, "world/world.json#")
    world = _parse(world_raw, "world/world.json#", "inspection_incomplete")
    try:
        schemas.validate("world", world)
    except (DataError, ValueError, TypeError, RecursionError) as exc:
        raise ProjectMetadataError("inspection_incomplete", "world/world.json#", "World metadata is invalid or unsupported") from None
    project_raw = _read(project_path, "project.json#", missing_code="legacy_metadata_missing")
    project = _parse(project_raw, "project.json#", "metadata_invalid")
    validate_project_metadata(project, schemas)
    if project["world_id"] != world["world_id"]:
        raise ProjectMetadataError("identity_conflict", "project.json#/world_id", "Project and world identities differ")
    if (_read(world_path, "world/world.json#") != world_raw
            or _read(project_path, "project.json#") != project_raw):
        raise ProjectMetadataError("baseline_changed", "project.json#", "Input changed during the read-only check")
    return {"status": "metadata_valid", "scope": "project_metadata_and_world_identity",
            "project_sha256": hashlib.sha256(project_raw).hexdigest(),
            "world_sha256": hashlib.sha256(world_raw).hexdigest()}
