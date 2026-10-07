"""Trusted engine resources and explicit, independent local world repositories.

Filesystem checks are application boundaries, not an OS sandbox. No world file
is interpreted as executable policy or host authorization.
"""

import copy
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .git_host import git, check_independent_git
from .ids import new_id
from .snapshots import create_snapshot, utc_now
from .tools.storage import Workspace, check_links, read_bounded, strict_json
from .validation import DataError, KNOWLEDGE_DIRECTORIES, SchemaStore, collect_world, digest


STATE_PREFIX = ".axiom/local"
WORLD_IGNORE = """# Local durable execution records: excluded from Git, retain for recovery.
.axiom/local/
.cache/
.env
.env.*
!.env.example
*.key
*.pem
secrets/
credentials.json
*.log
__pycache__/
*.tmp
"""


def checked_root(value):
    path = Path(value).absolute()
    check_links(path)
    return path.resolve()


def disjoint(first, second):
    return not (first.is_relative_to(second) or second.is_relative_to(first))


def resolve_host_root(value=None):
    if value is None:
        local = os.environ.get("LOCALAPPDATA")
        value = Path(local) / "AxiomForge/host" if local else Path.home() / ".axiom-forge/host"
    return checked_root(value)


def root_identity(root):
    return digest(os.path.normcase(str(root)))


@dataclass(frozen=True)
class EngineResources:
    root: Path

    def __post_init__(self):
        object.__setattr__(self, "root", checked_root(self.root))
        for item in ("AGENTS.md", "agents/README.md", "schemas/world.schema.json",
                     "routing/model_registry.yaml", "tools/python-scripts/manifest.json"):
            read_bounded(self.root / item)

    @classmethod
    def default(cls):
        # Source distribution resource locator. A future installer may supply a
        # trusted packaged resource root; never discover it in a world directory.
        return cls(Path(__file__).resolve().parents[1])

    @property
    def schemas(self):
        return SchemaStore(self.root / "schemas")


class WorldWorkspace:
    def __init__(self, root, engine=None, *, host_root=None):
        self.engine = engine if isinstance(engine, EngineResources) else EngineResources(engine) if engine else EngineResources.default()
        self.root = checked_root(root)
        if not disjoint(self.root, self.engine.root):
            raise DataError("World workspace and engine resources must be outside one another")
        if any((parent / ".git").exists() for parent in self.root.parents):
            raise DataError("World workspace cannot be nested inside another Git repository")
        self.host_root = resolve_host_root(host_root)
        if not disjoint(self.host_root, self.root) or not disjoint(self.host_root, self.engine.root):
            raise DataError("Host configuration must be outside the world and engine roots")
        self._check_git()
        self.schemas = self.engine.schemas
        metadata = strict_json(read_bounded(self.root / "world/world.json"))
        self.schemas.validate("world", metadata)
        self.world_id = metadata["world_id"]
        collect_world(self.root, self.schemas)
        self.state = Workspace(self.root / STATE_PREFIX)
        descriptor = {"layout_version": "1.0", "world_id": self.world_id,
                      "root_sha256": root_identity(self.root)}
        path = self.state.path("workspace.json")
        if path.exists():
            stored = strict_json(read_bounded(path))
            if (not isinstance(stored, dict) or set(stored) != {*descriptor, "workspace_id"}
                    or any(stored[k] != value for k, value in descriptor.items())):
                raise DataError("World workspace moved or binding changed; explicit migration is required")
            try:
                identity = uuid.UUID(stored["workspace_id"])
            except (ValueError, TypeError, AttributeError) as exc:
                raise DataError("Invalid workspace identity") from exc
            if str(identity) != stored["workspace_id"] or identity.version != 4:
                raise DataError("Invalid workspace identity")
        else:
            if (self.root / ".cache/tasks").exists() or (self.root / ".cache/runtime-runs").exists():
                raise DataError("Legacy mixed-workspace execution records require explicit migration")
            stored = {**descriptor, "workspace_id": str(uuid.uuid4())}
            self.state.write_json("workspace.json", stored)
        self._binding = stored

    @property
    def binding(self):
        return copy.deepcopy(self._binding)

    @property
    def key_path(self):
        return self.host_root / "world-approvals" / digest(self.binding) / ".env.approval"

    def _check_git(self):
        git_dir = self.root / ".git"
        check_links(git_dir)
        if not git_dir.is_dir():
            raise DataError("World workspace needs its own .git directory; parent repositories/worktrees are unsupported")
        check_independent_git(self.root)
        for item in ("objects", "objects/info/alternates", "config", "HEAD"):
            check_links(git_dir / item)
        if (git_dir / "objects/info/alternates").exists():
            raise DataError("World Git object storage must be independent")
        toplevel = checked_root(git(self.root, "rev-parse", "--show-toplevel").decode("utf-8").strip())
        if toplevel != self.root:
            raise DataError("World path is not the Git repository root")
        git(self.root, "rev-parse", "--verify", "HEAD")
        common_path = Path(git(self.root, "rev-parse", "--git-common-dir").decode("utf-8").strip())
        common = checked_root(common_path if common_path.is_absolute() else self.root / common_path)
        if common != git_dir:
            raise DataError("World Git common directory must belong to the workspace")
        if git(self.root, "rev-parse", "--is-bare-repository").strip() != b"false":
            raise DataError("World workspace requires a working tree")
        for item in (STATE_PREFIX + "/ignore-check", ".env.approval", ".env.local"):
            git(self.root, "check-ignore", "--no-index", item)
        if git(self.root, "ls-files", "-z", "--", STATE_PREFIX, ".env", ".env.approval"):
            raise DataError("Local runtime records and credentials cannot be tracked")

    def validate_binding(self, value):
        if value != self.binding:
            raise DataError("Record belongs to another world workspace or legacy layout")

    def validate_current(self):
        # Recheck local identity and link boundaries on every invocation. Git
        # commands additionally pin their git-dir/work-tree explicitly; full
        # repository validation happens on open/check, not for every SDK tool.
        check_links(self.root / ".git")
        if not (self.root / ".git").is_dir():
            raise DataError("Independent world Git directory disappeared")
        self.validate_binding(strict_json(read_bounded(self.state.path("workspace.json"))))
        metadata = strict_json(read_bounded(self.root / "world/world.json"))
        self.validate_world(metadata.get("world_id") if isinstance(metadata, dict) else None)

    def validate_world(self, value):
        if value != self.world_id:
            raise DataError("Input belongs to another world")

    def host_file(self, value):
        if value is None:
            return None
        path = checked_root(value)
        if path.is_relative_to(self.root) or path.is_relative_to(self.engine.root):
            raise DataError("Host configuration and credential files must be outside world and engine directories")
        return path

    def check(self):
        self._check_git()
        files = collect_world(self.root, self.schemas)
        self.validate_world(files["world/world.json"]["world_id"])
        descriptor = strict_json(read_bounded(self.state.path("workspace.json")))
        self.validate_binding(descriptor)
        return {"status": "valid", "world_id": self.world_id, "workspace": str(self.root),
                "workspace_id": self.binding["workspace_id"], "system_version": __version__,
                "head": git(self.root, "rev-parse", "HEAD").decode("ascii").strip()}


