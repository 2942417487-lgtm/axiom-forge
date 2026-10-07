"""Role boundaries; all results and receipts are explicitly synthetic fixtures."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from axiom_forge.contracts import (
    ContractStore, OUTPUTS, SPECIALISTS, project_input, validate_agent_input,
    validate_agent_output, validate_output_artifacts,
)
from axiom_forge.ids import new_id
from axiom_forge.validation import DataError, SchemaStore, digest, read_json

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(tempfile.gettempdir()) / "axiom-forge-test-runs"


def fixture(name):
    return read_json(ROOT / "examples" / f"{name}.json")


def invocation(role):
    return fixture("agent_input" if role == "lead" else f"agents/{role}-input")


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = SchemaStore(ROOT / "schemas")

    def test_all_seven_roles_accept_matching_inputs_outputs(self):
        store = ContractStore(ROOT, self.schemas)
        self.assertEqual(set(store.contracts), set(OUTPUTS))
        for role, output in OUTPUTS.items():
            with self.subTest(role=role):
                data = invocation(role)
                store.validate_input(data)
                store.validate_output(data, fixture(output))

    def test_claude_entrypoints_are_read_only_and_do_not_pin_models(self):
        names = set()
        paths = list((ROOT / ".claude/agents").glob("*.md"))
        self.assertEqual(len(paths), 7)
        for path in paths:
            contents = path.read_text(encoding="utf-8")
            self.assertTrue(contents.startswith("---\n"))
            frontmatter = contents.split("---\n", 2)[1]
            fields = dict(line.split(": ", 1) for line in frontmatter.strip().splitlines())
            self.assertEqual(set(fields), {"name", "description", "tools", "permissionMode"})
            self.assertEqual(fields["tools"], "Read")
            self.assertEqual(fields["permissionMode"], "default")
            self.assertTrue(fields["name"].startswith("axiom-"))
            self.assertNotIn(fields["name"], names)
            names.add(fields["name"])

    def test_projection_does_not_forward_answers_or_task_metadata(self):
        task = fixture("task_state")
        task["metadata"]["hidden_peer_answer"] = "DO NOT FORWARD"
        task["final_result"] = "DO NOT FORWARD"
        execution = {key: new_id(key.removesuffix("_id"))
                     for key in ("run_id", "agent_run_id", "artifact_id")}
        before = copy.deepcopy(task)
        outputs = [project_input(task, execution, role, "independent", list(SPECIALISTS), self.schemas)
                   for role in SPECIALISTS]
        for data in outputs:
            self.assertEqual(data["prior_results"], [])
            self.assertNotIn("metadata", data)
            self.assertNotIn("DO NOT FORWARD", json.dumps(data))
        self.assertEqual(task, before)
        self.assertTrue(all(data["canon_snapshot"] == outputs[0]["canon_snapshot"] for data in outputs))
        outputs[0]["canon_snapshot"]["files"][0]["data"]["statement"] = "mutated"
        self.assertNotEqual(outputs[1]["canon_snapshot"]["files"][0]["data"].get("statement"), "mutated")
        self.assertEqual(task, before)

    def test_projection_rejects_extra_execution_fields(self):
        execution = {key: invocation("lead")[key] for key in ("run_id", "agent_run_id", "artifact_id")}
        execution["provider_thread_id"] = "vendor"
        with self.assertRaisesRegex(DataError, "three system-generated"):
            project_input(fixture("task_state"), execution, "lead", "planning", [], self.schemas)

    def test_independent_input_rejects_peer_results(self):
        data = invocation("researcher")
        data["prior_results"] = invocation("integrator")["prior_results"][:1]
        with self.assertRaisesRegex(DataError, "cannot read prior"):
            validate_agent_input(data, self.schemas)

    def test_independent_input_rejects_artifact_side_channel(self):
        data = invocation("researcher")
        data["supporting_artifacts"] = [fixture("artifact")]
        with self.assertRaisesRegex(DataError, "cannot read prior"):
            validate_agent_input(data, self.schemas)

    def test_input_rejects_full_task_state_or_opaque_metadata(self):
        for extra in ({"metadata": {"other_answer": "leak"}}, {"task_state": fixture("task_state")}):
            data = invocation("researcher")
            data.update(extra)
            with self.assertRaises(DataError):
                validate_agent_input(data, self.schemas)

    def test_role_stage_selection_are_checked(self):
        for mutate in (lambda d: d.update(stage="final_synthesis"),
                       lambda d: d.update(selected_specialists=[]),
                       lambda d: d.update(selected_specialists=["engineering_auditor"]),
                       lambda d: d.update(role="unknown")):
            data = invocation("researcher")
            mutate(data)
            with self.assertRaises(DataError):
                validate_agent_input(data, self.schemas)

    def test_changed_snapshot_version_or_relevant_scope_rejected(self):
        for mutate in (lambda d: d.update(canon_version="CANON-" + "0" * 64),
                       lambda d: d.update(world_id=new_id("world")),
                       lambda d: d.update(relevant_entities=["TECH-999"]),
                       lambda d: d["canon_snapshot"]["files"][0]["data"].update(statement="tampered")):
            data = invocation("researcher")
            mutate(data)
            with self.assertRaises(DataError):
                validate_agent_input(data, self.schemas)

    def test_review_waits_for_all_selected_first_rounds(self):
        data = invocation("redteam")
        data["prior_results"].pop()
        with self.assertRaisesRegex(DataError, "All selected Specialists"):
            validate_agent_input(data, self.schemas)
        data = invocation("redteam")
        data["prior_results"][0]["stage"] = "cross_review"
        with self.assertRaisesRegex(DataError, "All selected Specialists"):
            validate_agent_input(data, self.schemas)

    def test_dynamic_selection_can_use_only_one_specialist(self):
        data = invocation("redteam")
        data["selected_specialists"] = ["researcher"]
        data["prior_results"] = data["prior_results"][:1]
        validate_agent_input(data, self.schemas)

    def test_unselected_and_premature_roles_rejected(self):
        data = invocation("redteam")
        data["selected_specialists"] = ["researcher"]
        with self.assertRaisesRegex(DataError, "unselected or premature"):
            validate_agent_input(data, self.schemas)
        data = invocation("integrator")
        data.update(role="researcher", stage="cross_review", agent_run_id=new_id("agent_run"), artifact_id=new_id("artifact"))
        with self.assertRaisesRegex(DataError, "unselected or premature"):
            validate_agent_input(data, self.schemas)

    def test_final_synthesis_requires_redteam(self):
        data = invocation("integrator")
        data["prior_results"].pop()
        with self.assertRaisesRegex(DataError, "requires Red Team"):
            validate_agent_input(data, self.schemas)

    def test_optional_draft_can_be_reviewed_by_redteam(self):
        data = invocation("redteam")
        task = fixture("task_state")
        synthesis = task["synthesis"]
        data["prior_results"].append(dict(stage="draft_synthesis", result=synthesis,
            agent_run=task["agent_runs"][-1], artifact=task["artifacts"][-1]))
        validate_agent_input(data, self.schemas)
        data["prior_results"][-1]["stage"] = "redteam"
        with self.assertRaisesRegex(DataError, "invalid role/stage"):
            validate_agent_input(data, self.schemas)

    def test_cross_review_and_draft_are_available_only_after_first_rounds(self):
        data = invocation("redteam")
        for role, stage in (("researcher", "cross_review"), ("integrator", "draft_synthesis")):
            projected = copy.deepcopy(data)
            projected.update(role=role, stage=stage, agent_run_id=new_id("agent_run"), artifact_id=new_id("artifact"))
            validate_agent_input(projected, self.schemas)

    def test_prior_completion_receipt_and_hash_checked(self):
        for mutate in (lambda p: p["agent_run"].update(status="running"),
                       lambda p: p["agent_run"].update(finished_at=None),
                       lambda p: p["agent_run"].update(finished_at="2000-01-01T00:00:00Z"),
                       lambda p: p["result"].update(summary="changed"),
                       lambda p: p["artifact"].update(agent_run_id=new_id("agent_run"))):
            data = invocation("redteam")
            mutate(data["prior_results"][0])
            with self.assertRaises(DataError):
                validate_agent_input(data, self.schemas)

    def test_prior_identity_and_role_checked(self):
        for mutate in (lambda p: p["result"].update(canon_version="CANON-" + "0" * 64),
                       lambda p: p["artifact"].update(run_id=new_id("run")),
                       lambda p: p["agent_run"].update(role="economic_auditor"),
                       lambda p: p["result"].update(task_id=new_id("task"))):
            data = invocation("redteam")
            mutate(data["prior_results"][0])
            with self.assertRaises(DataError):
                validate_agent_input(data, self.schemas)

    def test_duplicates_and_current_execution_as_prior_rejected(self):
        data = invocation("redteam")
        data["prior_results"].append(copy.deepcopy(data["prior_results"][0]))
        with self.assertRaisesRegex(DataError, "Duplicate or current"):
            validate_agent_input(data, self.schemas)
        data = invocation("redteam")
        data["agent_run_id"] = data["prior_results"][0]["agent_run"]["agent_run_id"]
        with self.assertRaisesRegex(DataError, "Duplicate or current"):
            validate_agent_input(data, self.schemas)

    def test_output_schema_and_identity_are_bound_to_role(self):
        data = invocation("researcher")
        with self.assertRaises(DataError):
            validate_agent_output(data, fixture("engineering_result"), self.schemas)
        for key in ("task_id", "run_id", "agent_run_id", "artifact_id", "world_id"):
            output = fixture("research_result")
            output[key] = new_id(key.removesuffix("_id"))
            with self.assertRaisesRegex(DataError, "Output identity"):
                validate_agent_output(data, output, self.schemas)

    def test_output_cannot_launder_synthetic_fact(self):
        output = fixture("research_result")
        evidence = output["evidence"][0]
        output["claims"][0].update(category="FACT", evidence_ids=[evidence["evidence_id"]])
        with self.assertRaisesRegex(DataError, "requires recorded source reading"):
            validate_agent_output(invocation("researcher"), output, self.schemas)

    def test_output_requires_known_claim_conflict_and_causal_references(self):
        output = fixture("research_result")
        output["claims"][0]["entity_ids"] = ["TECH-999"]
        with self.assertRaises(DataError):
            validate_agent_output(invocation("researcher"), output, self.schemas)
        output = fixture("historical_result")
        output["causal_chains"] = [dict(steps=["TEST CAUSE", "TEST EFFECT"], assumptions=[], evidence_ids=[new_id("evidence")])]
        with self.assertRaisesRegex(DataError, "Causal chain references unknown"):
            validate_agent_output(invocation("historical_analyst"), output, self.schemas)
        output = fixture("redteam_result")
        output["contradictions"] = [dict(conflict_id=new_id("claim"), description="TEST FIXTURE",
            entity_ids=["TECH-999"], evidence_ids=[], severity="high", resolution=None)]
        with self.assertRaisesRegex(DataError, "Conflict references unknown"):
            validate_agent_output(invocation("redteam"), output, self.schemas)

    def test_integrator_cannot_approve_or_change_the_proposal_baseline(self):
        for mutate in (lambda c: c["approval"].update(status="approved", reviewer="forged",
                         reviewed_at="2026-10-03T00:00:00Z", decision_id="DEC-001"),
                       lambda c: c.update(base_canon_version="CANON-" + "0" * 64),
                       lambda c: c["after"].update(dependencies=["TECH-999"])):
            output = fixture("synthesis_result")
            mutate(output["proposed_changes"][0])
            with self.assertRaises(DataError):
                validate_agent_output(invocation("integrator"), output, self.schemas)

    def test_lead_plan_cannot_change_canon_or_duplicate_assignments(self):
        for mutate in (lambda p: p.update(proposed_changes=[]),
                       lambda p: p["assignments"].append(copy.deepcopy(p["assignments"][0])),
                       lambda p: p["assignments"][0].update(entity_ids=["TECH-999"])):
            output = fixture("lead_plan")
            mutate(output)
            with self.assertRaises(DataError):
                validate_agent_output(invocation("lead"), output, self.schemas)

    def test_calculation_receipts_are_validated_after_independent_execution(self):
        data = invocation("engineering_auditor")
        output = fixture("engineering_result")
        identifier = new_id("artifact")
        output["calculations"] = [dict(artifact_id=identifier, description="TEST FIXTURE",
            tool="python", inputs=[dict(name="x", value=1, unit="m")],
            outputs=[dict(name="y", value=2, unit="m")], assumptions=["TEST FIXTURE"],
            reproducible_code="y = 2 * x")]
        with self.assertRaisesRegex(DataError, "supporting artifact is missing"):
            validate_agent_output(data, output, self.schemas)
        receipt = fixture("artifact")
        receipt.update({key: data[key] for key in ("world_id", "task_id", "run_id", "agent_run_id")})
        receipt.update(artifact_id=identifier, kind="calculation", path="test-only/calculation.json")
        before = copy.deepcopy(data)
        validate_output_artifacts(data, output, self.schemas, [receipt])
        self.assertEqual(data, before)
        receipt["agent_run_id"] = new_id("agent_run")
        with self.assertRaisesRegex(DataError, "another Agent Run"):
            validate_output_artifacts(data, output, self.schemas, [receipt])

    def test_prior_output_cannot_carry_approved_proposals(self):
        data = invocation("redteam")
        task = fixture("task_state")
        result = task["synthesis"]
        result["proposed_changes"][0]["approval"].update(status="approved", reviewer="forged",
            reviewed_at="2026-10-03T00:00:00Z", decision_id="DEC-001")
        artifact = task["artifacts"][-1]
        artifact["sha256"] = digest(result)
        data["prior_results"].append(dict(stage="draft_synthesis", result=result,
            agent_run=task["agent_runs"][-1], artifact=artifact))
        with self.assertRaisesRegex(DataError, "only propose pending"):
            validate_agent_input(data, self.schemas)

    def test_final_integrator_can_revise_or_withdraw_draft_proposals(self):
        data = invocation("integrator")
        task = fixture("task_state")
        draft = copy.deepcopy(task["synthesis"])
        agent, artifact = copy.deepcopy(task["agent_runs"][-1]), copy.deepcopy(task["artifacts"][-1])
        draft.update(agent_run_id=new_id("agent_run"), artifact_id=new_id("artifact"))
        agent.update(agent_run_id=draft["agent_run_id"], artifact_id=draft["artifact_id"])
        artifact.update(agent_run_id=draft["agent_run_id"], artifact_id=draft["artifact_id"], sha256=digest(draft))
        data["prior_results"].append(dict(stage="draft_synthesis", result=draft, agent_run=agent, artifact=artifact))
        output = fixture("synthesis_result")
        output["proposed_changes"][0]["proposal_id"] = new_id("proposal")
        output["proposed_changes"][0]["after"]["statement"] = "TEST FIXTURE：修订后的提案"
        validate_agent_output(data, output, self.schemas)
        output["proposed_changes"] = []
        validate_agent_output(data, output, self.schemas)
        self.assertEqual(data["prior_results"][-1]["result"], draft)

    def test_validation_never_mutates_inputs_or_production_world(self):
        data, result = invocation("integrator"), fixture("synthesis_result")
        before = copy.deepcopy((data, result))
        world_before = {p: p.read_bytes() for p in (ROOT / "templates/legacy-world").rglob("*.json")}
        validate_agent_output(data, result, self.schemas)
        self.assertEqual((data, result), before)
        self.assertEqual(world_before, {p: p.read_bytes() for p in (ROOT / "templates/legacy-world").rglob("*.json")})

    def test_registry_rejects_missing_roles_or_relaxed_boundaries(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            repo = Path(tmp)
            (repo / "agents/contracts").mkdir(parents=True)
            with self.assertRaisesRegex(DataError, "seven role"):
                ContractStore(repo, self.schemas)
            contract = read_json(ROOT / "agents/contracts/lead.json")
            contract["stages"] = ["independent"]
            (repo / "agents/contracts/lead.json").write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(DataError, "protected role boundary"):
                ContractStore(repo, self.schemas)

    def test_cli_contract_commands_and_semantic_failure(self):
        for arguments, expected in ((["check-contracts"], 0),
                (["validate-agent-input", "examples/agents/redteam-input.json"], 0),
                (["validate", "agent_input", "examples/agents/integrator-input.json"], 0),
                (["validate-agent-output", "examples/agent_input.json", "examples/lead_plan.json"], 0),
                (["validate-agent-output", "examples/agent_input.json", "examples/research_result.json"], 1)):
            process = subprocess.run([sys.executable, "-m", "axiom_forge", *arguments], cwd=ROOT,
                                     capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(process.returncode, expected, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
