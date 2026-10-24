"""Local validation, tools, and explicitly enabled Runtime CLI."""

import argparse
import json
import sys
from pathlib import Path

from .ids import DOMAIN_PREFIXES, ID_PREFIXES, new_id
from .contracts import ContractStore, validate_agent_input, validate_agent_output
from .snapshots import create_snapshot, verify_snapshot
from .validation import DataError, SchemaStore, collect_world, read_json, validate_task
from .workspaces import EngineResources, WorldWorkspace, create_world
from .project_metadata import ProjectMetadataError, check_project, check_project_file


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", type=Path, help="Explicit trusted system resource root")
    parser.add_argument("--world", type=Path, help="External world Git workspace; never defaults to cwd")
    parser.add_argument("--host-root", type=Path, help="External trusted host configuration/approval storage")
    parser.add_argument("--repo", type=Path, help="Legacy mixed layout; rejected, use --world/--engine-root")
    commands = parser.add_subparsers(dest="command", required=True)
    world = commands.add_parser("world", help="Independent local world workspaces")
    world_actions = world.add_subparsers(dest="world_action", required=True)
    world_create = world_actions.add_parser("create")
    world_create.add_argument("--path", type=Path, required=True)
    world_create.add_argument("--name", required=True)
    world_create.add_argument("--author-name")
    world_create.add_argument("--author-email")
    world_actions.add_parser("check")
    project = commands.add_parser("project", help="Read-only project metadata; no registration or Git checks")
    project_actions = project.add_subparsers(dest="project_action", required=True)
    project_actions.add_parser("check")
    commands.add_parser("check-system-boundary")
    commands.add_parser("validate-world")
    commands.add_parser("check-schemas")
    commands.add_parser("check-contracts")
    tasks = commands.add_parser("tasks", help="Host Task Manager; no automatic approval")
    task_actions = tasks.add_subparsers(dest="task_action", required=True)
    task_run = task_actions.add_parser("run")
    task_run.add_argument("--question-file", type=Path, required=True)
    task_run.add_argument("--mode", choices=["scenario_simulation", "direct_challenge", "roundtable", "court"], required=True)
    task_run.add_argument("--entity", action="append", default=[])
    task_run.add_argument("--config", type=Path, required=True)
    task_run.add_argument("--credentials", type=Path)
    task_run.add_argument("--allow-live", action="store_true")
    for action in ('inspect', 'events', 'resume'):
        entry = task_actions.add_parser(action)
        entry.add_argument('--task-id', required=True)
        if action == 'resume':
            entry.add_argument('--config', type=Path)
            entry.add_argument('--credentials', type=Path)
            entry.add_argument('--allow-live', action='store_true')
    canon = commands.add_parser("canon", help="Local operator approval and Canon branch commits")
    canon_actions = canon.add_subparsers(dest="canon_action", required=True)
    canon_actions.add_parser("init-approval")
    canon_prepare = canon_actions.add_parser("prepare")
    canon_prepare.add_argument("--task", type=Path, required=True)
    for action in ("approve", "reject"):
        decision = canon_actions.add_parser(action)
        decision.add_argument("--bundle", type=Path, required=True)
        decision.add_argument("--reviewer", required=True)
    canon_apply = canon_actions.add_parser("apply")
    canon_apply.add_argument("--bundle", type=Path, required=True)
    canon_recover = canon_actions.add_parser('recover')
    canon_recover.add_argument('--bundle', type=Path, required=True)
    routing = commands.add_parser("routing", help="Offline trusted model policy")
    routing_actions = routing.add_subparsers(dest="routing_action", required=True)
    routing_actions.add_parser("check")
    routing_select = routing_actions.add_parser("select")
    routing_select.add_argument("--request", type=Path, required=True)
    mode = commands.add_parser("modes", help="Bounded worldbuilding mode sessions")
    mode_actions = mode.add_subparsers(dest="mode_action", required=True)
    mode_run = mode_actions.add_parser("run")
    mode_run.add_argument("--task", type=Path, required=True)
    mode_run.add_argument("--config", type=Path, required=True)
    mode_run.add_argument("--credentials", type=Path)
    mode_run.add_argument("--allow-live", action="store_true")
    runtime_parser = commands.add_parser("runtime", help="Host-operated research Runtime")
    runtime_actions = runtime_parser.add_subparsers(dest="runtime_action", required=True)
    runtime_call = runtime_actions.add_parser("run")
    runtime_call.add_argument("--context", type=Path, required=True)
    runtime_call.add_argument("--config", type=Path, required=True, help="Trusted provider, model, limits and tool grants")
    runtime_call.add_argument("--credentials", type=Path, help="Explicit local .env path; never printed")
    runtime_call.add_argument("--allow-live", action="store_true", help="Operator authorizes potentially paid SDK execution")
    tools_parser = commands.add_parser("tools", help="Host-operated, scoped Tool Layer")
    tools_actions = tools_parser.add_subparsers(dest="tool_action", required=True)
    tools_actions.add_parser("list")
    tool_call = tools_actions.add_parser("call")
    tool_call.add_argument("name")
    tool_call.add_argument("--input", type=Path, required=True, help="JSON argument object")
    tool_call.add_argument("--context", type=Path, required=True, help="Validated AgentInput selected by host")
    tool_call.add_argument("--config", type=Path, required=True, help="Trusted host grants; not an Agent-controlled file")
    agent_input = commands.add_parser("validate-agent-input")
    agent_input.add_argument("file", type=Path)
    agent_output = commands.add_parser("validate-agent-output")
    agent_output.add_argument("input", type=Path)
    agent_output.add_argument("output", type=Path)
    validate = commands.add_parser("validate")
    validate.add_argument("schema")
    validate.add_argument("file", type=Path)
    identity = commands.add_parser("new-id")
    identity.add_argument("kind", choices=[*ID_PREFIXES, "entity"])
    identity.add_argument("--domain", choices=list(DOMAIN_PREFIXES))
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("action", choices=["create", "verify"])
    snapshot.add_argument("file", type=Path, nargs="?")
    args = parser.parse_args(argv)
    try:
        if args.repo is not None:
            raise DataError("--repo is a legacy mixed layout. Specify --world and, if needed, --engine-root; existing records are preserved")
        if args.command == "new-id":
            print(new_id(args.kind, args.domain))
            return 0
        args.engine = EngineResources(args.engine_root) if args.engine_root else EngineResources.default()
        schemas = args.engine.schemas
        if args.command == "project":
            if args.world is None:
                raise ProjectMetadataError("inspection_incomplete", "project.json#", "This check requires an explicit external --world directory")
            print(json.dumps(check_project(args.world, args.engine), ensure_ascii=True, indent=2))
            return 0
        if args.command == "validate" and args.schema == "project_metadata":
            print(json.dumps(check_project_file(args.file, schemas), ensure_ascii=True, indent=2))
            return 0
        if args.command == "validate" and args.schema.startswith("repository_"):
            from .repository_receipts import check_receipt_file
            print(json.dumps(check_receipt_file(args.file, args.schema, schemas), ensure_ascii=True, indent=2))
            return 0
        if args.command == "world" and args.world_action == "create":
            receipt = create_world(args.path, args.name, engine=args.engine, host_root=args.host_root,
                                   author_name=args.author_name, author_email=args.author_email)
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            return 0
        if args.command == "check-system-boundary":
            if (args.engine.root / "world").exists():
                raise DataError("Live world/ must be outside system resources; retain templates/fixtures only")
            from .git_host import git
            if (args.engine.root / ".git").exists():
                tracked = git(args.engine.root, "ls-files", "-z", "--", "world", ".axiom", ".cache", ".env", ".env.approval", engine_listing=True)
                if tracked:
                    raise DataError("World data, private state or credentials are tracked in the system repository")
            print("OK: system resources contain no live world or tracked private execution state")
            return 0
        world_required = (args.command in ("tasks", "canon", "modes", "runtime", "validate-world", "world")
                          or args.command == "tools" and args.tool_action == "call"
                          or args.command == "snapshot" and args.action == "create")
        if world_required:
            if args.world is None:
                raise DataError("This operation requires an explicit external --world workspace")
            args.workspace = WorldWorkspace(args.world, args.engine, host_root=args.host_root)
        if args.command == "world":
            print(json.dumps(args.workspace.check(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "tasks":
            from .tasks import run_cli
            receipt = run_cli(args)
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            return 0 if args.task_action in ('inspect', 'events') or receipt['status'] in (
                'completed', 'waiting_approval', 'approved', 'applying', 'committed', 'rejected') else 1
        if args.command == "canon":
            from .canon_host import CanonHost
            host = CanonHost(args.workspace)
            if args.canon_action == "init-approval": receipt = host.init_key()
            elif args.canon_action == "prepare": receipt = host.prepare(args.task)
            elif args.canon_action == "apply": receipt = host.apply(args.bundle)
            elif args.canon_action == 'recover': receipt = host.recover(args.bundle)
            else:
                # Only this host CLI asks for human confirmation; no ToolSession
                # function or model-provided boolean can invoke approval.
                if not sys.stdin.isatty(): raise DataError("Human approval requires an interactive terminal")
                bundle, _, _ = host.reviewed(args.bundle)
                from .validation import digest
                print("Review SHA-256: " + digest(bundle))
                print("Read the full review.md and bundle.json before deciding.")
                confirmed = input("Type the full SHA-256 to confirm this decision: ").strip()
                receipt = host.decide(args.bundle, args.reviewer, confirmed,
                                      status="approved" if args.canon_action == "approve" else "rejected")
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            return 0
        if args.command == "routing":
            from .routing import ModelRouter
            router = ModelRouter(args.engine.root)
            if args.routing_action == "check":
                print(f"OK: {len(router.models)} registered models, policy {router.sha256}")
            else:
                print(json.dumps(router.select(read_json(args.request)), ensure_ascii=False, indent=2))
            return 0
        if args.command == "modes":
            from .modes import run_cli
            receipt = run_cli(args)
            print(json.dumps({key: receipt[key] for key in ("status", "run_id", "mode", "reason", "reserved_cost_usd")}, ensure_ascii=False, indent=2))
            return 0 if receipt["status"] == "completed" else 1
        if args.command == "tools":
            from .tools import ToolSession, definitions
            from .tools.network import PublicHTTPS
            from .tools.python_backend import TrustedPython
            if args.tool_action == "list":
                print(json.dumps(definitions(), ensure_ascii=False, indent=2))
                return 0
            config = read_json(args.workspace.host_file(args.config))
            allowed = {"capabilities", "network_hosts", "documents", "contact", "enable_trusted_python", "python_timeout"}
            if (set(config) - allowed or not isinstance(config.get("capabilities", []), list)
                    or not isinstance(config.get("network_hosts", []), list)
                    or not isinstance(config.get("documents", {}), dict)):
                raise DataError("Invalid host Tool Layer config")
            network = PublicHTTPS(config["network_hosts"], contact=config.get("contact")) if config.get("network_hosts") else None
            backend = TrustedPython(args.engine.root, read_json(args.engine.root / "tools/python-scripts/manifest.json"),
                                    enabled=config.get("enable_trusted_python", False), timeout=config.get("python_timeout", 10))
            session = ToolSession(args.workspace, read_json(args.context), capabilities=config.get("capabilities", []),
                                  documents=config.get("documents", {}), network=network, python_backend=backend)
            result = session.call(args.name, read_json(args.input))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "completed" else 1
        elif args.command == "runtime":
            from .runtimes.cli import run
            packet = run(args)
            # Provider/model content remains in private storage, not console logs.
            print(json.dumps({"status": packet["agent_run"]["status"],
                              "agent_run_id": packet["agent_run"]["agent_run_id"],
                              "artifact": packet["artifact"], "error": packet["error"]}, ensure_ascii=False, indent=2))
            return 0 if packet["agent_run"]["status"] == "completed" else 1
        elif args.command == "check-schemas":
            print(f"OK: {len(schemas.schemas)} schemas, all references resolve offline")
        elif args.command == "check-contracts":
            contracts = ContractStore(args.engine.root, schemas)
            print(f"OK: {len(contracts.contracts)} role contracts and prompt files")
        elif args.command == "validate-agent-input":
            validate_agent_input(read_json(args.file), schemas)
            print(f"OK: agent input: {args.file}")
        elif args.command == "validate-agent-output":
            validate_agent_output(read_json(args.input), read_json(args.output), schemas)
            print(f"OK: agent output: {args.output}")
        elif args.command == "validate-world":
            files = collect_world(args.workspace.root, schemas)
            print(f"OK: {len(files)} knowledge documents")
        elif args.command == "validate":
            data = read_json(args.file)
            if args.schema == "task_state":
                validate_task(data, schemas)
            elif args.schema == "canon_snapshot":
                verify_snapshot(data, schemas)
            elif args.schema == "agent_input":
                validate_agent_input(data, schemas)
            else:
                schemas.validate(args.schema, data)
            print(f"OK: {args.schema}: {args.file}")
        elif args.action == "create":
            if args.file is not None:
                raise DataError("snapshot create does not accept an output override")
            print(create_snapshot(args.workspace.root, schemas))
        else:
            if args.file is None:
                raise DataError("snapshot verify requires a file")
            verify_snapshot(read_json(args.file), schemas)
            print(f"OK: verified self-contained snapshot {args.file}")
        return 0
    except ProjectMetadataError as exc:
        print(json.dumps(exc.diagnostic(), ensure_ascii=True), file=sys.stderr)
        return 1
    except (DataError, OSError, ValueError, EOFError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