def require_world(value):
    if not isinstance(value, WorldWorkspace):
        raise DataError("Explicit WorldWorkspace required; legacy mixed repositories are not execution targets")
    value.validate_current()
    return value


def create_world(root, name, *, engine=None, host_root=None, author_name=None, author_email=None):
    engine = engine if isinstance(engine, EngineResources) else EngineResources(engine) if engine else EngineResources.default()
    root = checked_root(root)
    if not disjoint(root, engine.root):
        raise DataError("Create the world outside the engine directory")
    if not isinstance(name, str) or not name.strip():
        raise DataError("A world name is required")
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise DataError("World creation requires a new or empty directory; existing files are preserved")
    for parent in root.parents:
        if (parent / ".git").exists():
            raise DataError("Do not create a world inside another Git repository")
    # Validate host placement before writing any world files.
    host_root = resolve_host_root(host_root)
    if not disjoint(host_root, root) or not disjoint(host_root, engine.root):
        raise DataError("Host configuration must be outside the world and engine")
    for value in (author_name, author_email):
        if value is not None and (not isinstance(value, str) or not value.strip()
                                  or len(value) > 120 or any(ord(c) < 32 for c in value)):
            raise DataError("Git author fields must be short nonempty text without control characters")
    root.mkdir(parents=True, exist_ok=True)
    workspace = Workspace(root)
    template = strict_json(read_bounded(engine.root / "templates/world/world.json"))
    template.update(world_id=new_id("world"), name=name.strip(), created_at=utc_now(), metadata={})
    engine.schemas.validate("world", template)
    for directory in (*KNOWLEDGE_DIRECTORIES, "world/snapshots"):
        (root / directory).mkdir(parents=True)
        workspace.write(directory + "/.gitkeep", b"")
    workspace.write_json("world/world.json", template)
    workspace.write(".gitignore", WORLD_IGNORE.encode("utf-8"))
    snapshot = create_snapshot(root, engine.schemas)
    git(root, "init", "-b", "main")
    git(root, "add", "--", ".gitignore", "world")
    # Initial empty-world metadata has no Canon propositions. Later Canon
    # changes still require the independent operator review and branch flow.
    git(root, "config", "--local", "user.name", author_name or "Axiom Forge")
    git(root, "config", "--local", "user.email", author_email or "local@axiom-forge.invalid")
    git(root, "commit", "-m", "Initialize empty world workspace")
    world = WorldWorkspace(root, engine, host_root=host_root)
    return {**world.check(), "status": "created", "snapshot": str(snapshot),
            "github_connected": False, "approval_key_initialized": False}
