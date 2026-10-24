"""Local host-only immutable content records, backed by SQLite transactions.

No Agent tool, receipt issuer, permission verifier or world repository writer.
The host selects all roots and expected record kinds; bytes remain opaque.
"""

import hashlib
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from .tools.storage import MAX_BYTES, check_links
from .validation import DataError
from .workspaces import EngineResources, checked_root, disjoint


RECORD_KINDS = frozenset((
    "source_selection", "target_selection", "host_context", "policy", "engine_resources",
    "limits", "sensitive_preflight", "source_capture", "target_before", "coverage", "checks",
    "comparison", "write_projection", "merge_verification", "actor", "host_verification",
    "execution_intent", "before", "after", "effects", "preservation", "saved_records", "diagnostics",
))
FORMAT_VERSION = "1.0"
TABLES = {
    "store_info": """CREATE TABLE store_info (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        format_version TEXT NOT NULL, operation_id TEXT NOT NULL,
        store_id TEXT NOT NULL, location_sha256 TEXT NOT NULL)""",
    "records": """CREATE TABLE records (
        record_id TEXT PRIMARY KEY NOT NULL, operation_id TEXT NOT NULL,
        record_kind TEXT NOT NULL, byte_length INTEGER NOT NULL,
        sha256 TEXT NOT NULL, payload BLOB NOT NULL,
        CHECK (typeof(payload) = 'blob' AND length(payload) = byte_length),
        CHECK (byte_length >= 0 AND byte_length <= 2097152))""",
}


class ContentStoreError(DataError):
    """Safe status only. A write error may carry its generated reference."""

    def __init__(self, code, reference=None, *, cause_code=None):
        self.code = code
        self.cause_code = cause_code
        self.reference = dict(reference) if reference is not None else None
        super().__init__(code if cause_code is None else f"{code}: {cause_code}")


def _require(condition, code):
    if not condition:
        raise ContentStoreError(code)


def _uuid4(value):
    try:
        parsed = UUID(value)
        return parsed.version == 4 and str(parsed) == value
    except (ValueError, TypeError, AttributeError):
        return False


