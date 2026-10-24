"""Host Task Manager with explicit recovery and append-only audit checkpoints."""

import asyncio
import copy
from pathlib import Path

from . import __version__
from .workspaces import require_world
from .ids import new_id
from .journal import LIFECYCLES, TaskJournal, load, publish, source_fingerprint
from .modes import MODES, ModeRunner
from .recovery import Recovery
from .snapshots import build_snapshot, utc_now, verify_snapshot
from .tools.storage import Workspace, read_bounded
from .validation import DataError, digest, validate_task


RESULT_FIELDS = {'research': 'research_results', 'engineering': 'engineering_results',
                 'economic': 'economic_results', 'historical': 'historical_results', 'redteam': 'redteam_results'}
STAGES = {'planning': 'PLANNING', 'independent': 'RESEARCHING', 'cross_review': 'ANALYZING',
          'draft_synthesis': 'ANALYZING', 'redteam': 'REDTEAM', 'final_synthesis': 'SYNTHESIS'}


class TaskManager:
    def __init__(self, repo, config, *, runtime_factory):
        self.world = require_world(repo)
        self.repo = self.world.root
        self.engine_root = self.world.engine.root
        self.runner = ModeRunner(self.world, config, runtime_factory=runtime_factory)
        self.schemas = self.runner.store.schemas

    async def run(self, question, mode, relevant_entities=()):
        from .canon_host import CanonHost
        if not isinstance(question, str) or not question.strip() or mode not in MODES:
            raise DataError('A nonempty question and known mode are required')
        host = CanonHost(self.world)
        base = host.head()
        snapshot = build_snapshot(host.live_world(), self.schemas)
        host.check_base(base, snapshot)
        task = {'schema_version': '1.0', 'world_id': snapshot['world_id'], 'task_id': new_id('task'),
                'user_question': question, 'task_type': mode, 'lifecycle': 'CREATED',
                'canon_version': snapshot['canon_version'], 'canon_snapshot': snapshot,
                'relevant_entities': list(relevant_entities), 'synthesis': None,
                'proposed_changes': [], 'approval_status': 'not_requested', 'final_result': None,
                'runs': [], 'agent_runs': [], 'artifacts': [], 'contradictions': [],
                'metadata': {'task_manager': '2.0', 'workspace_binding': self.world.binding, 'system_version': __version__, 'base_git_sha': base,
                             'host_config_sha256': self.runner.config_sha256}}
        for field in RESULT_FIELDS.values(): task[field] = []
        validate_task(task, self.schemas)
        journal = TaskJournal(self.world, task['task_id'])
        with journal.lock():
            journal.workspace.write_json('created.json', task)
            control = {'run_id': new_id('run'), 'run_started_at': utc_now(),
                       'host_config_sha256': self.runner.config_sha256, 'policy_sha256': self.runner.router.sha256,
                       'source_sha256': source_fingerprint(self.engine_root), 'system_version': __version__, 'attempts': []}
            journal.append(task, control, 'running', [('TaskCreated', {'initial_task_sha256': digest(task)})])
            return await self._execute(task, copy.deepcopy(task), control, journal)

    async def resume(self, task_id):
        journal = TaskJournal(self.world, task_id)
        with journal.lock():
            latest = journal.latest()
            initial = load(journal.workspace.path('created.json'))
            if initial != journal.read()[0]['task_state']: raise DataError('Original task differs from its first checkpoint')
            Recovery(self.runner, initial, latest['control'])
            verify_state_artifacts(self.world, latest['task_state'])
            if latest['status'] not in ('running', 'interrupted'): return settled(self.world, latest)
            journal.append(latest['task_state'], latest['control'], 'running',
                           [('TaskResumed', {'retry_unfinished': True, 'reuse_completed': True})])
            return await self._execute(initial, copy.deepcopy(latest['task_state']), copy.deepcopy(latest['control']), journal)

    async def _execute(self, initial, task, control, journal):
        workspace, snapshot = journal.workspace, initial['canon_snapshot']
        recovery = Recovery(self.runner, initial, control)
        run = task['runs'][0] if task['runs'] else None
        if run: run.update(status='running', finished_at=None)

        def checkpoint(events, status='running'): return journal.append(task, control, status, events)

        def observe(event, payload):
            nonlocal run
            if event == 'started':
                if run is None:
                    run = {**{k: task[k] for k in ('world_id', 'task_id', 'canon_version')},
                           'run_id': payload['run_id'], 'status': 'running', 'started_at': payload['started_at'],
                           'finished_at': None, 'agent_run_ids': [], 'artifact_ids': [], 'metadata': {}}
                    task['runs'].append(run)
                    checkpoint([('RunStarted', {'run_id': run['run_id']})])
            elif event == 'invocation':
                lifecycle = STAGES[payload['stage']]
                if LIFECYCLES.index(lifecycle) > LIFECYCLES.index(task['lifecycle']):
                    task['lifecycle'] = lifecycle
                    events = [('LifecycleChanged', {'lifecycle': lifecycle})]
                    if lifecycle == 'RESEARCHING': events.append(('ResearchStarted', {'canon_version': task['canon_version']}))
                    checkpoint(events)
            elif event == 'reserved':
                if source_fingerprint(self.engine_root) != control['source_sha256']:
                    raise DataError('Task instructions/schemas changed before invocation')
                data = payload['input']
                path = workspace.write_json('inputs/' + data['agent_run_id'] + '.json', data)
                control['attempts'].append({'role': data['role'], 'stage': data['stage'], 'agent_run_id': data['agent_run_id'],
                    'input_path': path.relative_to(self.repo).as_posix(), 'input_sha256': digest(data),
                    'route': payload['route'], 'amount_usd': payload['amount_usd'], 'status': 'reserved',
                    'packet_path': None, 'packet_sha256': None})
                checkpoint([('AgentRunReserved', {'agent_run_id': data['agent_run_id'], 'role': data['role'],
                              'stage': data['stage'], 'amount_usd': payload['amount_usd']})])
            elif event == 'retrieval':
                dataset = verify_snapshot(snapshot, self.schemas)
                selected = set(task['relevant_entities'])
                for item in payload['assignments'].values(): selected.update(item['entity_ids'])
                pending = list(selected)
                while pending:
                    item = dataset['entities'][pending.pop()]
                    for target in item['dependencies'] + item['conflicts']:
                        if target not in selected: selected.add(target); pending.append(target)
                evidence = {eid for entity in selected for eid in dataset['entities'][entity]['evidence_ids']}
                evidence.update(eid for eid, record in dataset['evidence'].items()
                                if selected.intersection(record['supported_entities']))
                retrieval = {'canon_version': task['canon_version'], 'assignments': payload['assignments'],
                    'records': [r for r in snapshot['files'] if r['data'].get('entity_id') in selected
                                or r['data'].get('evidence_id') in evidence], 'source': 'fixed_snapshot_only'}
                path = publish(workspace, 'canon-retrieval.json', retrieval)
                if not any(a['kind'] == 'canon_retrieval' for a in task['artifacts']):
                    artifact = {**{k: task[k] for k in ('world_id', 'task_id')}, 'run_id': run['run_id'],
                        'artifact_id': new_id('artifact'), 'agent_run_id': None, 'kind': 'canon_retrieval',
                        'path': path.relative_to(self.repo).as_posix(), 'sha256': digest(retrieval),
                        'created_at': utc_now(), 'metadata': {'canon_version': task['canon_version']}}
                    task['artifacts'].append(artifact)
                    run['artifact_ids'].append(artifact['artifact_id'])
                    checkpoint([('ArtifactRecovered', {'artifact_id': artifact['artifact_id'], 'kind': 'canon_retrieval'})])
            elif event in ('packet', 'reused_packet'):
                agent = payload['agent_run']
                attempt = next(a for a in control['attempts'] if a['agent_run_id'] == agent['agent_run_id'])
                if event == 'reused_packet' and attempt['status'] == 'completed': return
                attempt.update(status=agent['status'], packet_path=f".axiom/local/runtime-runs/{agent['agent_run_id']}/completion.json",
                               packet_sha256=digest(payload))
                if agent['status'] != 'completed':
                    run['metadata']['failed_agent_run_id'] = agent['agent_run_id']
                    checkpoint([('AgentRunFailed', {'agent_run_id': agent['agent_run_id'], 'status': agent['status']})])
                    return
                task['agent_runs'].append(agent)
                run['agent_run_ids'].append(agent['agent_run_id'])
                artifacts = [payload['artifact'], *payload['tool_artifacts'], *payload['calculation_request_artifacts']]
                task['artifacts'].extend(artifacts)
                run['artifact_ids'].extend(a['artifact_id'] for a in artifacts)
                result = payload['result']
                events = [('AgentRunCompleted', {'agent_run_id': agent['agent_run_id'], 'artifact_id': agent['artifact_id']})]
                if event == 'reused_packet': events.append(('ArtifactRecovered', {'agent_run_id': agent['agent_run_id']}))
                if result['result_type'] in RESULT_FIELDS:
                    existing = {e['evidence_id'] for r in task['research_results'] for e in r['evidence']}
                    task[RESULT_FIELDS[result['result_type']]].append(result)
                    for evidence in result.get('evidence', []):
                        if evidence['evidence_id'] not in existing:
                            events.append(('EvidenceAdded', {'evidence_id': evidence['evidence_id'],
                                          'sha256': digest(evidence), 'provisional': True}))
                elif payload['stage'] in ('draft_synthesis', 'final_synthesis'):
                    task['synthesis'] = result
                    task['proposed_changes'] = copy.deepcopy(result['proposed_changes'])
                    task['contradictions'] = copy.deepcopy(result['contradictions'])
                if result['result_type'] == 'redteam':
                    for conflict in result['contradictions']: events.append(('RedTeamRaisedConflict', {'conflict': conflict}))
                checkpoint(events)

        receipt = await self.runner.run(initial, observer=observe, use_plan=True, recovery=recovery)
        run['status'] = 'completed' if receipt['status'] == 'completed' else (
            'cancelled' if receipt['status'] == 'cancelled' else 'failed')
        run['finished_at'] = utc_now()
        if receipt['status'] != 'completed':
            publish(workspace, 'failures/' + new_id('artifact') + '.json', {
                'status': receipt['status'], 'reason': receipt['reason'], 'run_id': run['run_id'], 'automatic_resume': False})
            checkpoint([('TaskInterrupted', {'status': receipt['status'], 'reason': receipt['reason']})], 'interrupted')
            return {'status': receipt['status'], 'reason': receipt['reason'], 'task_id': task['task_id'],
                    'run_id': run['run_id'], 'state_path': str(workspace.path('created.json')),
                    'checkpoint_path': str(journal.records.path(f"{journal.latest()['sequence']:08d}.json")),
                    'reserved_cost_usd': receipt['reserved_cost_usd']}
        task['approval_status'] = 'pending' if task['proposed_changes'] else 'not_requested'
        task['lifecycle'] = 'WAITING_APPROVAL' if task['proposed_changes'] else 'SYNTHESIS'
        if not task['proposed_changes']: task['final_result'] = task['synthesis']['summary']
        name = 'waiting.json' if task['proposed_changes'] else 'completed.json'
        if workspace.path(name).exists(): run['finished_at'] = load(workspace.path(name))['runs'][0]['finished_at']
        validate_task(task, self.schemas)
        path = publish(workspace, name, task)
        events = [('TaskCompleted', {'state_path': path.relative_to(self.repo).as_posix()})]
        if task['proposed_changes']:
            events.append(('CanonChangeProposed', {'proposal_hashes': {c['proposal_id']: digest(c) for c in task['proposed_changes']}}))
            events.append(('LifecycleChanged', {'lifecycle': 'WAITING_APPROVAL'}))
        latest = checkpoint(events, 'waiting_approval' if task['proposed_changes'] else 'completed')
        result = settled(self.world, latest)
        result['reserved_cost_usd'] = receipt['reserved_cost_usd']
        return result


