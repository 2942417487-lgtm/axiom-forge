"""Bounded, append-only storage for one trusted host-selected AgentRun."""

import json
import os
import re
import stat
import tempfile
from pathlib import Path, PurePosixPath

from ..validation import DataError, canonical_bytes


MAX_BYTES = 2 * 1024 * 1024


class ToolError(DataError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def strict_json(raw):
    def pairs(items):
        data = {}
        for key, value in items:
            if key in data:
                raise ValueError("Duplicate JSON key")
            data[key] = value
        return data

    def constant(value):
        raise ValueError("Non-finite JSON number")

    try:
        data = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        canonical_bytes(data)
        return data
    except (ValueError, UnicodeError, TypeError) as exc:
        raise ToolError("invalid_json", "Expected finite UTF-8 JSON with unique keys") from exc


def safe_relative(value):
    if not isinstance(value, str) or not value or len(value) > 240:
        raise ToolError("unsafe_path", "Expected a short repository-relative POSIX path")
    path = PurePosixPath(value)
    reserved = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
    if (path.is_absolute() or path.as_posix() != value or "\\" in value
            or any(part in (".", "..") or part.endswith((".", " "))
                   or reserved.match(part) or any(ord(c) < 32 or c in ':<>"|?*' for c in part)
                   for part in path.parts)):
        raise ToolError("unsafe_path", "Noncanonical, reserved or escaping path")
    return path


def check_links(path):
    # Junctions and symlinks are rejected even when they point inside the scope.
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise ToolError("unsafe_path", "Links are not allowed in tool storage paths")
        try:
            attributes = getattr(part.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ToolError("unsafe_path", "Reparse points are not allowed in tool storage paths")


def read_bounded(path, limit=MAX_BYTES):
    path = Path(path).absolute()
    check_links(path)
    if not path.is_file():
        raise ToolError("file_unavailable", "File missing or nonregular")
    if path.stat().st_size > limit:
        raise ToolError("size_limit", "File exceeds size limit")
    with path.open("rb") as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ToolError("size_limit", "File exceeds size limit")
    return raw


class Workspace:
    def __init__(self, root):
        self.root = Path(root).absolute()
        check_links(self.root)

    def path(self, relative):
        path = self.root / safe_relative(relative)
        check_links(path)
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ToolError("unsafe_path", "Path escapes AgentRun workspace")
        return path

    def read(self, relative):
        return read_bounded(self.path(relative))

    def write(self, relative, raw):
        if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
            raise ToolError("size_limit", "Output exceeds size limit")
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path(relative)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=".tmp") as output:
                temporary = Path(output.name)
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            if os.name == "nt":
                os.rename(temporary, path)
            else:
                os.link(temporary, path)
        except FileExistsError as exc:
            raise ToolError("already_exists", "Tool outputs are append-only") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return path

    def write_json(self, relative, data):
        return self.write(relative, canonical_bytes(data) + b"\n")
