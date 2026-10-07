"""Bounded operator Git commands; no network or inherited execution helpers."""

import os
import hashlib
import subprocess
import tempfile
from pathlib import Path

from .tools.storage import check_links, read_bounded
from .validation import DataError

_checked_configs = {}


def check_independent_git(root):
    """Reject shared Git internals and all symlink/junction descendants."""
    directory = Path(root) / ".git"
    check_links(directory)
    if not directory.is_dir():
        raise DataError("Independent Git directory required")
    if (directory / "commondir").exists() or (directory / "objects/info/alternates").exists():
        raise DataError("Shared Git common/object directories are forbidden")
    if (directory / "config.worktree").exists():
        raise DataError("World Git worktree configuration is unsupported")
    # Do not follow links while enumerating. Each child is checked before any
    # traversal; check_links rejects Windows reparse points as well as symlinks.
    def inaccessible(error):
        raise DataError("Cannot inspect independent Git directory") from error
    for current, directories, files in os.walk(directory, followlinks=False, onerror=inaccessible):
        for name in (*directories, *files):
            check_links(Path(current) / name)


def git(root, *args, raw=None, index=None):
    root = Path(root).absolute()
    check_links(root)
    if (root / ".git").is_dir():
        check_independent_git(root)
    env = {key: value for key, value in os.environ.items() if key.upper() in
           {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE"}}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    if (root / ".git").is_dir():
        config = root / ".git/config"
        fingerprint = hashlib.sha256(read_bounded(config)).hexdigest()
        if _checked_configs.get(str(root)) != fingerprint:
            try:
                keys = subprocess.run(["git", "--git-dir=" + str(root / ".git"),
                    "--work-tree=" + str(root), "config", "--local", "--no-includes",
                    "--name-only", "--list"], cwd=root, env=env, capture_output=True,
                    timeout=30, shell=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise DataError("Cannot validate world Git configuration") from exc
            if keys.returncode or len(keys.stdout) > 2 * 1024 * 1024:
                raise DataError("Invalid world Git configuration")
            try:
                names = keys.stdout.decode("utf-8", errors="strict").lower().splitlines()
            except UnicodeError as exc:
                raise DataError("Invalid world Git configuration names") from exc
            for key in names:
                if (key.startswith(("filter.", "include.", "includeif.", "merge."))
                        or key == "extensions.worktreeconfig"
                        or key.startswith("diff.") and key.endswith((".command", ".textconv"))):
                    raise DataError("World Git filters, includes and external drivers require separate host authorization")
            _checked_configs[str(root)] = fingerprint
    # A temporary host directory avoids writing merely to inspect a repository.
    with tempfile.TemporaryDirectory(prefix="axiom-git-hooks-") as hooks:
        location = ["--git-dir=" + str(root / ".git"), "--work-tree=" + str(root)] if (root / ".git").is_dir() else []
        command = ["git", *location, "-c", "core.fsmonitor=false", "-c", "core.autocrlf=false",
                   "-c", "core.attributesFile=" + os.devnull, "-c", "core.excludesFile=" + os.devnull,
                   "-c", "core.pager=", "-c", "diff.external=",
                   "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + hooks, *args]
        try:
            result = subprocess.run(command, cwd=root, env=env, input=raw,
                                    capture_output=True, timeout=30, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DataError("Git host command unavailable or timed out") from exc
    if result.returncode:
        raise DataError("Git host command failed: " + args[0])
    if len(result.stdout) > 2 * 1024 * 1024:
        raise DataError("Git response exceeds size limit")
    return result.stdout
