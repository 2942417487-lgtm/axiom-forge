"""SYNTHETIC Phase 10 demo in a temporary repository; no API or live world writes."""

import asyncio
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from axiom_forge.workspaces import EngineResources, WorldWorkspace, WORLD_IGNORE
from axiom_forge.git_host import git
from axiom_forge.canon_host import CanonHost
from axiom_forge.ids import new_id
from axiom_forge.runtimes.core import AgentRuntime, RuntimeLimits
from axiom_forge.tasks import TaskManager
from axiom_forge.tools.session import ToolSession
from axiom_forge.validation import KNOWLEDGE_DIRECTORIES, read_json
from examples.offline_modes import FixtureAdapter


class ProposalFixture(FixtureAdapter):
    """Deliberately fake analysis; only the contracts and host flow are tested."""
    def __init__(self, *args, proposals=True, operations=False, new_evidence=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.proposals, self.operations, self.new_evidence = proposals, operations, new_evidence
        self.evidence_id = new_id("evidence")

    async def execute(self, instructions, prompt, output_schema, tools, limits):
        reply = await super().execute(instructions, prompt, output_schema, tools, limits)
        data = json.loads(prompt)["agent_input"]
        if self.new_evidence and data["role"] == "researcher":
            evidence = read_json(ROOT / "examples/evidence.json")
            evidence["evidence_id"] = self.evidence_id
            reply.output["evidence"] = [evidence]
        if self.proposals and data["stage"] == "final_synthesis":
            changes = []
            operations = [("add", "TECH-002")]
            if self.operations: operations += [("update", "TECH-003"), ("delete", "TECH-004")]
            snapshot = {r["data"].get("entity_id"): r["data"] for r in data["canon_snapshot"]["files"]}
            for operation, target in operations:
                change = read_json(ROOT / "examples/canon_change.json")
                change.update({k: data[k] for k in ("world_id", "task_id", "run_id")})
                change.update(proposal_id=new_id("proposal"), base_canon_version=data["canon_version"],
                              operation=operation, target_entity_id=target, before=copy.deepcopy(snapshot.get(target)))
                if operation == "delete": change["after"] = None
                else:
                    change["after"]["entity_id"] = target
                    change["after"]["title"] = "SYNTHETIC offline proposal " + target
                changes.append(change)
            reply.output["proposed_changes"] = changes
        return reply


def fixture_factory(repo, seen=None, **kwargs):
    def create(mid, profile):
        return AgentRuntime(repo, ProposalFixture(profile["provider"], profile["model"], seen=seen, **kwargs),
            limits=RuntimeLimits(**profile.get("limits", {})), session_factory=lambda data: ToolSession(repo, data))
    return create


def fixture_binding(repo):
    repo = Path(repo).absolute()
    return WorldWorkspace(repo, EngineResources(repo.parent / "engine"), host_root=repo.parent / "host")


def initialize_fixture(directory):
    directory = Path(directory).absolute()
    repo, engine = directory / "world-repo", directory / "engine"
    repo.mkdir()
    engine.mkdir()
    for folder in ("schemas", "agents", "modes", "routing", ".claude", "tools", "templates"):
        shutil.copytree(ROOT / folder, engine / folder)
    shutil.copyfile(ROOT / "AGENTS.md", engine / "AGENTS.md")
    (repo / ".gitignore").write_text(WORLD_IGNORE, encoding="utf-8")
    for folder in KNOWLEDGE_DIRECTORIES:
        directory = repo / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").write_text("", encoding="utf-8")
    files = {r["path"]: r["data"] for r in read_json(ROOT / "examples/canon_snapshot.json")["files"]}
    for target in ("TECH-003", "TECH-004"):
        entry = copy.deepcopy(read_json(ROOT / "examples/canon_change.json")["after"])
        entry["entity_id"] = target
        files[f"world/canon/technology/{target}.json"] = entry
    for path, data in files.items():
        (repo / path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "SYNTHETIC test operator")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "add", "--", ".")
    git(repo, "commit", "-m", "SYNTHETIC fixture baseline")
    return CanonHost(fixture_binding(repo))


async def main():
    scratch = Path(tempfile.gettempdir()) / "axiom-forge-test-runs"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as temporary:
        repo = Path(temporary).absolute()
        host = initialize_fixture(repo)
        world = host.world
        config = read_json(ROOT / "examples/mode-host.json")
        config["max_cost_usd"] = 20  # Synthetic reservations only; this factory cannot call any API.
        manager = TaskManager(world, config, runtime_factory=fixture_factory(world, operations=True, new_evidence=True))
        head = host.head()
        result = await manager.run("SYNTHETIC contract/approval test; no scientific research", "court", ["TECH-001"])
        if result["status"] != "waiting_approval": raise RuntimeError(result)
        host.init_key()
        review = result["review"]
        host.decide(Path(review["bundle"]), "SYNTHETIC test operator", review["sha256"])
        commit = host.apply(Path(review["bundle"]))
        assert host.head() == head
        print(json.dumps({"test_fixture": True, "api_calls": 0, "temporary_repository": True,
            "status": commit["status"], "branch": commit["branch"], "main_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__": asyncio.run(main())
