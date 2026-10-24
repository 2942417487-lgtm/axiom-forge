"""Explicit SYNTHETIC fixture demo: real contracts/storage, zero model/API calls."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "product"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "development"))
from support import EXAMPLES_ROOT as EXAMPLES, LEGACY_ROOT

from axiom_forge.contracts import IDENTITY, OUTPUTS, SPECIALISTS
from axiom_forge.modes import MODES, ModeRunner
from axiom_forge.runtimes.core import AdapterReply, AgentRuntime, RuntimeLimits
from axiom_forge.tools.session import ToolSession
from axiom_forge.validation import read_json


def fixture_analysis(mode):
    def assessment():
        return {"statement": "SYNTHETIC placeholder; no scientific claim", "reasoning": "Fixture only",
            "assumptions": ["No real research performed"], "evidence_ids": [], "uncertainty": "Unverified fixture"}
    common = {"mode": mode, "open_questions": ["Scientific research not performed"]}
    if mode == "scenario_simulation":
        common.update(causal_nodes=[{"id": "N" + str(order), "order": order,
            "parents": [] if order == 1 else ["N" + str(order - 1)], "analysis": assessment()} for order in (1, 2, 3)],
            consistency_checks=["Fixture structure checked only"])
    elif mode == "direct_challenge":
        common.update(premises=[{"premise": "SYNTHETIC premise", "implicit_conditions": ["Fixture"],
            "counterexamples": ["Potential fixture counterexample, untested"], "analysis": assessment()}], required_revisions=[])
    elif mode == "roundtable":
        common.update(positions=[{"role": role, "position": "No scientific conclusion", "analysis": assessment()} for role in SPECIALISTS],
            disagreements=["Evidence missing"], evidence_comparison="No real Evidence collected")
    else:
        common.update(proposition="SYNTHETIC proposition", burden_of_proof="Not discharged", proponent=assessment(),
            objections=[{"domain": domain, "objection": "Missing real evidence", "resolution": "OPEN QUESTION", "analysis": assessment()}
                for domain in ("physics", "engineering", "economics", "history")], ruling_reasons=["Scientific research not performed"])
    return common


class FixtureAdapter:
    def __init__(self, provider, model, *, seen=None, fail_stage=None):
        self.provider, self.model, self.seen, self.fail_stage = provider, model, seen, fail_stage

    async def execute(self, instructions, prompt, output_schema, tools, limits):
        data = json.loads(prompt)["agent_input"]
        if self.seen is not None: self.seen.append(data)
        if data["stage"] == self.fail_stage: raise ValueError("Synthetic failure")
        output = read_json(EXAMPLES / (OUTPUTS[data["role"]] + ".json"))
        for key, value in list(output.items()):
            if isinstance(value, list): output[key] = []
        output.update({key: data[key] for key in IDENTITY})
        output.update(summary="SYNTHETIC fixture, no scientific research", open_questions=["Scientific research not performed"], metadata={"test_fixture": True})
        if data["role"] == "lead":
            output["assignments"] = [{"role": role, "question": "Synthetic fixture", "entity_ids": [], "required_checks": ["Fixture only"]} for role in SPECIALISTS]
            output["success_criteria"] = ["Fixture passes contracts"]
        if data["role"] == "integrator":
            output["verdict"] = "OPEN QUESTION"
            if data["stage"] == "final_synthesis": output["mode_analysis"] = fixture_analysis(data["task_type"])
        return AdapterReply(output, "SYNTHETIC-NO-API", 0, 0, 0)


def factory(repo, seen=None, fail_stage=None):
    def create(mid, profile):
        return AgentRuntime(repo, FixtureAdapter(profile["provider"], profile["model"], seen=seen, fail_stage=fail_stage),
            limits=RuntimeLimits(**profile.get("limits", {})), session_factory=lambda data: ToolSession(repo, data))
    return create


async def run_fixture(world):
    config = read_json(EXAMPLES / "mode-host.json")
    config["max_cost_usd"] = 20  # Reservations are synthetic; this demo cannot call an API.
    task = read_json(EXAMPLES / "task_state.json")
    for mode in MODES:
        task["task_type"] = mode
        receipt = await ModeRunner(world, config, runtime_factory=factory(world)).run(task)
        print(json.dumps({"test_fixture": True, "mode": mode, "status": receipt["status"], "run_id": receipt["run_id"]}))
        if receipt["status"] != "completed": raise SystemExit(1)


async def main():
    from examples.offline_task_manager import initialize_fixture
    with tempfile.TemporaryDirectory(prefix="axiom-offline-modes-") as directory:
        world = initialize_fixture(Path(directory)).world
        await run_fixture(world)


if __name__ == "__main__": asyncio.run(main())
