"""Trusted, offline business routing. This module never calls a model or reads keys."""

import copy
from pathlib import Path

import yaml

from .contracts import OUTPUTS
from .tools.storage import read_bounded
from .validation import DataError, SchemaStore, canonical_bytes, digest


class ClosedLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise DataError("YAML aliases are not supported in host policy")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise DataError("Policy keys must be unique strings")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def read_policy(path):
    try:
        value = yaml.load(read_bounded(path, limit=131072).decode("utf-8"), Loader=ClosedLoader)
        canonical_bytes(value)  # Reject timestamps, nonfinite numbers and other non-JSON data.
    except (yaml.YAMLError, UnicodeError, RecursionError, TypeError) as exc:
        raise DataError("Invalid bounded YAML host policy") from exc
    if not isinstance(value, dict):
        raise DataError("Host policy must be an object")
    return value


class ModelRouter:
    def __init__(self, repo):
        self.repo = Path(repo).absolute()
        self.schemas = SchemaStore(self.repo / "schemas")
        policies = {}
        for name in ("model_registry", "routing_policy", "escalation_policy", "role_assignments"):
            data = read_policy(self.repo / "routing" / (name + ".yaml"))
            self.schemas.validate(name, data)
            policies[name] = data
        self.registry = policies["model_registry"]
        self.policy = policies["routing_policy"]
        self.escalation = policies["escalation_policy"]
        self.assignments = policies["role_assignments"]["roles"]
        self.models = {item["id"]: item for item in self.registry["models"]}
        if len(self.models) != len(self.registry["models"]):
            raise DataError("Duplicate registered model ID")
        if set(self.assignments) != set(OUTPUTS):
            raise DataError("All research roles require editable assignments")
        for item in self.models.values():
            if item["enabled"] and (item["validation"] != "passed" or item["pool"] != "current"
                                    or item["runtime_provider"] not in ("openai", "claude")):
                raise DataError("Enabled model needs a validated supported Runtime")
        for values in self.assignments.values():
            if any(model not in self.models for model in values):
                raise DataError("Assignment references unknown model")
        self.sha256 = digest(policies)

    def validate_request(self, request):
        canonical_bytes(request)
        self.schemas.validate("routing_request", request)
        if request["role"] not in self.assignments:
            raise DataError("No research role assignment")

    def minimum_tier(self, request):
        tier = self.policy["task_minimum_tiers"][request["task_kind"]]
        if request["difficulty"] >= self.policy["extreme_difficulty"] or request["major_canon_change"]:
            tier = max(tier, 3)
        elif request["importance"] >= self.policy["high_importance"]:
            tier = max(tier, 2)
        if request["tool_complexity"] >= self.policy["complex_tools"]:
            tier = max(tier, 1)
        return tier

    def select(self, request, *, minimum_tier=None, exclude=(), different_family=None):
        self.validate_request(request)
        tier = self.minimum_tier(request)
        if minimum_tier is not None:
            if type(minimum_tier) is not int or not 0 <= minimum_tier <= 3:
                raise DataError("Invalid escalation tier")
            tier = max(tier, minimum_tier)
        preference = self.assignments[request["role"]]
        candidates, rejected = [], {}
        for model in self.models.values():
            reasons = []
            if model["id"] not in preference: reasons.append("not_assigned")
            if not model["enabled"] or model["validation"] != "passed": reasons.append("disabled_or_unverified")
            if model["pool"] != "current": reasons.append("legacy")
            if model["tier"] < tier: reasons.append("insufficient_tier")
            if model["id"] in exclude: reasons.append("already_attempted")
            if model["family"] == different_family: reasons.append("same_family")
            if model["context_tokens"] is None or request["context_size"] + request["output_tokens"] > model["context_tokens"]:
                reasons.append("context_capacity")
            if model["max_output_tokens"] is None or request["output_tokens"] > model["max_output_tokens"]:
                reasons.append("output_capacity")
            if not set(request["required_tools"]).issubset(model["available_tools"]): reasons.append("tool_capacity")
            if model["latency_class"] > request["latency_tolerance"]: reasons.append("latency")
            if model["minimum_reservation_usd"] > request["budget_usd"]: reasons.append("budget")
            if reasons:
                rejected[model["id"]] = reasons
            else:
                candidates.append(model)
        # Cheap-first tier is primary; editable role preference breaks ties within a tier.
        candidates.sort(key=lambda m: (m["tier"], preference.index(m["id"]), m["cost_class"], m["id"]))
        chosen = candidates[0] if candidates else None
        return {"status": "selected" if chosen else "OPEN_QUESTION", "model_id": chosen["id"] if chosen else None,
                "minimum_tier": tier, "policy_sha256": self.sha256, "rejected": rejected,
                "reason": "eligible_model" if chosen else "No validated model satisfies the host constraints"}

    def pair(self, lead_request, review_request):
        lead = self.select(lead_request)
        if lead["model_id"] is None:
            return {"lead": lead, "redteam": None, "status": "OPEN_QUESTION"}
        self.validate_request(review_request)
        require = (lead_request["need_independent_review"] or review_request["need_independent_review"]
                   or max(lead_request["importance"], review_request["importance"]) >= self.policy["high_importance"])
        review = self.select(review_request, different_family=self.models[lead["model_id"]]["family"] if require else None)
        return {"lead": lead, "redteam": review,
                "status": "selected" if review["model_id"] else "OPEN_QUESTION"}

    def escalate(self, request, current_model, attempted, signals):
        self.validate_request(request)
        if current_model not in self.models or not isinstance(attempted, list) or len(set(attempted)) != len(attempted):
            raise DataError("Invalid escalation history")
        if any(item not in self.models for item in attempted) or current_model not in attempted:
            raise DataError("Escalation history must include the current known model")
        if not isinstance(signals, dict) or set(signals) != {"uncertain", "disagreement", "unresolved"} or any(type(v) is not bool for v in signals.values()):
            raise DataError("Explicit boolean escalation signals required")
        if not any(signals.values()):
            return {"status": "retain", "model_id": current_model, "policy_sha256": self.sha256}
        current_tier = self.models[current_model]["tier"]
        if current_tier >= 3 or len(attempted) >= self.escalation["max_attempts"]:
            return {"status": "OPEN_QUESTION", "model_id": None, "reason": "Escalation exhausted", "policy_sha256": self.sha256}
        next_tier = self.escalation["next_tier"][str(current_tier)]
        return self.select(request, minimum_tier=next_tier, exclude=attempted)

    def model(self, model_id):
        if model_id not in self.models:
            raise DataError("Unknown model")
        return copy.deepcopy(self.models[model_id])
