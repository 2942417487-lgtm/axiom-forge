"""Host-only atomic checkpoint/event batches and process-scoped task locks."""

import copy
import hashlib
import os
import re
from contextlib import contextmanager
from pathlib import Path

from . import __version__
from .workspaces import require_world
from .ids import new_id
from .snapshots import utc_now
from .tools.storage import Workspace, read_bounded, strict_json
from .validation import DataError, SchemaStore, digest, validate_task


LIFECYCLES = ("CREATED", "PLANNING", "RESEARCHING", "ANALYZING", "REDTEAM", "SYNTHESIS", "WAITING_APPROVAL", "COMMITTED")
TERMINAL = {"completed", "rejected", "committed"}


def load(path):
    data = strict_json(read_bounded(path))
    if not isinstance(data, dict): raise DataError("Expected a journal object")
    return data


def publish(workspace, name, value):
    """Crash reconciliation may reuse an identical file, never overwrite it."""
    if workspace.path(name).exists():
        if load(workspace.path(name)) != value: raise DataError("Existing artifact differs from recovered content")
        return workspace.path(name)
    return workspace.write_json(name, value)


class TaskJournal:
    def __init__(self, repo, task_id):
        if not re.fullmatch(r"TSK-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", task_id):
            raise DataError("Invalid task ID")
        self.world = require_world(repo)
        self.repo = self.world.root
        self.task_id = task_id
        self.workspace = Workspace(self.repo / ".axiom/local/tasks" / task_id)
        self.records = Workspace(self.workspace.root / "journal")
        self.schemas = self.world.schemas
        self.locked = False
        self._cache = None
        self._verified_files = []
        self._verified_records = []

    @contextmanager
    def lock(self):
        if self.locked: raise DataError("Task journal lock is not reentrant")
        path = self.workspace.path("operator.lock")
        if not path.exists():
            try: self.workspace.write("operator.lock", b"0")
            except DataError:
                if not path.exists(): raise
        read_bounded(path, limit=1)
        with path.open("r+b") as stream:
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise DataError("Task is already running/recovering in another process") from exc
            self.locked = True
            self._cache = None
            try: yield self
            finally:
                self.locked = False
                self._cache = None
                stream.seek(0)
                if os.name == "nt": msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def read(self):
        if self.locked and self._cache is not None: return copy.deepcopy(self._cache)
        records, previous, event_ids = [], None, set()
        files = []
        for number, path in enumerate(sorted(self.records.root.glob('*.json')), 1):
            if path.name != f"{number:08d}.json": raise DataError("Checkpoint sequence has a gap or invalid filename")
            raw = read_bounded(path)
            files.append((path.name, hashlib.sha256(raw).hexdigest(), raw))
        # Re-read and hash every file; reuse semantic validation only for an
        # identical, already verified prefix. Never trust mtime/size alone.
        prefix = 0
        while prefix < min(len(files), len(self._verified_files)):
            if files[prefix][:2] != self._verified_files[prefix]: break
            prefix += 1
        if len(files) < len(self._verified_files) and prefix == len(files):
            raise DataError('Previously observed checkpoints disappeared')
        records = copy.deepcopy(self._verified_records[:prefix])
        if records:
            previous = digest(records[-1])
            event_ids = {e['event_id'] for r in records for e in r['events']}
        for number, (_, _, raw) in enumerate(files[prefix:], prefix + 1):
            record = strict_json(raw)
            self.schemas.validate("task_checkpoint", record)
            if (record["sequence"] != number or record["previous_sha256"] != previous
                    or record["task_state"]["task_id"] != self.task_id):
                raise DataError("Checkpoint sequence/context/hash chain differs")
            validate_task(record["task_state"], self.schemas)
            self._context(record)
            if records:
                self._transition(records[-1], record)
                for key in ("world_id", "task_id", "canon_version", "canon_snapshot", "user_question", "task_type", 'relevant_entities', 'metadata'):
                    if record["task_state"][key] != records[0]["task_state"][key]:
                        raise DataError("Task checkpoint changed fixed input/snapshot")
            if record["state_sha256"] != digest(record["task_state"]): raise DataError("Checkpoint state hash differs")
            for event in record["events"]:
                if (event["event_id"] in event_ids or event["task_id"] != self.task_id
                        or event["world_id"] != record["task_state"]["world_id"]
                        or event["checkpoint_id"] != record["checkpoint_id"]):
                    raise DataError("Event identity differs from its checkpoint")
                event_ids.add(event["event_id"])
            previous = digest(record)
            records.append(record)
        self._verified_files = [entry[:2] for entry in files]
        self._verified_records = copy.deepcopy(records)
        if self.locked: self._cache = copy.deepcopy(records)
        return records

    def latest(self):
        records = self.read()
        if not records: raise DataError("No Phase 11 checkpoint exists for this task")
        return records[-1]

    def _transition(self, before, after):
        for key in ('run_id', 'run_started_at', 'host_config_sha256', 'policy_sha256', 'source_sha256', 'system_version'):
            if before['control'][key] != after['control'][key]: raise DataError('Frozen host control changed')
        old_attempts, new_attempts = before['control']['attempts'], after['control']['attempts']
        if len(new_attempts) < len(old_attempts): raise DataError('Budget reservations cannot be removed')
        for old, new in zip(old_attempts, new_attempts):
            immutable = set(old) - {'status', 'packet_path', 'packet_sha256'}
            if any(old[k] != new[k] for k in immutable): raise DataError('Reserved input/route/amount changed')
            if old['status'] != 'reserved' and old != new: raise DataError('Sealed invocation changed')
        if before["status"] in TERMINAL:
            if before["status"] != after["status"] or before["task_state"] != after["task_state"]:
                raise DataError("Terminal task cannot resume or change its scientific state")
        old, new = before["task_state"]["lifecycle"], after["task_state"]["lifecycle"]
        if LIFECYCLES.index(new) < LIFECYCLES.index(old) and after["status"] != "rejected":
            raise DataError("Lifecycle cannot move backwards")

    def _context(self, record):
        task, control = record['task_state'], record['control']
        self.world.validate_world(task['world_id'])
        self.world.validate_binding(task['metadata'].get('workspace_binding'))
        if record['schema_version'] != '1.1' or control.get('system_version') != __version__:
            raise DataError('Legacy or incompatible execution records require explicit migration')
        if task['metadata'].get('host_config_sha256') != control['host_config_sha256']:
            raise DataError('Task and checkpoint host config differ')
        if task['runs'] and (len(task['runs']) != 1 or task['runs'][0]['run_id'] != control['run_id']
                            or task['runs'][0]['started_at'] != control['run_started_at']):
            raise DataError('Task and checkpoint Run differ')
        attempts = {a['agent_run_id']: a for a in control['attempts']}
        if len(attempts) != len(control['attempts']): raise DataError('Duplicate reserved AgentRun')
        completed = {a['agent_run_id'] for a in control['attempts'] if a['status'] == 'completed'}
        if completed != {a['agent_run_id'] for a in task['agent_runs']}:
            raise DataError('Checkpoint completed invocations differ from TaskState')
        for agent in task['agent_runs']:
            attempt = attempts[agent['agent_run_id']]
            if (attempt['input_sha256'] != agent['metadata'].get('input_sha256')
                    or (attempt['role'], attempt['stage']) != (agent['role'], agent['metadata'].get('stage'))
                    or attempt['packet_sha256'] is None or attempt['packet_path'] is None):
                raise DataError('Checkpoint completion/input binding differs')

    def append(self, task, control, status, events):
        if not self.locked: raise DataError("Checkpoint writes require the operator process lock")
        prior = self.read()
        record = {"schema_version": "1.1", "checkpoint_id": new_id("checkpoint"), "sequence": len(prior) + 1,
            "previous_sha256": digest(prior[-1]) if prior else None, "created_at": utc_now(),
            "task_state": copy.deepcopy(task), "state_sha256": digest(task), "control": copy.deepcopy(control),
            "status": status, "events": []}
        for kind, data in events:
            record["events"].append({"schema_version": "1.0", "event_id": new_id("event"),
                "checkpoint_id": record["checkpoint_id"], "world_id": task["world_id"], "task_id": self.task_id,
                "run_id": control.get("run_id"), "event_type": kind, "occurred_at": record["created_at"], "data": copy.deepcopy(data)})
        self.schemas.validate("task_checkpoint", record)
        validate_task(task, self.schemas)
        self._context(record)
        if prior: self._transition(prior[-1], record)
        self.records.write_json(f"{record['sequence']:08d}.json", record)
        self._cache = [*prior, copy.deepcopy(record)]
        return record

    def events(self):
        return [event for checkpoint in self.read() for event in checkpoint["events"]]


def source_fingerprint(repo):
    """Freeze instruction, schema and routing files actually used by research."""
    repo = Path(repo)
    paths = {repo / "AGENTS.md", repo / "agents/README.md", repo / "tools/python-scripts/manifest.json"}
    for directory, pattern in (("schemas", "*.schema.json"), ("agents", "*.md"),
            ("agents/contracts", "*.json"), ("routing", "*.yaml"), ("modes", "*.md")):
        paths.update((repo / directory).glob(pattern))
    import hashlib
    return digest({"system_version": __version__, "resources": {p.relative_to(repo).as_posix(): hashlib.sha256(read_bounded(p)).hexdigest() for p in sorted(paths)}})
