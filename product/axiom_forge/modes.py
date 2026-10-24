"""Bounded mode sessions on existing research Runtime; no TaskManager/Canon Apply."""

import asyncio
import copy
from decimal import Decimal
from pathlib import Path

from .workspaces import require_world
from .contracts import ContractStore, SPECIALISTS, project_input
from .ids import new_id
from .journal import publish
from .snapshots import utc_now
from .mode_validation import validate_mode_analysis
from .routing import ModelRouter
from .runtimes.cli import credentials, runtime_from_config, validate_host_config
from .runtimes.core import as_prior_result
from .tools.storage import Workspace
from .validation import DataError, canonical_bytes, digest, read_json, validate_task


MODES = ("scenario_simulation", "direct_challenge", "roundtable", "court")


class ModeRunner:
    def __init__(self, repo, config, *, runtime_factory, router=None):
        self.world = require_world(repo)
        self.repo = self.world.root
        self.engine_root = self.world.engine.root
        self.store = ContractStore(self.engine_root, self.world.schemas)
        self.router = router or ModelRouter(self.engine_root)
        self.store.schemas.validate("mode_host", config)
        canonical_bytes(config)
        self.config = copy.deepcopy(config)
        self.runtime_factory = runtime_factory
        for mid, profile in self.config["profiles"].items():
            model = self.router.model(mid)
            validate_host_config(profile)
            if profile["provider"] != model["runtime_provider"] or profile["model"] != model["model"]:
                raise DataError("Host Runtime profile differs from registered model/provider")
            if type(profile.get("max_cost_usd")) not in (int, float) or profile["max_cost_usd"] <= 0:
                raise DataError("Each mode Runtime requires a positive host allowance")
            canonical_bytes(profile)
        self.config_sha256 = digest(config)

    async def run(self, task, *, observer=None, use_plan=False, recovery=None):
        task = copy.deepcopy(task)
        validate_task(task, self.store.schemas)
        self.world.validate_world(task["world_id"])
        if task["task_type"] not in MODES:
            raise DataError("Unknown worldbuilding mode")
        # All four are deliberately selected; Lead provides an advisory plan but cannot
        # eliminate an audit domain, select models, grant tools or change the snapshot.
        selected = list(SPECIALISTS)
        run_id = recovery.control['run_id'] if recovery and recovery.control['run_id'] else new_id("run")
        started_at = recovery.control['run_started_at'] if recovery and recovery.control['run_started_at'] else utc_now()
        workspace = Workspace(self.repo / ".axiom/local/mode-runs" / run_id)
        publish(workspace, "started.json", {"run_id": run_id, "task_id": task["task_id"], "started_at": started_at,
            "mode": task["task_type"], "canon_version": task["canon_version"],
            "task_sha256": digest(task), "host_config_sha256": self.config_sha256,
            "policy_sha256": self.router.sha256, "workspace_binding": self.world.binding})
        packets, routes, reserved = [], [], recovery.reserved if recovery else Decimal(0)
        lead_family = None
        status, reason, result = "completed", None, None
        assignments = {}

        def observe(event, payload):
            if observer is not None:
                observer(event, copy.deepcopy(payload))

        observe("started", {"run_id": run_id, "started_at": started_at})

        def invocation(role, stage, prior, artifacts):
            data = project_input(task, {"run_id": run_id, "agent_run_id": new_id("agent_run"),
                "artifact_id": new_id("artifact")}, role, stage, selected, self.store.schemas,
                prior_results=prior, supporting_artifacts=artifacts)
            data["mode_protocol"] = "1.0"
            if role in assignments:
                data["planning_assignment"] = copy.deepcopy(assignments[role])
                data["relevant_entities"] = sorted(set(task["relevant_entities"]) | set(assignments[role]["entity_ids"]))
            self.store.validate_input(data)
            if recovery:
                cached = recovery.completed(role, stage)
                if cached:
                    for key in ('agent_run_id', 'artifact_id'): data[key] = cached['agent_run'][key]
                recovery.check_input(data)
            return data

        async def call(data):
            nonlocal reserved, lead_family
            observe("invocation", data)
            cached = recovery.completed(data['role'], data['stage']) if recovery else None
            if cached:
                route = recovery.attempt(data['role'], data['stage'])['route']
                routes.append(copy.deepcopy(route))
                packets.append(copy.deepcopy(cached))
                if data['role'] == 'lead': lead_family = self.router.model(route['model_id'])['family']
                observe('reused_packet', cached)
                return cached
            request = {**self.config["routing"], "role": data["role"],
                "task_kind": "scenario" if task["task_type"] == "scenario_simulation" else "research",
                # Host counts UTF-8 bytes conservatively, plus instructions/schema overhead.
                "context_size": len(canonical_bytes(data)) + 65536,
                "output_tokens": max(profile.get("limits", {}).get("max_output_tokens", 4096)
                                     for profile in self.config["profiles"].values()),
                "budget_usd": float(Decimal(str(self.config["max_cost_usd"])) - reserved)}
            if data["role"] == "integrator": request["task_kind"] = "synthesis"
            elif data["role"] == "redteam": request["task_kind"] = "review"
            excluded = set(self.router.models) - set(self.config["profiles"])
            for mid, profile in self.config["profiles"].items():
                if (not set(request["required_tools"]).issubset(profile.get("tools", {}).get("capabilities", []))
                        or Decimal(str(profile["max_cost_usd"])) > Decimal(str(request["budget_usd"]))):
                    excluded.add(mid)
            require_family = (lead_family if data["role"] == "redteam" and
                              (request["need_independent_review"] or request["importance"] >= self.router.policy["high_importance"])
                              else None)
            route = self.router.select(request, exclude=excluded, different_family=require_family)
            routes.append({"agent_run_id": data["agent_run_id"], "role": data["role"], "stage": data["stage"], **route})
            workspace.write_json("routes/" + data["agent_run_id"] + ".json", routes[-1])
            if route["model_id"] is None:
                return None
            mid = route["model_id"]
            profile = copy.deepcopy(self.config["profiles"][mid])
            reserved += Decimal(str(profile["max_cost_usd"]))  # No refund on failure/unknown usage.
            observe('reserved', {'input': data, 'route': routes[-1], 'amount_usd': format(Decimal(str(profile['max_cost_usd'])), 'f')})
            if data["role"] == "lead": lead_family = self.router.model(mid)["family"]
            runtime = self.runtime_factory(mid, profile)
            if runtime.adapter.provider != profile["provider"] or runtime.adapter.model != profile["model"] or runtime.repo != self.repo or runtime.engine_root != self.engine_root or runtime.world.binding != self.world.binding:
                raise DataError("Host factory returned a different Runtime/model")
            packet = await runtime.run_input(copy.deepcopy(data))
            packets.append(packet)
            observe("packet", packet)
            return packet

        def require(packet):
            if packet is None:
                raise ModeStop("OPEN_QUESTION", "No validated model satisfies mode capacity/family/budget constraints")
            if packet["agent_run"]["status"] != "completed":
                raise ModeStop("failed", "Role invocation failed; later stages were not run")
            return packet

        try:
            lead = require(await call(invocation("lead", "planning", [], [])))
            if use_plan:
                assignments = {item["role"]: item for item in lead["result"]["assignments"]}
                if set(assignments) != set(selected):
                    raise ModeStop("OPEN_QUESTION", "Task planning must assign all four audit domains")
                observe("retrieval", {"run_id": run_id, "assignments": assignments})
            # Prepare all first inputs before any first answer exists; no packet side channel.
            first_inputs = [invocation(role, "independent", [], []) for role in selected]
            first = [require(await call(data)) for data in first_inputs]
            prior = [as_prior_result(packet) for packet in first]
            artifacts = [item for packet in first for item in packet["tool_artifacts"]]
            # All cross reviewers see the same completed independent set; no earlier
            # cross review is appended to a later reviewer's context.
            cross_inputs = [invocation(role, "cross_review", prior, artifacts) for role in selected]
            cross = [require(await call(data)) for data in cross_inputs]
            prior += [as_prior_result(packet) for packet in cross]
            artifacts += [item for packet in cross for item in packet["tool_artifacts"]]
            draft = require(await call(invocation("integrator", "draft_synthesis", prior, artifacts)))
            prior.append(as_prior_result(draft))
            artifacts += draft["tool_artifacts"]
            redteam = require(await call(invocation("redteam", "redteam", prior, artifacts)))
            prior.append(as_prior_result(redteam))
            artifacts += redteam["tool_artifacts"]
            final_input = invocation("integrator", "final_synthesis", prior, artifacts)
            final = require(await call(final_input))
            if "mode_analysis" not in final["result"]:
                raise ModeStop("failed", "Final synthesis lacks the required structured mode analysis")
            validate_mode_analysis(final_input, final["result"], self.store.schemas)
            result = copy.deepcopy(final["result"])
        except ModeStop as exc:
            status, reason = exc.status, exc.reason
        except asyncio.CancelledError:
            status, reason = "cancelled", "Mode session cancelled; explicit host resume required"
        except DataError:
            if recovery is not None: raise
            status, reason = "failed", "Mode session validation/execution failed"
        except Exception:
            status, reason = "failed", "Mode session validation/execution failed"
        completion = {"schema_version": "1.0", "run_id": run_id, "world_id": task["world_id"],
            "task_id": task["task_id"], "canon_version": task["canon_version"], "mode": task["task_type"],
            "status": status, "reason": reason, "reserved_cost_usd": str(reserved),
            "policy_sha256": self.router.sha256, "host_config_sha256": self.config_sha256,
            "routes": routes, "agent_run_ids": [p["agent_run"]["agent_run_id"] for p in packets],
            "result": result, "approval_status": "not_requested"}
        name = 'completion.json' if not workspace.path('completion.json').exists() else 'completions/' + new_id('artifact') + '.json'
        workspace.write_json(name, completion)
        observe("completion", completion)
        return completion


class ModeStop(Exception):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason


def run_cli(args):
    if not args.allow_live:
        raise DataError("Mode execution requires the operator's --allow-live flag")
    config = read_json(args.workspace.host_file(args.config))
    # Validate trusted profiles before reading the caller-selected credential file.
    runner = ModeRunner(args.workspace, config, runtime_factory=lambda mid, profile: runtime_from_config(args.workspace, profile, keys))
    keys = credentials(args.workspace.host_file(args.credentials))
    return asyncio.run(runner.run(read_json(args.task)))
