"""Host routing and mode boundaries; all providers below are synthetic."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from axiom_forge.contracts import IDENTITY, SPECIALISTS, validate_agent_output
from axiom_forge.modes import MODES, ModeRunner
from axiom_forge.mode_validation import validate_mode_analysis
from axiom_forge.routing import ModelRouter, read_policy
from axiom_forge.validation import DataError, SchemaStore, read_json
from examples.offline_task_manager import initialize_fixture
from examples.offline_modes import factory, fixture_analysis

ROOT = Path(__file__).resolve().parents[1]


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.router = ModelRouter(ROOT)
        self.request = read_json(ROOT / "examples/routing-request.json")

    def test_only_validated_enabled_current_models_selected(self):
        for role in self.router.assignments:
            for kind in ("metadata", "research", "synthesis"):
                result = self.router.select({**self.request, "role": role, "task_kind": kind})
                if result["model_id"]:
                    model = self.router.model(result["model_id"])
                    self.assertTrue(model["enabled"])
                    self.assertEqual(model["validation"], "passed")
                    self.assertEqual(model["pool"], "current")
        for mid in ("claude-fable-5.1", "gpt-6-astra", "deepseek-4.1-flash"):
            self.assertFalse(self.router.model(mid)["enabled"])

    def test_capacity_tools_latency_and_budget_do_not_silently_downgrade(self):
        for updates in ({"context_size": 1900000}, {"budget_usd": 0}, {"latency_tolerance": 0},
                        {"major_canon_change": True}, {"difficulty": 3}):
            result = self.router.select({**self.request, **updates})
            self.assertEqual(result["status"], "OPEN_QUESTION")
        with self.assertRaises(DataError): self.router.select({**self.request, "required_tools": ["shell"]})
        with self.assertRaises(DataError): self.router.select({**self.request, "budget_usd": float("nan")})

    def test_cheap_first_and_editable_role_preference(self):
        self.router.models["gpt-6-luna"].update(enabled=True, validation="passed")
        self.assertEqual(self.router.select({**self.request, "task_kind": "metadata"})["model_id"], "gpt-6-luna")
        self.assertEqual(self.router.select({**self.request, "role": "engineering_auditor"})["model_id"], "gpt-6.1-sol")
        self.router.assignments["engineering_auditor"] = ["claude-sonnet-5.5", "gpt-6.1-sol"]
        self.assertEqual(self.router.select({**self.request, "role": "engineering_auditor"})["model_id"], "claude-sonnet-5.5")

    def test_independent_review_family_required_and_missing_capacity_explicit(self):
        pair = self.router.pair({**self.request, "role": "lead"}, {**self.request, "role": "redteam"})
        self.assertEqual(pair["status"], "selected")
        self.assertNotEqual(self.router.model(pair["lead"]["model_id"])["family"], self.router.model(pair["redteam"]["model_id"])["family"])
        self.router.models["gpt-6.1-sol"]["enabled"] = False
        self.router.models["gpt-6-luna"]["enabled"] = False
        self.assertEqual(self.router.pair({**self.request, "role": "lead"}, {**self.request, "role": "redteam"})["status"], "OPEN_QUESTION")

    def test_bounded_escalation_and_no_skipping_disabled_frontier(self):
        flags = {"uncertain": True, "disagreement": False, "unresolved": False}
        self.router.models["claude-opus-5.5"].update(enabled=True, validation="passed")
        self.assertEqual(self.router.escalate(self.request, "gpt-6.1-sol", ["gpt-6.1-sol"], flags)["model_id"], "claude-opus-5.5")
        self.assertEqual(self.router.escalate(self.request, "claude-opus-5.5", ["gpt-6.1-sol", "claude-opus-5.5"], flags)["status"], "OPEN_QUESTION")
        self.assertEqual(self.router.escalate(self.request, "gpt-6-astra", ["gpt-6-astra"], flags)["status"], "OPEN_QUESTION")
        with self.assertRaises(DataError): self.router.escalate(self.request, "gpt-6.1-sol", [], flags)

    def test_closed_yaml_rejects_duplicates_aliases_tags_nonfinite_and_nonobjects(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()) / "axiom-forge-test-runs") as temporary:
            file = Path(temporary) / "policy.yaml"
            for raw in ("a: 1\na: 2", "a: &x [1]\nb: *x", "a: !!python/object:builtins.list {}", "a: .nan", "[1,2]", "a: 2026-10-06"):
                file.write_text(raw, encoding="utf-8")
                with self.assertRaises(DataError): read_policy(file)
            file.write_text("a: 1", encoding="utf-8")
            self.assertEqual(read_policy(file), {"a": 1})


class ModeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        scratch = Path(tempfile.gettempdir()) / "axiom-forge-test-runs"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.repo = Path(self.temporary.name).absolute()
        self.workspace = initialize_fixture(self.repo).world
        self.repo = self.workspace.root
        self.engine = self.workspace.engine.root
        self.config = read_json(ROOT / "examples/mode-host.json")
        self.config["max_cost_usd"] = 20
        self.task = read_json(ROOT / "examples/task_state.json")
        self.schemas = self.workspace.schemas

    def tearDown(self): self.temporary.cleanup()

    async def test_all_modes_real_runtime_contract_storage_and_isolation(self):
        before = copy.deepcopy(self.task)
        self.task["metadata"]["private_peer_answer"] = "DO_NOT_FORWARD"
        for mode in MODES:
            self.task["task_type"] = mode
            seen = []
            receipt = await ModeRunner(self.workspace, self.config, runtime_factory=factory(self.workspace, seen)).run(self.task)
            self.assertEqual(receipt["status"], "completed", receipt["reason"])
            self.assertEqual(len(seen), 12)
            self.assertEqual(len({d["agent_run_id"] for d in seen}), 12)
            self.assertTrue(all(d["canon_snapshot"] == self.task["canon_snapshot"] for d in seen))
            for data in seen:
                self.assertNotIn("DO_NOT_FORWARD", json.dumps(data))
                if data["stage"] in ("planning", "independent"):
                    self.assertEqual(data["prior_results"], [])
            cross = [data for data in seen if data["stage"] == "cross_review"]
            self.assertTrue(all(data["prior_results"] == cross[0]["prior_results"] for data in cross))
            self.assertTrue(all(p["stage"] == "independent" for p in cross[0]["prior_results"]))
            self.assertEqual(receipt["approval_status"], "not_requested")
            self.assertEqual(receipt["result"]["mode_analysis"]["mode"], mode)
            self.assertEqual(receipt["result"]["verdict"], "OPEN QUESTION")
            self.assertTrue((self.repo / "world/world.json").exists())
        self.assertEqual(self.task["canon_snapshot"], before["canon_snapshot"])

    async def test_failed_first_round_stops_reviews_and_no_final_result(self):
        seen = []
        receipt = await ModeRunner(self.workspace, self.config, runtime_factory=factory(self.workspace, seen, "independent")).run(self.task)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual([d["stage"] for d in seen], ["planning", "independent"])
        self.assertIsNone(receipt["result"])

    async def test_budget_reservation_and_missing_family_stop_without_fallback(self):
        for kind in ("budget", "family"):
            config = copy.deepcopy(self.config)
            if kind == "budget": config["max_cost_usd"] = 0.01
            else: config["profiles"] = {"claude-sonnet-5.5": config["profiles"]["claude-sonnet-5.5"]}
            seen = []
            receipt = await ModeRunner(self.workspace, config, runtime_factory=factory(self.workspace, seen)).run(self.task)
            self.assertEqual(receipt["status"], "OPEN_QUESTION")
            self.assertIsNone(receipt["result"])
            if kind == "budget": self.assertEqual(seen, [])
            else: self.assertNotIn("redteam", [d["role"] for d in seen])

    def test_profile_cannot_change_registered_model_provider_or_embed_secrets(self):
        for field, value in (("model", "unknown"), ("provider", "other"), ("api_key", "SECRET")):
            config = copy.deepcopy(self.config)
            config["profiles"]["gpt-6.1-sol"][field] = value
            with self.assertRaises(DataError): ModeRunner(self.workspace, config, runtime_factory=factory(self.workspace))

    def test_mode_semantics_reject_false_links_duplicate_domains_and_unknown_evidence(self):
        data = read_json(ROOT / "examples/agents/integrator-input.json")
        for mode, mutate in (("scenario_simulation", lambda a: a["causal_nodes"][1].update(parents=["N3"])),
                             ("roundtable", lambda a: a["positions"][1].update(role="researcher")),
                             ("court", lambda a: a["objections"][1].update(domain="physics"))):
            analysis = fixture_analysis(mode)
            data["task_type"] = mode
            mutate(analysis)
            with self.assertRaises(DataError): validate_mode_analysis(data, {"mode_analysis": analysis}, self.schemas)
        analysis = fixture_analysis("court")
        analysis["proponent"]["evidence_ids"] = ["EVD-999"]
        data["task_type"] = "court"
        with self.assertRaises(DataError): validate_mode_analysis(data, {"mode_analysis": analysis}, self.schemas)

    def test_mode_protocol_requires_typed_final_result_without_breaking_legacy(self):
        data = read_json(ROOT / "examples/agents/integrator-input.json")
        data["mode_protocol"] = "1.0"
        output = read_json(ROOT / "examples/synthesis_result.json")
        output.update({key: data[key] for key in IDENTITY})
        data["stage"] = "final_synthesis"
        with self.assertRaises(DataError): validate_agent_output(data, output, self.schemas)
