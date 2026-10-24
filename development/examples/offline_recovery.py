"""SYNTHETIC subprocess crash harness; no credentials, SDK or live Canon."""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "product"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "development"))
from support import EXAMPLES_ROOT as EXAMPLES, LEGACY_ROOT

from axiom_forge.journal import TaskJournal
from axiom_forge.tasks import TaskManager
from axiom_forge.validation import read_json
from examples.offline_task_manager import fixture_factory, fixture_binding


async def crash(repo, boundary, count=3):
    """Only operates on an already initialized isolated fixture repository."""
    repo = Path(repo).absolute()
    scratch = Path(tempfile.gettempdir()) / "axiom-forge-test-runs"
    if not repo.resolve().is_relative_to(scratch.resolve()):
        raise ValueError('Crash harness requires an isolated test repository')
    config = read_json(EXAMPLES / 'mode-host.json')
    config['max_cost_usd'] = 20
    original, completed = TaskJournal.append, 0

    def append(journal, task, control, status, events):
        nonlocal completed
        kinds = {kind for kind, _ in events}
        if boundary == 'archive_gap' and 'AgentRunCompleted' in kinds:
            os._exit(75)  # Runtime archive exists; checkpoint still reserved.
        record = original(journal, task, control, status, events)
        if boundary == 'unknown_call' and 'AgentRunReserved' in kinds:
            os._exit(75)  # Reservation exists; no provider result is known.
        if 'AgentRunCompleted' in kinds:
            completed += 1
            if boundary == 'checkpoint' and completed == count: os._exit(75)
        return record

    TaskJournal.append = append
    world = fixture_binding(repo)
    manager = TaskManager(world, config, runtime_factory=fixture_factory(world))
    await manager.run('SYNTHETIC subprocess recovery task', 'court', ['TECH-001'])


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4): raise SystemExit('repo boundary [completed_count]')
    asyncio.run(crash(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) == 4 else 3))
