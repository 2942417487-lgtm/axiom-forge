"""Local validation, ID generation, and snapshot CLI; no model calls."""

import argparse
import sys
from pathlib import Path

from .ids import DOMAIN_PREFIXES, ID_PREFIXES, new_id
from .contracts import ContractStore, validate_agent_input, validate_agent_output
from .snapshots import create_snapshot, verify_snapshot
from .validation import DataError, SchemaStore, collect_world, read_json, validate_task


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository root")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-world")
    commands.add_parser("check-schemas")
    commands.add_parser("check-contracts")
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
        if args.command == "new-id":
            print(new_id(args.kind, args.domain))
            return 0
        schemas = SchemaStore(args.repo / "schemas")
        if args.command == "check-schemas":
            print(f"OK: {len(schemas.schemas)} schemas, all references resolve offline")
        elif args.command == "check-contracts":
            contracts = ContractStore(args.repo, schemas)
            print(f"OK: {len(contracts.contracts)} role contracts and prompt files")
        elif args.command == "validate-agent-input":
            validate_agent_input(read_json(args.file), schemas)
            print(f"OK: agent input: {args.file}")
        elif args.command == "validate-agent-output":
            validate_agent_output(read_json(args.input), read_json(args.output), schemas)
            print(f"OK: agent output: {args.output}")
        elif args.command == "validate-world":
            files = collect_world(args.repo, schemas)
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
            print(create_snapshot(args.repo, schemas))
        else:
            if args.file is None:
                raise DataError("snapshot verify requires a file")
            verify_snapshot(read_json(args.file), schemas)
            print(f"OK: verified self-contained snapshot {args.file}")
        return 0
    except (DataError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
