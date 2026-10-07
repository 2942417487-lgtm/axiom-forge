"""Git inspection only. No caller-supplied command, ref, environment or repository."""

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
                or any(part.startswith(".env") or part in (".git", ".cache", ".axiom", "credentials.json", "secrets") for part in relative.parts)):
            raise ToolError("denied", "Git diff is limited to project code and documentation")
        command = ["diff", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all", "--", relative.as_posix()]
    else:
        raise ToolError("denied", "Only status, HEAD and scoped unstaged diff are supported")
    from ..git_host import git
    from ..validation import DataError
    try:
        output = git(repo, *command)
    except DataError as exc:
        raise ToolError("git_failed", "Git inspection failed or repository boundary is unsafe") from exc
    if len(output) > MAX_BYTES:
        raise ToolError("size_limit", "Git output exceeds size limit")
    return {"action": action, "text": output.decode("utf-8", errors="replace")}