class RepositoryContentStore:
    """One operation's host-private store. Construction opens an existing store.

    Use create() for a new store. There is no replace, delete or migration API.
    Filesystem checks detect observed links/overlap, not hostile OS-level races.
    """

    def __init__(self, host_root, operation_id, *, world_root, engine=None):
        self._configure(host_root, operation_id, world_root, engine)
        # An rw connection lets SQLite recover its own uncommitted journal.
        # This never replays a receipt, acceptance or repository operation.
        with self._connection(recover=True) as connection:
            self._check_store(connection)

    @classmethod
    def create(cls, host_root, operation_id, *, world_root, engine=None):
        store = cls.__new__(cls)
        store._configure(host_root, operation_id, world_root, engine)
        try:
            store.path.parent.mkdir(parents=True, exist_ok=True)
            store._check_paths()
            # Claim the name exclusively; SQLite mode=rw never creates files.
            with store.path.open("xb"):
                pass
        except FileExistsError:
            raise ContentStoreError("store_exists") from None
        except (OSError, DataError, ValueError):
            raise ContentStoreError("store_path_invalid") from None
        store.store_id = str(uuid4())
        try:
            with store._connection(write=True) as connection:
                for sql in TABLES.values():
                    connection.execute(sql)
                connection.execute("INSERT INTO store_info VALUES (1, ?, ?, ?, ?)", (
                    FORMAT_VERSION, store.operation_id, store.store_id, store.location_sha256))
            # Independent connection checks actual saved schema and metadata.
            with store._connection() as connection:
                store._check_store(connection)
        except ContentStoreError as error:
            # Preserve empty/partial files for explicit operator diagnosis.
            raise ContentStoreError("initialization_unconfirmed", cause_code=error.code) from None
        return store

    def _configure(self, host_root, operation_id, world_root, engine):
        _require(isinstance(operation_id, str) and operation_id.startswith("RPO-")
                 and _uuid4(operation_id[4:]), "operation_id_invalid")
        self.operation_id = operation_id
        self.store_id = None
        try:
            self.engine = (engine if isinstance(engine, EngineResources) else
                           EngineResources(engine) if engine else EngineResources.default())
            _require(Path(host_root).is_absolute() and Path(world_root).is_absolute(), "store_path_invalid")
            self.host_root, self.world_root = checked_root(host_root), checked_root(world_root)
            self.path = self.host_root / "repository-operations" / operation_id / "content.sqlite3"
            self.location_sha256 = hashlib.sha256(os.path.normcase(str(self.path)).encode("utf-8")).hexdigest()
            self.schemas = self.engine.schemas
            self._check_paths()
        except (DataError, OSError, ValueError, TypeError, RuntimeError):
            raise ContentStoreError("store_path_invalid") from None

    def _check_paths(self):
        try:
            # Recheck the selected roots on every access, including ancestor links.
            for root in (self.host_root, self.world_root, self.engine.root):
                check_links(root)
            _require(self.world_root.is_dir() and disjoint(self.world_root, self.engine.root)
                     and disjoint(self.host_root, self.world_root)
                     and disjoint(self.host_root, self.engine.root), "store_path_invalid")
            _require(not any(
                (parent / ".git").exists() or (
                    (parent / "HEAD").exists() and (parent / "objects").is_dir()
                    and (parent / "refs").is_dir())
                for parent in (self.path.parent, *self.path.parent.parents)), "store_path_invalid")
            for suffix in ("", "-journal", "-wal", "-shm"):
                candidate = Path(str(self.path) + suffix)
                check_links(candidate)
                if candidate.exists():
                    stat = candidate.stat()
                    _require(candidate.is_file() and stat.st_nlink == 1, "store_path_invalid")
                    _require(suffix not in ("-wal", "-shm"), "store_path_invalid")
        except (OSError, DataError, ValueError):
            raise ContentStoreError("store_path_invalid") from None

    @contextmanager
    def _connection(self, *, write=False, recover=False):
        self._check_paths()
        connection = None
        try:
            uri = self.path.as_uri() + ("?mode=rw" if write or recover else "?mode=ro")
            connection = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=1.0)
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_BYTES + 4096)
            connection.execute("PRAGMA trusted_schema=OFF")
            _require(connection.execute("PRAGMA trusted_schema").fetchone() == (0,), "store_settings_unsupported")
            _require(connection.execute("PRAGMA journal_mode").fetchone() == ("delete",), "store_settings_unsupported")
            if write:
                connection.execute("PRAGMA synchronous=EXTRA")
                _require(connection.execute("PRAGMA synchronous").fetchone() == (3,), "store_settings_unsupported")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            if write:
                connection.execute("COMMIT")
        except (sqlite3.Error, OSError, ValueError):
            raise ContentStoreError("store_unavailable") from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except sqlite3.Error:
                    raise ContentStoreError("store_unavailable") from None

    def _check_store(self, connection):
        _require(connection.execute("PRAGMA quick_check(1)").fetchall() == [("ok",)], "store_corrupt")
        schema = connection.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL").fetchall()
        _require(sorted(schema) == sorted(TABLES.items()), "store_format_unsupported")
        rows = connection.execute("SELECT * FROM store_info").fetchall()
        _require(len(rows) == 1, "store_context_mismatch")
        singleton, version, operation_id, store_id, location = rows[0]
        _require(singleton == 1 and version == FORMAT_VERSION and operation_id == self.operation_id
                 and _uuid4(store_id) and location == self.location_sha256, "store_context_mismatch")
        _require(self.store_id is None or store_id == self.store_id, "store_context_mismatch")
        self.store_id = store_id

    def put(self, record_kind, raw):
        """Commit a new immutable record, then independently read and verify it.

        On write_unconfirmed, reference identifies the attempted record. The
        caller can explicitly read it later; the store never retries the insert.
        """
        _require(isinstance(record_kind, str) and record_kind in RECORD_KINDS, "record_kind_invalid")
        _require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES, "record_size_or_type_invalid")
        reference = {"record_id": str(uuid4()), "sha256": hashlib.sha256(raw).hexdigest()}
        try:
            with self._connection(write=True) as connection:
                self._check_store(connection)
                connection.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?, ?)", (
                    reference["record_id"], self.operation_id, record_kind, len(raw), reference["sha256"], raw))
            _require(self.read(reference, expected_kind=record_kind) == raw, "record_corrupt")
        except ContentStoreError as error:
            raise ContentStoreError("write_unconfirmed", reference, cause_code=error.code) from None
        return reference

    def read(self, reference, *, expected_kind):
        """Read exactly one record using the host's expected type and operation."""
        _require(isinstance(expected_kind, str) and expected_kind in RECORD_KINDS, "record_kind_invalid")
        try:
            self.schemas.validate("repository_receipt_common", reference)
            _require(set(reference) == {"record_id", "sha256"}, "record_reference_invalid")
        except (DataError, ValueError, TypeError, RecursionError):
            raise ContentStoreError("record_reference_invalid") from None
        with self._connection() as connection:
            self._check_store(connection)
            row = connection.execute(
                "SELECT operation_id, record_kind, byte_length, sha256, payload FROM records WHERE record_id = ?",
                (reference["record_id"],)).fetchone()
        _require(row is not None, "record_missing")
        operation_id, kind, byte_length, sha256, raw = row
        _require(operation_id == self.operation_id and kind == expected_kind, "record_context_mismatch")
        _require(isinstance(raw, bytes) and type(byte_length) is int and byte_length == len(raw)
                 and len(raw) <= MAX_BYTES and sha256 == reference["sha256"]
                 and hashlib.sha256(raw).hexdigest() == sha256, "record_corrupt")
        return raw
