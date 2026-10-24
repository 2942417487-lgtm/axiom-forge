"""Inspect only the explicit development repository index, never secret values."""

from pathlib import Path, PurePosixPath

from axiom_forge.git_host import git
from axiom_forge.tools.storage import check_links
from axiom_forge.validation import DataError
from support import REPOSITORY_ROOT


def check_source_boundary(root=REPOSITORY_ROOT):
    root = Path(root).absolute()
    check_links(root)
    if not (root / ".git").exists():
        raise DataError("Source repository inspection incomplete: Git metadata is missing")
    if (root / "world").exists():
        raise DataError("Live world/ must be outside the source repository")
    tracked = git(root, "ls-files", "-z", "--", engine_listing=True)
    try:
        paths = tracked.decode("utf-8", errors="strict").split("\0")
    except UnicodeError as exc:
        raise DataError("Source repository paths are not valid UTF-8") from exc
    private_directories = {".axiom", ".cache", ".venv", "node_modules", "secrets", "__pycache__"}
    for name in filter(None, paths):
        parts = tuple(part.casefold() for part in PurePosixPath(name).parts)
        filename = parts[-1]
        if (parts[0] == "world" or private_directories.intersection(parts[:-1])
                or filename in (".env", "credentials.json")
                or filename.startswith(".env.") and filename != ".env.example"
                or filename.endswith((".key", ".pem", ".pyc", ".log"))):
            raise DataError("Source repository tracks private state, credentials or generated files")
    return len(tuple(filter(None, paths)))
