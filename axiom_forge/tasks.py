"""Small host Task Manager. No automatic approval, retries or recovery."""

import asyncio
import copy
from pathlib import Path

from .ids import new_id
from .modes import MODES, ModeRunner
from .snapshots import build_snapshot, utc_now, verify_snapshot
from .tools.storage import Workspace, read_bounded, strict_json
from .validation import DataError, digest, validate_task


RESULT_FIELDS = {"research": "research_results", "engineering": "engineering_results",
                 "economic": "economic_results", "historical": "historical_results",
                 "redteam": "redteam_results"}


class TaskManager:
    def __init__(self, repo, config, *, runtime_factory):
        self.repo = Path(repo).absolute()
        self.runner = ModeRunner(self.repo, config, runtime_factory=runtime_factory)
        self.schemas = self.runner.store.schemas

    async def run(self, question, mode, relevant_entities=()):
        from .canon_host import CanonHost
        if not isinstance(question, str) or not question.strip() or mode not in MODES:
            raise DataError("A nonempty question and known mode are required")
        host = CanonHost(self.repo)
        base = host.head()
        snapshot = build_snapshot(host.live_world(), self.schemas)
        host.check_base(base, snapshot)
        task = {"schema_version": "1.0", "world_id": snapshot["world_id"], "task_id": new_id("task"),
                "user_question": question, "task_type": mode, "lifecycle": "CREATED",
                "canon_version": snapshot["canon_version"], "canon_snapshot": snapshot,
                "relevant_entities": list(relevant_entities), "synthesis": None,
                "proposed_changes": [], "approval_status": "not_requested", "final_result": None,
                "runs": [], "agent_runs": [], "artifacts": [], "contradictions": [],
                "metadata": {"task_manager": "1.0", "base_git_sha": base,
                             "host_config_sha256": self.runner.config_sha256}}
        for field in RESULT_FIELDS.values(): task[field] = []
        validate_task(task, self.schemas)
        workspace = Workspace(self.repo / ".cache/tasks" / task["task_id"])
        workspace.write_json("created.json", task)
        initial = copy.deepcopy(task)
        run = None

        def observe(event, payload):
            nonlocal run
            if event == "started":
                run = {**{k: task[k] for k in ("world_id", "task_id", "canon_version")},
                       "run_id": payload["run_id"], "status": "running", "started_at": utc_now(),
                       "finished_at": None, "agent_run_ids": [], "artifact_ids": [], "metadata": {}}
                task["runs"].append(run)
            elif event == "invocation":
                task["lifecycle"] = {"planning": "PLANNING", "independent": "RESEARCHING",
                    "cross_review": "ANALYZING", "draft_synthesis": "SYNTHESIS",
                    "redteam": "REDTEAM", "final_synthesis": "SYNTHESIS"}[payload["stage"]]
            elif event == "retrieval":
                dataset = verify_snapshot(snapshot, self.schemas)
                # Retrieve the plan's entities, dependency/conflict closure and attached
                # Evidence from the same snapshot. No live Canon or peer answers.
                selected = set(task["relevant_entities"])
                for item in payload["assignments"].values(): selected.update(item["entity_ids"])
                pending = list(selected)
                while pending:
                    item = dataset["entities"][pending.pop()]
                    for target in item["dependencies"] + item["conflicts"]:
                        if target not in selected: selected.add(target); pending.append(target)
                evidence = {eid for entity in selected for eid in dataset["entities"][entity]["evidence_ids"]}
                evidence.update(eid for eid, record in dataset["evidence"].items()
                                if selected.intersection(record["supported_entities"]))
                records = [r for r in snapshot["files"] if r["data"].get("entity_id") in selected
                           or r["data"].get("evidence_id") in evidence]
                retrieval = {"canon_version": task["canon_version"], "assignments": payload["assignments"],
                             "records": records, "source": "fixed_snapshot_only"}
                path = workspace.write_json("canon-retrieval.json", retrieval)
                artifact = {**{k: task[k] for k in ("world_id", "task_id")}, "run_id": run["run_id"],
                    "artifact_id": new_id("artifact"), "agent_run_id": None, "kind": "canon_retrieval",
                    "path": path.relative_to(self.repo).as_posix(), "sha256": digest(retrieval),
                    "created_at": utc_now(), "metadata": {"canon_version": task["canon_version"]}}
                task["artifacts"].append(artifact)
                run["artifact_ids"].append(artifact["artifact_id"])
            elif event == "packet":
                if payload["agent_run"]["status"] != "completed":
                    # A failed Runtime has no output Artifact; keep its real receipt
                    # outside TaskState rather than inventing a completed output.
                    run["metadata"]["failed_agent_run_id"] = payload["agent_run"]["agent_run_id"]
                    return
                agent = payload["agent_run"]
                task["agent_runs"].append(agent)
                run["agent_run_ids"].append(agent["agent_run_id"])
                artifacts = [payload["artifact"], *payload["tool_artifacts"], *payload["calculation_request_artifacts"]]
                task["artifacts"].extend(artifacts)
                run["artifact_ids"].extend(a["artifact_id"] for a in artifacts)
                result = payload["result"]
                if result["result_type"] in RESULT_FIELDS:
                    task[RESULT_FIELDS[result["result_type"]]].append(result)
                elif payload["stage"] == "final_synthesis":
                    task["synthesis"] = result
                    task["proposed_changes"] = copy.deepcopy(result["proposed_changes"])
                    task["contradictions"] = copy.deepcopy(result["contradictions"])

        receipt = await self.runner.run(initial, observer=observe, use_plan=True)
        run["status"] = "completed" if receipt["status"] == "completed" else (
            "cancelled" if receipt["status"] == "cancelled" else "failed")
        run["finished_at"] = utc_now()
        if receipt["status"] != "completed":
            workspace.write_json("failed.json", {"status": receipt["status"], "reason": receipt["reason"],
                "run_id": receipt["run_id"], "initial_task_sha256": digest(initial), "automatic_resume": False})
            return {"status": receipt["status"], "reason": receipt["reason"], "task_id": task["task_id"],
                    "run_id": run["run_id"], "state_path": str(workspace.path("created.json"))}
        task["approval_status"] = "pending" if task["proposed_changes"] else "not_requested"
        task["lifecycle"] = "WAITING_APPROVAL" if task["proposed_changes"] else "SYNTHESIS"
        if not task["proposed_changes"]: task["final_result"] = task["synthesis"]["summary"]
        validate_task(task, self.schemas)
        path = workspace.write_json("waiting.json" if task["proposed_changes"] else "completed.json", task)
        bundle = host.prepare(path) if task["proposed_changes"] else None
        return {"status": "waiting_approval" if bundle else "completed", "task_id": task["task_id"],
                "run_id": run["run_id"], "state_path": str(path), "review": bundle,
                "reserved_cost_usd": receipt["reserved_cost_usd"]}


def load_document(path):
    data = strict_json(read_bounded(Path(path)))
    if not isinstance(data, dict): raise DataError("Expected a JSON object")
    return data


def run_cli(args):
    from .runtimes.cli import credentials, runtime_from_config
    if not args.allow_live: raise DataError("Task research requires explicit --allow-live; offline demo is separate")
    config = load_document(args.config)
    manager = TaskManager(args.repo, config,
        runtime_factory=lambda mid, profile: runtime_from_config(args.repo, profile, keys))
    keys = credentials(args.credentials)
    question = read_bounded(args.question_file, limit=65536).decode("utf-8")
    return asyncio.run(manager.run(question, args.mode, args.entity))
