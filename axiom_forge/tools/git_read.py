"""Git inspection only. No caller-supplied command, ref, environment or repository."""

import os
import subprocess

from .storage import MAX_BYTES, ToolError, safe_relative


def git_read(repo, action, path=None):
    if action == "status" and path is None:
        command = ["status", "--porcelain=v1", "--untracked-files=no", "--ignore-submodules=all"]
    elif action == "head" and path is None:
        command = ["rev-parse", "--verify", "HEAD"]
    elif action == "diff" and path is not None:
        relative = safe_relative(path)
        # Grant is limited to code/docs, never .env, .git, .cache or role artifacts.
        if (relative.parts[0] not in ("axiom_forge", "tools", "docs", "schemas", "tests")
                or any(part.startswith(".env") or part in (".git", ".cache", "credentials.json", "secrets") for part in relative.parts)):
            raise ToolError("denied", "Git diff is limited to project code and documentation")
        command = ["diff", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all", "--", relative.as_posix()]
    else:
        raise ToolError("denied", "Only status, HEAD and scoped unstaged diff are supported")
    environment = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "LANG", "LC_ALL")
                   if key in os.environ}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        output = subprocess.run(["git", "-c", "core.fsmonitor=false", "--no-pager", "-C", str(repo), *command],
                                capture_output=True, timeout=10, env=environment, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolError("git_unavailable", "Git inspection unavailable") from exc
    if output.returncode:
        raise ToolError("git_failed", "Git inspection failed")
    if len(output.stdout) > MAX_BYTES:
        raise ToolError("size_limit", "Git output exceeds size limit")
    return {"action": action, "text": output.stdout.decode("utf-8", errors="replace")}
