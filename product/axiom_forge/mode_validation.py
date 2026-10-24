"""Mode-specific structure and references, without deciding scientific truth."""

from .contracts import SPECIALISTS
from .validation import DataError


def validate_mode_analysis(data, output, schemas):
    analysis = output.get("mode_analysis")
    if analysis is None:
        if data.get("mode_protocol") == "1.0" and data["stage"] == "final_synthesis":
            raise DataError("Mode final synthesis requires structured mode analysis")
        return
    schemas.validate("mode_analysis", analysis)
    if analysis["mode"] != data["task_type"]:
        raise DataError("Mode analysis differs from the task mode")
    known = {file["data"]["evidence_id"] for file in data["canon_snapshot"]["files"] if "evidence_id" in file["data"]}
    for result in [packet["result"] for packet in data["prior_results"]] + [output]:
        known.update(item["evidence_id"] for item in result.get("evidence", []))
    def references(node):
        if isinstance(node, dict):
            if "evidence_ids" in node and not set(node["evidence_ids"]).issubset(known):
                raise DataError("Mode analysis references unknown Evidence")
            for value in node.values(): references(value)
        elif isinstance(node, list):
            for value in node: references(value)
    references(analysis)
    mode = analysis["mode"]
    if mode == "scenario_simulation":
        nodes = {item["id"]: item for item in analysis["causal_nodes"]}
        if len(nodes) != len(analysis["causal_nodes"]) or {item["order"] for item in nodes.values()} != {1, 2, 3}:
            raise DataError("Scenario requires unique nodes covering orders 1, 2, 3")
        for node in nodes.values():
            if (node["order"] == 1 and node["parents"]) or (node["order"] > 1 and not node["parents"]):
                raise DataError("Scenario parent/order relation is incomplete")
            for parent in node["parents"]:
                if parent not in nodes or nodes[parent]["order"] != node["order"] - 1:
                    raise DataError("Scenario causal links must connect consecutive orders")
    elif mode == "roundtable":
        roles = [item["role"] for item in analysis["positions"]]
        if len(roles) != len(set(roles)) or set(roles) != set(SPECIALISTS):
            raise DataError("Roundtable must compare all four distinct Specialist positions")
    elif mode == "court":
        domains = [item["domain"] for item in analysis["objections"]]
        if len(domains) != len(set(domains)) or set(domains) != {"physics", "engineering", "economics", "history"}:
            raise DataError("Court must assess all four distinct domains")
