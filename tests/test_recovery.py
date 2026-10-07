"""Offline crash/recovery tests using real archives, process locks and Git refs."""

import copy
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from axiom_forge.__main__ import main
from axiom_forge.canon_host import document
from axiom_forge.journal import LIFECYCLES, TaskJournal
from axiom_forge.tasks import TaskManager
from axiom_forge.validation import DataError, digest, read_json
from examples.offline_task_manager import ROOT, fixture_factory, initialize_fixture
from examples.offline_task_manager import ProposalFixture


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        scratch = Path(tempfile.gettempdir()) / "axiom-forge-test-runs"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.repo = Path(self.temporary.name).absolute()
        self.host = initialize_fixture(self.repo)
        self.workspace = self.host.world
        self.repo = self.workspace.root
        self.engine = self.workspace.engine.root
        self.base = self.host.head()
        self.config = read_json(ROOT / 'examples/mode-host.json')
        self.config['max_cost_usd'] = 20

    def tearDown(self): self.temporary.cleanup()

    def manager(self, seen=None, **kwargs):
        return TaskManager(self.workspace, self.config, runtime_factory=fixture_factory(self.workspace, seen, **kwargs))

    def crash(self, boundary, count=3):
        result = subprocess.run([sys.executable, str(ROOT / 'examples/offline_recovery.py'),
                                 str(self.repo), boundary, str(count)], cwd=ROOT, capture_output=True, timeout=90)
        self.assertEqual(result.returncode, 75, result.stderr.decode(errors='replace'))
        task_id = next((self.repo / '.axiom/local/tasks').glob('TSK-*')).name
        return TaskJournal(self.workspace, task_id)

    async def test_real_process_exit_reuses_completed_roles_and_fixed_contexts(self):
        journal = self.crash('checkpoint')
        before = journal.latest()
        originals = copy.deepcopy(before['task_state']['agent_runs'])
        self.assertEqual(len(originals), 3)
        seen = []
        result = await self.manager(seen).resume(journal.task_id)
        self.assertEqual(result['status'], 'waiting_approval')
        after = journal.latest()
        self.assertEqual(after['task_state']['agent_runs'][:3], originals)
        self.assertEqual(len(seen), 9)
        self.assertEqual(after['control']['run_id'], before['control']['run_id'])
        self.assertEqual(len(after['control']['attempts']), 12)
        self.assertTrue(all(d['canon_snapshot'] == before['task_state']['canon_snapshot'] for d in seen))
        self.assertTrue(all(d['prior_results'] == [] and d['supporting_artifacts'] == []
                            for d in seen if d['stage'] == 'independent'))
        records = journal.read()
        order = [LIFECYCLES.index(r['task_state']['lifecycle']) for r in records]
        self.assertEqual(order, sorted(order))
        events = journal.events()
        self.assertEqual(sum(e['event_type'] == 'AgentRunCompleted' for e in events), 12)
        self.assertEqual(sum(e['event_type'] == 'TaskCreated' for e in events), 1)
        self.assertEqual(self.host.head(), self.base)

    async def test_archive_checkpoint_gap_adopts_result_without_another_call(self):
        journal = self.crash('archive_gap')
        before = journal.latest()
        arn = before['control']['attempts'][0]['agent_run_id']
        self.assertEqual(before['control']['attempts'][0]['status'], 'reserved')
        seen = []
        result = await self.manager(seen).resume(journal.task_id)
        self.assertEqual(result['status'], 'waiting_approval')
        self.assertEqual(len(seen), 11)
        self.assertNotIn('planning', [d['stage'] for d in seen])
        self.assertEqual(journal.latest()['task_state']['agent_runs'][0]['agent_run_id'], arn)
        self.assertTrue(any(e['event_type'] == 'ArtifactRecovered' and e['data'].get('agent_run_id') == arn
                            for e in journal.events()))

    async def test_unknown_call_gets_new_ids_and_retains_old_budget(self):
        journal = self.crash('unknown_call')
        old = journal.latest()['control']['attempts'][0]
        seen = []
        result = await self.manager(seen).resume(journal.task_id)
        self.assertEqual(result['status'], 'waiting_approval')
        attempts = journal.latest()['control']['attempts']
        self.assertEqual(len(attempts), 13)
        self.assertEqual(attempts[0], old)
        self.assertNotEqual(seen[0]['agent_run_id'], old['agent_run_id'])
        self.assertEqual(Decimal(result['reserved_cost_usd']), sum(Decimal(a['amount_usd']) for a in attempts))

    async def test_archived_tool_receipts_and_calculation_requests_reused(self):
        import json
        from axiom_forge.ids import new_id
        execute = ProposalFixture.execute
        async def with_receipt(adapter, instructions, prompt, schema, tools, limits):
            reply = await execute(adapter, instructions, prompt, schema, tools, limits)
            data = json.loads(prompt)['agent_input']
            if data['role'] == 'engineering_auditor' and data['stage'] == 'independent':
                receipt = json.loads(await tools.call('canon__read', {'entity_id': 'TECH-001'}))
                self.assertEqual(receipt['status'], 'completed')
                request = read_json(ROOT / 'examples/calculations/engineering_result-with-request.json')['calculation_requests'][0]
                request.update({k: data[k] for k in ('world_id', 'task_id', 'run_id', 'agent_run_id', 'canon_version', 'role')})
                request['request_id'] = new_id('artifact')
                reply.output['calculation_requests'] = [request]
            return reply
        with patch.object(ProposalFixture, 'execute', with_receipt):
            from axiom_forge.tools.session import ToolSession
            factory = fixture_factory(self.workspace, fail_stage='cross_review')
            def granted(mid, profile):
                runtime = factory(mid, profile)
                runtime.session_factory = lambda data: ToolSession(self.workspace, data,
                    capabilities=profile['tools']['capabilities'])
                return runtime
            manager = TaskManager(self.workspace, self.config, runtime_factory=granted)
            result = await manager.run('SYNTHETIC receipt recovery', 'court', ['TECH-001'])
        journal = TaskJournal(self.workspace, result['task_id'])
        artifacts = journal.latest()['task_state']['artifacts']
        receipt_ref = next(a for a in artifacts if a['kind'] == 'tool_result')
        request_ref = next(a for a in artifacts if a['kind'] == 'calculation_request')
        receipt_path = self.repo / receipt_ref['path']
        raw = receipt_path.read_bytes()
        receipt_path.write_bytes(b'{}\n')
        with self.assertRaises(DataError): await self.manager().resume(journal.task_id)
        receipt_path.write_bytes(raw)
        request_raw = (self.repo / request_ref['path']).read_bytes()
        seen = []
        resumed = await self.manager(seen).resume(journal.task_id)
        self.assertEqual(resumed['status'], 'waiting_approval')
        self.assertEqual(len(seen), 7)
        self.assertEqual(receipt_path.read_bytes(), raw)
        self.assertEqual((self.repo / request_ref['path']).read_bytes(), request_raw)
        self.assertIn(receipt_ref, journal.latest()['task_state']['artifacts'])
        self.assertIn(request_ref, journal.latest()['task_state']['artifacts'])

    async def test_failed_invocation_retry_does_not_rerun_lead(self):
        result = await self.manager(fail_stage='independent').run('SYNTHETIC failure', 'court', ['TECH-001'])
        journal = TaskJournal(self.workspace, result['task_id'])
        failed = journal.latest()['control']['attempts'][-1]
        lead = journal.latest()['task_state']['agent_runs'][0]
        seen = []
        resumed = await self.manager(seen).resume(result['task_id'])
        self.assertEqual(resumed['status'], 'waiting_approval')
        self.assertEqual(len(seen), 11)
        self.assertEqual(journal.latest()['task_state']['agent_runs'][0], lead)
        self.assertEqual(journal.latest()['control']['attempts'][1], failed)
        self.assertEqual(failed['status'], 'failed')

    async def test_config_source_and_artifact_tampering_fail_before_factory(self):
        journal = self.crash('checkpoint')
        calls = []
        def forbidden(*args): calls.append(args); raise AssertionError('Must not construct Runtime')
        changed = copy.deepcopy(self.config)
        changed['max_cost_usd'] += 1
        with self.assertRaises(DataError): await TaskManager(self.workspace, changed, runtime_factory=forbidden).resume(journal.task_id)
        source = self.engine / 'agents/researcher.md'
        original = source.read_bytes()
        source.write_bytes(original + b'\nchanged rules\n')
        with self.assertRaises(DataError): await TaskManager(self.workspace, self.config, runtime_factory=forbidden).resume(journal.task_id)
        source.write_bytes(original)
        artifact = self.repo / journal.latest()['task_state']['artifacts'][0]['path']
        artifact.write_bytes(b'{}\n')
        with self.assertRaises(DataError): await TaskManager(self.workspace, self.config, runtime_factory=forbidden).resume(journal.task_id)
        self.assertEqual(calls, [])

    async def test_rules_changed_during_execution_stop_before_next_runtime(self):
        source = self.engine / 'agents/researcher.md'
        original = source.read_bytes()
        execute = ProposalFixture.execute
        async def change_rules(adapter, *args, **kwargs):
            reply = await execute(adapter, *args, **kwargs)
            if reply.output['result_type'] == 'plan': source.write_bytes(original + b'\nchanged during task\n')
            return reply
        seen = []
        with patch.object(ProposalFixture, 'execute', change_rules):
            with self.assertRaises(DataError):
                await self.manager(seen).run('SYNTHETIC instruction change', 'court', ['TECH-001'])
        self.assertEqual([d['stage'] for d in seen], ['planning'])
        task_id = next((self.repo / '.axiom/local/tasks').glob('TSK-*')).name
        journal = TaskJournal(self.workspace, task_id)
        self.assertEqual(len(journal.latest()['control']['attempts']), 1)
        source.write_bytes(original)
        seen = []
        resumed = await self.manager(seen).resume(task_id)
        self.assertEqual(resumed['status'], 'waiting_approval')
        self.assertEqual(len(seen), 11)

    async def test_corrupt_chain_and_reserved_input_rejected(self):
        journal = self.crash('unknown_call')
        last = journal.latest()
        path = journal.records.path(f"{last['sequence']:08d}.json")
        original = path.read_bytes()
        path.write_text('{}', encoding='utf-8')
        with self.assertRaises(DataError): journal.latest()
        path.write_bytes(original)
        input_path = self.repo / last['control']['attempts'][0]['input_path']
        input_path.write_text('{}', encoding='utf-8')
        with self.assertRaises(DataError): await self.manager().resume(journal.task_id)

    async def test_budget_exhaustion_stops_before_retry_without_refunding_unknown(self):
        self.config['max_cost_usd'] = 0.60  # Research minimum tier 1: each call reserves 0.30.
        result = await self.manager(fail_stage='independent').run('SYNTHETIC bounded retry', 'court', ['TECH-001'])
        self.assertEqual(result['status'], 'failed')
        journal = TaskJournal(self.workspace, result['task_id'])
        before = journal.latest()['control']['attempts']
        seen = []
        resumed = await self.manager(seen).resume(journal.task_id)
        self.assertEqual(resumed['status'], 'OPEN_QUESTION')
        self.assertEqual(seen, [])
        self.assertEqual(journal.latest()['control']['attempts'], before)

    async def test_process_lock_and_terminal_resume_no_runtime(self):
        journal = self.crash('unknown_call')
        # A separate process must fail immediately while the operator owns the lock.
        code = 'import sys; from axiom_forge.journal import TaskJournal; from examples.offline_task_manager import fixture_binding; j=TaskJournal(fixture_binding(sys.argv[1]),sys.argv[2]);\nwith j.lock(): print("BAD")'
        with journal.lock():
            p = subprocess.run([sys.executable, '-c', code, str(self.repo), journal.task_id], cwd=ROOT,
                               capture_output=True, timeout=30)
            self.assertNotEqual(p.returncode, 0)
            self.assertNotIn(b'BAD', p.stdout)
        result = await self.manager().resume(journal.task_id)
        seen = []
        again = await self.manager(seen).resume(journal.task_id)
        self.assertEqual(again['review'], result['review'])
        self.assertEqual(seen, [])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--engine-root', str(self.engine), '--world', str(self.repo), '--host-root', str(self.workspace.host_root), 'tasks', 'inspect', '--task-id', journal.task_id]), 0)
            self.assertEqual(main(['--engine-root', str(self.engine), '--world', str(self.repo), '--host-root', str(self.workspace.host_root), 'tasks', 'events', '--task-id', journal.task_id]), 0)
            self.assertEqual(main(['--engine-root', str(self.engine), '--world', str(self.repo), '--host-root', str(self.workspace.host_root), 'tasks', 'resume', '--task-id', journal.task_id]), 0)

    async def research_and_approve(self):
        result = await self.manager(new_evidence=True).run('SYNTHETIC approval recovery', 'court', ['TECH-001'])
        self.host.init_key()
        review = result['review']
        self.host.decide(Path(review['bundle']), 'SYNTHETIC operator', review['sha256'])
        return result, Path(review['bundle']), TaskJournal(self.workspace, result['task_id'])

    async def test_approval_file_checkpoint_gap_reconciles_without_reapproval(self):
        result = await self.manager().run('SYNTHETIC approval crash', 'court', ['TECH-001'])
        self.host.init_key()
        bundle = Path(result['review']['bundle'])
        with patch.object(self.host, 'record_decision', side_effect=SystemExit(75)):
            with self.assertRaises(SystemExit): self.host.decide(bundle, 'SYNTHETIC operator', result['review']['sha256'])
        journal = TaskJournal(self.workspace, result['task_id'])
        self.assertEqual(journal.latest()['status'], 'waiting_approval')
        recovered = self.host.recover(bundle)
        self.assertEqual(recovered['status'], 'approved')
        self.assertEqual(journal.latest()['status'], 'approved')
        self.host.recover(bundle)
        self.assertEqual(sum(e['event_type'] == 'HumanApproved' for e in journal.events()), 1)
        self.assertEqual(self.host.head(), self.base)

    async def test_prepared_commit_before_ref_publication_recovers_exact_commit(self):
        _, bundle, journal = await self.research_and_approve()
        git = self.host.git
        def crash_ref(*args, **kwargs):
            if args[0] == 'update-ref': raise SystemExit(75)
            return git(*args, **kwargs)
        with patch.object(self.host, 'git', side_effect=crash_ref):
            with self.assertRaises(SystemExit): self.host.apply(bundle)
        self.assertEqual(journal.latest()['status'], 'applying')
        prepared = document(bundle.parent / 'commit-prepared.json')
        recovered = self.host.recover(bundle)
        self.assertEqual(recovered['commit_sha'], prepared['canon_commit']['commit_sha'])
        self.assertEqual(journal.latest()['status'], 'committed')
        self.host.recover(bundle)
        self.assertEqual(sum(e['event_type'] == 'CanonCommitted' for e in journal.events()), 1)
        self.assertTrue(any(e['event_type'] == 'EvidenceAdded' for e in journal.events()))
        self.assertEqual(self.host.head(), self.base)

    async def test_published_branch_missing_state_recovers_after_main_advances(self):
        _, bundle, journal = await self.research_and_approve()
        from axiom_forge.tools.storage import Workspace
        original = Workspace.write_json
        def crash_state(workspace, name, value):
            if name == 'committed.json': raise SystemExit(75)
            return original(workspace, name, value)
        with patch.object(Workspace, 'write_json', crash_state):
            with self.assertRaises(SystemExit): self.host.apply(bundle)
        self.host.git('commit', '--allow-empty', '-m', 'SYNTHETIC later main commit')
        head = self.host.head()
        recovered = self.host.recover(bundle)
        self.assertEqual(recovered['status'], 'committed')
        self.assertEqual(self.host.head(), head)
        self.assertEqual(journal.latest()['status'], 'committed')

    async def test_recovery_rejects_forged_approval_and_conflicting_branch(self):
        _, bundle, journal = await self.research_and_approve()
        git = self.host.git
        def crash_ref(*args, **kwargs):
            if args[0] == 'update-ref': raise SystemExit(75)
            return git(*args, **kwargs)
        with patch.object(self.host, 'git', side_effect=crash_ref):
            with self.assertRaises(SystemExit): self.host.apply(bundle)
        branch = document(bundle)['branch']
        self.host.git('branch', branch, self.base)
        with self.assertRaises(DataError): self.host.recover(bundle)
        self.assertEqual(self.host.git('rev-parse', 'refs/heads/' + branch).decode().strip(), self.base)
        approval = bundle.parent / 'approval.json'
        approval.write_text('{}', encoding='utf-8')
        with self.assertRaises(DataError): self.host.recover(bundle)
        self.assertEqual(journal.latest()['status'], 'applying')