def verify_state_artifacts(repo, task):
    world = require_world(repo)
    world.validate_world(task["world_id"])
    world.validate_binding(task["metadata"].get("workspace_binding"))
    from .tools.storage import safe_relative
    for artifact in task['artifacts']:
        if digest(load(world.root / safe_relative(artifact['path']))) != artifact['sha256']:
            raise DataError('Checkpoint artifact content changed')


def settled(repo, latest):
    world = require_world(repo)
    from .canon_host import CanonHost
    task, status = latest['task_state'], latest['status']
    name = 'waiting.json' if status in ('waiting_approval', 'approved', 'applying') else status + '.json'
    workspace = Workspace(world.root / '.axiom/local/tasks' / task['task_id'])
    path = publish(workspace, name, task)
    review = CanonHost(repo).prepare(path) if status == 'waiting_approval' else None
    return {'status': status, 'task_id': task['task_id'], 'run_id': latest['control']['run_id'],
            'state_path': str(path), 'review': review,
            **({'next_action': 'canon recover --bundle <review bundle>'} if status in ('approved', 'applying') else {})}


load_document = load


def run_cli(args):
    from .runtimes.cli import credentials, runtime_from_config
    if args.task_action in ('inspect', 'events'):
        journal = TaskJournal(args.workspace, args.task_id)
        return journal.latest() if args.task_action == 'inspect' else {'events': journal.events()}
    if args.task_action == 'resume':
        journal = TaskJournal(args.workspace, args.task_id)
        with journal.lock():
            latest = journal.latest()
            verify_state_artifacts(args.workspace, latest['task_state'])
            if latest['status'] not in ('running', 'interrupted'): return settled(args.workspace, latest)
    if not args.allow_live: raise DataError('Task research requires explicit --allow-live; offline demo is separate')
    if args.config is None: raise DataError('Research resume requires the original --config')
    manager = TaskManager(args.workspace, load(args.workspace.host_file(args.config)),
        runtime_factory=lambda mid, profile: runtime_from_config(args.workspace, profile, credentials(args.workspace.host_file(args.credentials))))
    if args.task_action == 'resume': return asyncio.run(manager.resume(args.task_id))
    question = read_bounded(args.question_file, limit=65536).decode('utf-8')
    return asyncio.run(manager.run(question, args.mode, args.entity))
