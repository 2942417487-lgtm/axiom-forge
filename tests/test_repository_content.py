"""Host storage tests use only temporary, synthetic content and fault injection."""

import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import traceback
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from axiom_forge.ids import new_id
from axiom_forge.repository_content import ContentStoreError, RepositoryContentStore
from axiom_forge.tools.storage import MAX_BYTES
from axiom_forge.workspaces import EngineResources


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = EngineResources(ROOT)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="axiom-content-tests-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.host, self.world = self.base / "host", self.base / "world"
        self.world.mkdir()
        self.operation = new_id("repository_operation")

    def create(self, operation=None, host=None, world=None):
        return RepositoryContentStore.create(host or self.host, operation or self.operation,
                                             world_root=world or self.world, engine=self.engine)

    def reopen(self, operation=None, host=None):
        return RepositoryContentStore(host or self.host, operation or self.operation,
                                      world_root=self.world, engine=self.engine)

    def mutate(self, path, sql, values=()):
        # Deliberate on-disk tampering is the input under test, not a verification
        # side channel. Assertions observe the public store API.
        connection = sqlite3.connect(path)
        try:
            connection.execute(sql, values)
            connection.commit()
        finally:
            connection.close()

    def test_original_bytes_empty_binary_and_json_survive_reopen(self):
        store = self.create()
        for raw in (b"", b"\x00\xff\x01", b' {"synthetic":true}\n', "合成记录".encode()):
            reference = store.put("checks", raw)
            self.assertEqual(set(reference), {"record_id", "sha256"})
            self.assertEqual(reference["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(self.reopen().read(reference, expected_kind="checks"), raw)

    def test_opaque_type_label_never_creates_execution_authority(self):
        store = self.create()
        raw = b'{"decision":"accepted","issuer":"synthetic"}'
        reference = store.put("checks", raw)
        self.assertEqual(store.read(reference, expected_kind="checks"), raw)
        with self.assertRaises(ContentStoreError):
            store.read(reference, expected_kind="host_verification")
        self.assertEqual(list(self.world.iterdir()), [])

    def test_identical_payloads_get_new_immutable_record_identities(self):
        store = self.create()
        first, second = store.put("checks", b"abc"), store.put("checks", b"abc")
        self.assertNotEqual(first["record_id"], second["record_id"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(store.read(first, expected_kind="checks"), b"abc")

    def test_create_never_replaces_existing_store(self):
        store = self.create()
        reference = store.put("coverage", b"original")
        before = store.path.read_bytes()
        with self.assertRaises(ContentStoreError) as caught:
            self.create()
        self.assertEqual(caught.exception.code, "store_exists")
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(self.reopen().read(reference, expected_kind="coverage"), b"original")

    def test_id_collision_cannot_overwrite_original_record(self):
        store = self.create()
        original = store.put("checks", b"original")
        with patch("axiom_forge.repository_content.uuid4", return_value=UUID(original["record_id"])):
            with self.assertRaises(ContentStoreError) as caught:
                store.put("checks", b"replacement")
        self.assertEqual(caught.exception.code, "write_unconfirmed")
        self.assertEqual(self.reopen().read(original, expected_kind="checks"), b"original")

    def test_wrong_type_operation_and_missing_record_are_rejected(self):
        store = self.create()
        reference = store.put("comparison", b"synthetic")
        for expected in ("checks", "unknown", None, []):
            with self.assertRaises(ContentStoreError):
                store.read(reference, expected_kind=expected)
        other = self.create(operation=new_id("repository_operation"))
        with self.assertRaises(ContentStoreError):
            other.read(reference, expected_kind="comparison")
        self.mutate(store.path, "UPDATE records SET operation_id = ?", (other.operation_id,))
        with self.assertRaises(ContentStoreError):
            store.read(reference, expected_kind="comparison")

    def test_content_ref_shape_and_hash_are_required(self):
        store = self.create()
        original = store.put("checks", b"abc")
        for reference in (None, [], "path", {**original, "path": "somewhere"},
                          {**original, "record_id": "../outside"},
                          {**original, "sha256": "a" * 64},
                          {**original, "sha256": original["sha256"].upper()}):
            with self.assertRaises(ContentStoreError):
                store.read(reference, expected_kind="checks")

    def test_kind_and_payload_limits_fail_before_insert(self):
        store = self.create()
        for kind, raw in (("not_registered", b"a"), ([], b"a"), ("checks", "a"),
                          ("checks", bytearray(b"a")), ("checks", b"a" * (MAX_BYTES + 1))):
            with self.assertRaises(ContentStoreError):
                store.put(kind, raw)
        raw = b"a" * MAX_BYTES
        reference = store.put("checks", raw)
        self.assertEqual(store.read(reference, expected_kind="checks"), raw)

    def test_content_hash_damage_is_detected_even_when_size_matches(self):
        store = self.create()
        reference = store.put("checks", b"abc")
        self.mutate(store.path, "UPDATE records SET payload = ?", (b"abd",))
        with self.assertRaises(ContentStoreError) as caught:
            self.reopen().read(reference, expected_kind="checks")
        self.assertEqual(caught.exception.code, "record_corrupt")

    def test_record_type_hash_and_size_metadata_damage_is_detected(self):
        for column, value in (("record_kind", "comparison"), ("sha256", "b" * 64), ("byte_length", 4)):
            operation = new_id("repository_operation")
            store = self.create(operation=operation)
            reference = store.put("checks", b"abc")
            connection = sqlite3.connect(store.path)
            try:
                connection.execute("PRAGMA ignore_check_constraints=ON")
                connection.execute("UPDATE records SET " + column + " = ?", (value,))
                connection.commit()
            finally:
                connection.close()
            with self.subTest(column=column), self.assertRaises(ContentStoreError):
                store.read(reference, expected_kind="checks")

    def test_missing_record_and_invalid_database_do_not_recreate_data(self):
        store = self.create()
        reference = store.put("checks", b"abc")
        self.mutate(store.path, "DELETE FROM records")
        with self.assertRaises(ContentStoreError) as caught:
            store.read(reference, expected_kind="checks")
        self.assertEqual(caught.exception.code, "record_missing")
        store.path.write_bytes(b"synthetic damaged database")
        with self.assertRaises(ContentStoreError):
            self.reopen()
        self.assertEqual(store.path.read_bytes(), b"synthetic damaged database")

    def test_schema_version_and_owner_metadata_damage_stop_open(self):
        for column, value in (("format_version", "2.0"), ("operation_id", new_id("repository_operation")),
                              ("store_id", "invalid"), ("location_sha256", "a" * 64)):
            operation = new_id("repository_operation")
            store = self.create(operation=operation)
            self.mutate(store.path, "UPDATE store_info SET " + column + " = ?", (value,))
            with self.subTest(column=column), self.assertRaises(ContentStoreError):
                self.reopen(operation=operation)

    def test_unknown_database_objects_are_rejected(self):
        store = self.create()
        self.mutate(store.path, "CREATE TABLE sqlitex_extra (value TEXT)")
        with self.assertRaises(ContentStoreError):
            self.reopen()

    def test_copied_or_moved_store_does_not_rebind_itself(self):
        store = self.create()
        other_host = self.base / "other-host"
        copied = other_host / "repository-operations" / self.operation / "content.sqlite3"
        copied.parent.mkdir(parents=True)
        shutil.copyfile(store.path, copied)
        before = copied.read_bytes()
        with self.assertRaises(ContentStoreError):
            self.reopen(host=other_host)
        self.assertEqual(copied.read_bytes(), before)

    def test_existing_handle_detects_database_identity_replacement(self):
        store = self.create()
        reference = store.put("checks", b"abc")
        self.mutate(store.path, "UPDATE store_info SET store_id = ?",
                    ("000000ff-0000-4000-8000-000000000000",))
        with self.assertRaises(ContentStoreError):
            store.read(reference, expected_kind="checks")

    def test_missing_store_open_has_no_creation_side_effect(self):
        with self.assertRaises(ContentStoreError):
            self.reopen()
        self.assertFalse(self.host.exists())

    def test_host_world_engine_and_git_boundaries(self):
        for host, world in ((ROOT / ".cache/content-not-created", self.world),
                            (self.world / "private", self.world),
                            (self.base, self.world), (self.host, ROOT / "templates/legacy-world"),
                            (Path("relative-host"), self.world), (self.host, self.base / "absent")):
            with self.subTest(host=host, world=world), self.assertRaises(ContentStoreError):
                self.create(host=host, world=world)
        git_root = self.base / "git"
        (git_root / ".git").mkdir(parents=True)
        with self.assertRaises(ContentStoreError):
            self.create(host=git_root / "host")
        self.assertFalse((git_root / "host").exists())

    def test_invalid_operation_ids_do_not_become_paths(self):
        for operation in ("RPO-../outside", "RUN-00000001-0000-4000-8000-000000000000",
                          "RPO-00000001-0000-5000-8000-000000000000", "RPO-0000000A-0000-4000-8000-000000000000"):
            with self.assertRaises(ContentStoreError):
                self.create(operation=operation)
        self.assertFalse(self.host.exists())

    def test_bare_git_boundary_is_checked_before_creation_and_on_each_access(self):
        bare = self.base / "synthetic-bare.git"
        (bare / "objects").mkdir(parents=True)
        (bare / "refs/heads").mkdir(parents=True)
        (bare / "HEAD").write_bytes(b"ref: refs/heads/main\n")
        (bare / "config").write_bytes(b"[core]\n bare = true\n")
        before = sorted(p.relative_to(bare).as_posix() for p in bare.rglob("*"))
        for host in (bare, bare / "private-host"):
            with self.assertRaises(ContentStoreError):
                self.create(host=host)
            self.assertEqual(sorted(p.relative_to(bare).as_posix() for p in bare.rglob("*")), before)
        store = self.create()
        reference = store.put("checks", b"original")
        database_before = store.path.read_bytes()
        (self.host / "objects").mkdir()
        (self.host / "refs").mkdir()
        (self.host / "HEAD").write_bytes(b"ref: refs/heads/main\n")
        with self.assertRaises(ContentStoreError):
            store.read(reference, expected_kind="checks")
        with self.assertRaises(ContentStoreError):
            store.put("checks", b"replacement")
        self.assertEqual(store.path.read_bytes(), database_before)

    def test_links_sidecars_and_nonregular_files_are_refused(self):
        store = self.create()
        reference = store.put("checks", b"abc")
        sidecar = Path(str(store.path) + "-wal")
        sidecar.write_bytes(b"synthetic")
        with self.assertRaises(ContentStoreError):
            store.read(reference, expected_kind="checks")
        sidecar.unlink()
        journal = Path(str(store.path) + "-journal")
        journal.mkdir()
        with self.assertRaises(ContentStoreError):
            store.read(reference, expected_kind="checks")
        journal.rmdir()
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda p: p == self.host or original(p)):
            with self.assertRaises(ContentStoreError):
                store.read(reference, expected_kind="checks")

    def test_hardlinked_database_is_refused(self):
        store = self.create()
        reference = store.put("checks", b"abc")
        alias = self.base / "hardlink.sqlite3"
        os.link(store.path, alias)
        with self.assertRaises(ContentStoreError):
            store.read(reference, expected_kind="checks")

    def test_failed_initialization_preserves_partial_file(self):
        with patch("axiom_forge.repository_content.sqlite3.connect",
                   side_effect=sqlite3.OperationalError("SYNTHETIC_SECRET_DO_NOT_ECHO")):
            with self.assertRaises(ContentStoreError) as caught:
                self.create()
        self.assertEqual(caught.exception.code, "initialization_unconfirmed")
        path = self.host / "repository-operations" / self.operation / "content.sqlite3"
        self.assertTrue(path.exists())
        with self.assertRaises(ContentStoreError):
            self.reopen()
        with self.assertRaises(ContentStoreError):
            self.create()

    def test_failed_postcommit_read_reports_unknown_write_with_reference(self):
        store = self.create()
        with patch.object(RepositoryContentStore, "read", side_effect=ContentStoreError("store_unavailable")):
            with self.assertRaises(ContentStoreError) as caught:
                store.put("checks", b"committed")
        self.assertEqual(caught.exception.code, "write_unconfirmed")
        self.assertEqual(self.reopen().read(caught.exception.reference, expected_kind="checks"), b"committed")

    def test_safe_diagnostics_hide_payload_paths_and_driver_messages(self):
        store = self.create()
        sensitive = b"SYNTHETIC_SECRET_DO_NOT_ECHO"
        with patch("axiom_forge.repository_content.sqlite3.connect",
                   side_effect=sqlite3.OperationalError("SYNTHETIC_SECRET_DO_NOT_ECHO")):
            try:
                store.put("checks", sensitive)
            except ContentStoreError as error:
                report = "".join(traceback.format_exception(error))
                self.assertNotIn("SYNTHETIC_SECRET", report)
                self.assertNotIn(str(store.path), str(error))
                self.assertEqual(error.code, "write_unconfirmed")
            else:
                self.fail("Driver failure must propagate as a safe store status")

    def test_concurrent_creation_and_writers_preserve_records(self):
        def create_once(_):
            try:
                return self.create()
            except ContentStoreError as error:
                self.assertEqual(error.code, "store_exists")
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            stores = [s for s in pool.map(create_once, range(2)) if s is not None]
        self.assertEqual(len(stores), 1)
        store = stores[0]
        with ThreadPoolExecutor(max_workers=4) as pool:
            references = list(pool.map(lambda n: store.put("checks", f"synthetic-{n}".encode()), range(8)))
        self.assertEqual(len({r["record_id"] for r in references}), 8)
        for i, reference in enumerate(references):
            self.assertEqual(self.reopen().read(reference, expected_kind="checks"), f"synthetic-{i}".encode())

    def test_locked_writer_fails_boundedly_without_automatic_retry(self):
        store = self.create()
        reference = store.put("checks", b"original")
        connection = sqlite3.connect(store.path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            with self.assertRaises(ContentStoreError) as caught:
                store.put("checks", b"blocked")
            self.assertEqual(caught.exception.code, "write_unconfirmed")
        finally:
            connection.close()
        self.assertEqual(store.read(reference, expected_kind="checks"), b"original")

    def test_process_exit_before_and_after_commit_preserves_atomic_record(self):
        store = self.create()
        original = store.put("checks", b"original")
        for after in (False, True):
            record_id = ("0000000b" if after else "0000000a") + "-0000-4000-8000-000000000000"
            script = f'''
import os, sqlite3
from uuid import UUID
import axiom_forge.repository_content as module
real = sqlite3.connect
class CrashConnection(sqlite3.Connection):
    def execute(self, sql, *args):
        if sql == "COMMIT":
            if {after!r}:
                super().execute(sql, *args)
            os._exit(71)
        return super().execute(sql, *args)
sqlite3.connect = lambda *a, **k: real(*a, **k, factory=CrashConnection)
module.uuid4 = lambda: UUID({record_id!r})
store = module.RepositoryContentStore({str(self.host)!r}, {self.operation!r}, world_root={str(self.world)!r})
store.put("checks", b"x" * 2097152)
'''
            process = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, timeout=20)
            self.assertEqual(process.returncode, 71, process.stderr.decode(errors="replace"))
            reopened = self.reopen()
            self.assertEqual(reopened.read(original, expected_kind="checks"), b"original")
            reference = {"record_id": record_id, "sha256": hashlib.sha256(b"x" * MAX_BYTES).hexdigest()}
            if after:
                self.assertEqual(reopened.read(reference, expected_kind="checks"), b"x" * MAX_BYTES)
            else:
                with self.assertRaises(ContentStoreError) as caught:
                    reopened.read(reference, expected_kind="checks")
                self.assertEqual(caught.exception.code, "record_missing")
