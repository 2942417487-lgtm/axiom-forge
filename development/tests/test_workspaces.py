"""Offline engine/world/host separation and copied-workspace replay boundaries."""

from support import EXAMPLES_ROOT as EXAMPLES, LEGACY_ROOT
import copy
import io
import json
import os
import subprocess
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from axiom_forge.__main__ import main
from axiom_forge.canon_host import CanonHost, document
from axiom_forge.git_host import git
from axiom_forge.journal import TaskJournal
from axiom_forge.runtimes.core import AgentRuntime
from axiom_forge.tasks import TaskManager
from axiom_forge.tools.session import ToolSession
from axiom_forge.tools.storage import read_bounded
from axiom_forge.validation import DataError, canonical_bytes, digest, read_json
from axiom_forge.workspaces import EngineResources, WorldWorkspace, create_world, root_identity
from examples.offline_task_manager import ROOT, fixture_factory, initialize_fixture
from tests.test_runtimes import FakeAdapter


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="axiom-workspace-tests-")
        self.base = Path(self.temporary.name).resolve()
        self.engine = EngineResources.default()
        self.host_root = self.base / "host"

    def tearDown(self):
        self.temporary.cleanup()

    def create(self, name="world"):
        path = self.base / name
        receipt = create_world(path, name, engine=self.engine, host_root=self.host_root)
        return WorldWorkspace(path, self.engine, host_root=self.host_root), receipt

    def test_new_world_has_independent_git_snapshot_and_ignored_durable_state(self):
        def engine_state():
            # Only this restricted listing permits managed engine worktree
            # settings. Hash explicit trusted resources; never read credentials.
            return {path.relative_to(ROOT).as_posix(): sha256(read_bounded(path)).hexdigest()
                    for directory in (ROOT / "axiom_forge", ROOT / "resources")
                    for path in directory.rglob("*") if path.is_file() and "__pycache__" not in path.parts}
        before = engine_state()
        world, receipt = self.create()
        self.assertEqual(receipt['status'], 'created')
        self.assertFalse(receipt['github_connected'])
        self.assertFalse(receipt['approval_key_initialized'])
        self.assertEqual(git(world.root, "remote"), b"")
        self.assertEqual(git(world.root, "symbolic-ref", "HEAD").strip(), b"refs/heads/main")
        self.assertTrue(Path(receipt['snapshot']).is_file())
        self.assertEqual(git(world.root, "status", "--porcelain"), b"")
        self.assertEqual(git(world.root, "ls-files", "--", ".axiom/local"), b"")
        self.assertEqual(engine_state(), before)
        self.assertFalse(world.key_path.is_relative_to(world.root))

    def test_nonempty_target_and_nested_engine_are_rejected_without_overwrite(self):
        occupied = self.base / "occupied"
        occupied.mkdir()
        original = occupied / "my-world.md"
        original.write_text("USER CONTENT", encoding="utf-8")
        with self.assertRaises(DataError):
            create_world(occupied, "world", engine=self.engine, host_root=self.host_root)
        self.assertEqual(original.read_text(encoding="utf-8"), "USER CONTENT")
        self.assertFalse((occupied / ".git").exists())
        with self.assertRaises(DataError):
            create_world(ROOT / "world", "world", engine=self.engine)
        self.assertFalse((ROOT / "world").exists())

    def test_parent_git_and_worktree_git_file_are_rejected(self):
        parent, _ = self.create("parent")
        with self.assertRaises(DataError):
            create_world(parent.root / "nested", "nested", engine=self.engine, host_root=self.host_root)
        child = parent.root / "child"
        child.mkdir()
        with self.assertRaises(DataError):
            WorldWorkspace(child, self.engine, host_root=self.host_root)
        linked = self.base / "linked"
        linked.mkdir()
        (linked / ".git").write_text("gitdir: " + str(parent.root / ".git"), encoding="utf-8")
        with self.assertRaises(DataError):
            WorldWorkspace(linked, self.engine, host_root=self.host_root)

    def test_host_overlap_rejected_before_world_creation(self):
        target = self.base / "new"
        with self.assertRaises(DataError):
            create_world(target, "world", engine=self.engine, host_root=target / "host")
        self.assertFalse(target.exists())

    def test_git_commondir_redirection_rejected_before_any_ref_write(self):
        first, _ = self.create('first')
        second, _ = self.create('second')
        (first.root / '.git/commondir').write_text(str(second.root / '.git'), encoding='utf-8')
        with self.assertRaises(DataError):
            WorldWorkspace(first.root, self.engine, host_root=self.host_root)
        with self.assertRaises(DataError):
            git(first.root, 'update-ref', 'refs/heads/unauthorized', git(second.root, 'rev-parse', 'HEAD').decode().strip())
        self.assertEqual(git(second.root, 'for-each-ref', 'refs/heads/unauthorized'), b'')

    def test_default_host_overlap_rejected_before_any_files_are_written(self):
        target = self.base / 'local-appdata'
        with patch.dict(os.environ, {'LOCALAPPDATA': str(target)}), self.assertRaises(DataError):
            create_world(target, 'world', engine=self.engine)
        self.assertFalse(target.exists())

    def test_git_filter_is_rejected_without_executing_external_program(self):
        world, _ = self.create()
        marker = self.base / 'MUST-NOT-EXIST.txt'
        # Inject configuration using the test's direct Git process, bypassing the
        # protected application API solely to construct this malicious fixture.
        result = subprocess.run(['git', '-C', str(world.root), 'config', '--local',
            'filter.synthetic.clean', 'powershell.exe -NoProfile -Command "Set-Content -LiteralPath ' + str(marker) + ' -Value SYNTHETIC"'],
            capture_output=True, check=False)
        self.assertEqual(result.returncode, 0)
        (world.root / '.gitattributes').write_text('world/world.json filter=synthetic\n', encoding='utf-8')
        metadata = world.root / 'world/world.json'
        metadata.write_text(metadata.read_text(encoding='utf-8').replace('Empty world', 'EMPTY world'), encoding='utf-8')
        with self.assertRaisesRegex(DataError, 'filters'):
            git(world.root, 'status', '--porcelain')
        with self.assertRaises(DataError):
            WorldWorkspace(world.root, self.engine, host_root=self.host_root)
        self.assertFalse(marker.exists())

    def test_git_include_is_rejected_before_loading_external_configuration(self):
        world, _ = self.create()
        external = self.base / 'external-config'
        external.write_text('[filter "synthetic"]\n clean = forbidden\n', encoding='utf-8')
        result = subprocess.run(['git', '-C', str(world.root), 'config', '--local', 'include.path', str(external)], capture_output=True)
        self.assertEqual(result.returncode, 0)
        with self.assertRaisesRegex(DataError, 'includes'):
            git(world.root, 'status', '--porcelain')

    def test_host_files_cannot_come_from_world_or_engine(self):
        world, _ = self.create()
        for path in (world.root / 'host.json', self.engine.root / '.env'):
            with self.assertRaises(DataError):
                world.host_file(path)
        self.assertEqual(world.host_file(self.host_root / '.env'), (self.host_root / '.env').resolve())

    def test_worktree_configuration_cannot_bypass_filter_validation(self):
        world, _ = self.create()
        result = subprocess.run(['git', '-C', str(world.root), 'config', '--local',
                                 'extensions.worktreeConfig', 'true'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        with self.assertRaises(DataError):
            git(world.root, 'status', '--porcelain')
        (world.root / '.git/config.worktree').write_text('[filter "synthetic"]\n clean = forbidden\n', encoding='utf-8')
        with self.assertRaisesRegex(DataError, 'worktree configuration'):
            WorldWorkspace(world.root, self.engine, host_root=self.host_root)

    def test_nested_git_ref_link_rejected_before_external_ref_write(self):
        first, _ = self.create('first')
        second, _ = self.create('second')
        link = first.root / '.git/refs/heads/canon'
        try:
            os.symlink(second.root / '.git/refs/heads', link, target_is_directory=True)
        except OSError as exc:
            self.skipTest('OS does not permit creation of a synthetic directory symlink: ' + str(exc))
        with self.assertRaises(DataError):
            git(first.root, 'update-ref', 'refs/heads/canon/unauthorized', git(second.root, 'rev-parse', 'HEAD').decode().strip())
        self.assertFalse((second.root / '.git/refs/heads/unauthorized').exists())

    def test_same_world_copy_requires_migration_and_cannot_reuse_binding(self):
        world, _ = self.create()
        cloned = self.base / "clone"
        shutil.copytree(world.root, cloned)
        self.assertEqual(git(world.root, "rev-parse", "HEAD"), git(cloned, "rev-parse", "HEAD"))
        with self.assertRaisesRegex(DataError, "moved|binding"):
            WorldWorkspace(cloned, self.engine, host_root=self.host_root)
        # Even replacing the local descriptor cannot reuse the old binding.
        descriptor = cloned / ".axiom/local/workspace.json"
        adjusted = world.binding
        adjusted['root_sha256'] = root_identity(cloned.resolve())
        descriptor.write_bytes(canonical_bytes(adjusted))
        other = WorldWorkspace(cloned, self.engine, host_root=self.host_root)
        with self.assertRaises(DataError):
            other.validate_binding(world.binding)
        self.assertNotEqual(world.key_path, other.key_path)

    def test_legacy_records_are_preserved_and_rejected(self):
        world, _ = self.create()
        descriptor = world.state.path("workspace.json")
        descriptor.unlink()
        legacy = world.root / ".cache/tasks/legacy.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text('{"legacy":true}', encoding="utf-8")
        with self.assertRaisesRegex(DataError, "Legacy"):
            WorldWorkspace(world.root, self.engine, host_root=self.host_root)
        self.assertEqual(legacy.read_text(encoding="utf-8"), '{"legacy":true}')
        self.assertFalse(descriptor.exists())

    def test_tracked_local_state_is_rejected(self):
        world, _ = self.create()
        git(world.root, "add", "-f", "--", ".axiom/local/workspace.json")
        with self.assertRaisesRegex(DataError, "tracked"):
            WorldWorkspace(world.root, self.engine, host_root=self.host_root)

    def test_cli_requires_explicit_world_and_rejects_legacy_repo(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(['validate-world']), 1)
            self.assertEqual(main(['--repo', str(ROOT), 'check-schemas']), 1)
            self.assertEqual(main(['check-schemas']), 0)
        world, _ = self.create()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--world', str(world.root), '--host-root', str(self.host_root), 'world', 'check']), 0)
            self.assertEqual(main(['--world', str(world.root), '--host-root', str(self.host_root), 'validate-world']), 0)

    def test_creation_failure_preserves_partial_files_and_never_reports_success(self):
        from axiom_forge import workspaces
        original = workspaces.git
        target = self.base / "partial"
        def fail(root, *args, **kwargs):
            if args[0] == 'init': raise DataError('SYNTHETIC Git unavailable')
            return original(root, *args, **kwargs)
        with patch.object(workspaces, 'git', fail), self.assertRaises(DataError):
            create_world(target, "world", engine=self.engine, host_root=self.host_root)
        self.assertTrue((target / 'world/world.json').is_file())
        with self.assertRaises(DataError):
            create_world(target, "world", engine=self.engine, host_root=self.host_root)

    def test_engine_boundary_accepts_managed_worktree_config_with_read_only_listing(self):
        host = initialize_fixture(self.base)
        engine = host.world.engine.root
        git(engine, 'init', '-b', 'main')
        git(engine, 'add', '--', 'resources/policies')
        result = subprocess.run(['git', '-C', str(engine), 'config', '--local',
                                 'extensions.worktreeConfig', 'true'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        # Trusted developer worktree configuration is supported, with execution
        # helpers disabled. World Git access retains its strict rejection.
        (engine / '.git/config.worktree').write_text('[core]\n fsmonitor = forbidden-synthetic-fsmonitor\n', encoding='utf-8')
        error = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(error):
            result = main(['--engine-root', str(engine), 'check-system-boundary'])
        self.assertEqual(result, 0, error.getvalue())
        with self.assertRaises(DataError):
            git(engine, 'status', '--porcelain')
        with self.assertRaises(DataError):
            git(engine, 'update-ref', 'refs/heads/forbidden', '0' * 40, engine_listing=True)
        private = engine / '.axiom/local/private.json'
        private.parent.mkdir(parents=True)
        private.write_text('{"synthetic":true}', encoding='utf-8')
        result = subprocess.run(['git', '-C', str(engine), '-c', 'core.fsmonitor=false',
                                 'add', '--', '.axiom/local/private.json'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--engine-root', str(engine), 'check-system-boundary']), 1)


class WorkspaceExecutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="axiom-workspace-execution-")
        self.base = Path(self.temporary.name).resolve()
        self.host = initialize_fixture(self.base)
        self.world = self.host.world
        self.config = read_json(EXAMPLES / 'mode-host.json')
        self.config['max_cost_usd'] = 20

    def tearDown(self):
        self.temporary.cleanup()

    async def test_world_rules_are_data_and_engine_resources_are_authoritative(self):
        for name in ('AGENTS.md', 'agents/researcher.md', 'modes/court.md', 'tools/python-scripts/manifest.json', 'schemas/world.schema.json'):
            path = self.world.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('UNTRUSTED_WORLD_EXECUTION_RULE', encoding='utf-8')
        data = read_json(EXAMPLES / 'agents/researcher-input.json')
        output = read_json(EXAMPLES / 'research_result.json')
        adapter = FakeAdapter(output)
        runtime = AgentRuntime(self.world, adapter)
        packet = await runtime.run_input(data)
        self.assertEqual(packet['agent_run']['status'], 'completed')
        self.assertNotIn('UNTRUSTED_WORLD_EXECUTION_RULE', adapter.instructions)
        self.assertEqual(runtime.engine_root, self.world.engine.root)
        self.assertTrue((self.world.root / packet['artifact']['path']).is_file())
        self.assertFalse((self.world.engine.root / packet['artifact']['path']).exists())

    async def test_two_worlds_keep_tasks_artifacts_and_git_independent(self):
        second_dir = self.base / 'second-fixture'
        second_dir.mkdir()
        second = initialize_fixture(second_dir).world
        # The synthetic fixtures intentionally share world_id. Local workspace
        # identity must still isolate their records and Git commits.
        self.assertEqual(self.world.world_id, second.world_id)
        first_head = git(self.world.root, 'rev-parse', 'HEAD')
        second_head = git(second.root, 'rev-parse', 'HEAD')
        results = []
        for world in (self.world, second):
            manager = TaskManager(world, self.config, runtime_factory=fixture_factory(world, proposals=False))
            result = await manager.run('SYNTHETIC isolated workspace', 'court', ['TECH-001'])
            self.assertEqual(result['status'], 'completed')
            results.append(result)
            task = document(Path(result['state_path']))
            self.assertEqual(task['metadata']['workspace_binding'], world.binding)
            for artifact in task['artifacts']:
                self.assertTrue((world.root / artifact['path']).exists())
        self.assertNotEqual(results[0]['task_id'], results[1]['task_id'])
        self.assertFalse((second.root / '.axiom/local/tasks' / results[0]['task_id']).exists())
        self.assertEqual(git(self.world.root, 'rev-parse', 'HEAD'), first_head)
        self.assertEqual(git(second.root, 'rev-parse', 'HEAD'), second_head)

    async def test_copied_task_approval_and_recovery_rejected_even_with_same_key(self):
        manager = TaskManager(self.world, self.config, runtime_factory=fixture_factory(self.world))
        result = await manager.run('SYNTHETIC replay protection', 'court', ['TECH-001'])
        self.assertEqual(result['status'], 'waiting_approval')
        self.host.init_key()  # Synthetic temporary host only, never real credentials.
        review = result['review']
        self.host.decide(Path(review['bundle']), 'SYNTHETIC operator', review['sha256'])
        clone = self.base / 'clone'
        shutil.copytree(self.world.root, clone)
        altered = self.world.binding
        altered['root_sha256'] = root_identity(clone.resolve())
        (clone / '.axiom/local/workspace.json').write_bytes(canonical_bytes(altered))
        other = WorldWorkspace(clone, self.world.engine, host_root=self.world.host_root)
        other.key_path.parent.mkdir(parents=True)
        shutil.copyfile(self.host.key_path, other.key_path)  # Explicit synthetic replay attack.
        copied_bundle = clone / Path(review['bundle']).relative_to(self.world.root)
        with self.assertRaises(DataError):
            CanonHost(other).apply(copied_bundle)
        with self.assertRaises(DataError):
            TaskJournal(other, result['task_id']).latest()
        def forbidden(*args):
            self.fail('Invalid recovery must fail before constructing Runtime')
        with self.assertRaises(DataError):
            await TaskManager(other, self.config, runtime_factory=forbidden).resume(result['task_id'])
        self.assertEqual(git(other.root, 'for-each-ref', 'refs/heads/canon/'), b'')

    async def test_foreign_world_input_and_foreign_factory_are_rejected(self):
        target = self.base / 'different-world'
        create_world(target, 'different', engine=self.world.engine, host_root=self.world.host_root)
        other = WorldWorkspace(target, self.world.engine, host_root=self.world.host_root)
        data = read_json(EXAMPLES / 'agents/researcher-input.json')
        with self.assertRaises(DataError):
            ToolSession(other, data)
        adapter = FakeAdapter(read_json(EXAMPLES / 'research_result.json'))
        with self.assertRaises(DataError):
            await AgentRuntime(other, adapter).run_input(data)
        self.assertEqual(adapter.count, 0)
        # Matching provider/model must not let a factory redirect output to a
        # different world's storage before invoking its adapter.
        from axiom_forge.modes import ModeRunner
        foreign_dir = self.base / 'foreign-fixture'
        foreign_dir.mkdir()
        fixture = initialize_fixture(foreign_dir).world
        foreign = WorldWorkspace(fixture.root, self.world.engine, host_root=self.world.host_root)
        self.assertEqual(foreign.world_id, self.world.world_id)
        calls = []
        def foreign_factory(mid, profile):
            calls.append(mid)
            adapter.provider, adapter.model = profile['provider'], profile['model']
            return AgentRuntime(foreign, adapter)
        receipt = await ModeRunner(self.world, self.config, runtime_factory=foreign_factory).run(
            read_json(EXAMPLES / 'task_state.json'))
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(len(calls), 1)
        self.assertEqual(adapter.count, 0)
        self.assertFalse((foreign.root / '.axiom/local/runtime-runs').exists())

    async def test_git_diff_does_not_bypass_fixed_snapshot_entity_scope(self):
        data = read_json(EXAMPLES / 'agents/researcher-input.json')
        session = ToolSession(self.world, data, capabilities=['git_read'])
        receipt = session.call('git.inspect', {'action': 'diff', 'path': 'world/canon/technology/TECH-003.json'})
        self.assertEqual(receipt['status'], 'denied')
        self.assertEqual(receipt['error']['code'], 'denied')
