"""Host-only reviewed script runner, not a calculator or an OS sandbox."""

import hashlib
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from .storage import MAX_BYTES, ToolError, check_links, read_bounded, safe_relative, strict_json
from ..validation import canonical_bytes


class TrustedPython:
    """Disabled by default. Enabling means a human host trusts the entire script."""

    def __init__(self, repo, manifest, *, enabled=False, timeout=10):
        self.root = Path(repo).absolute() / "resources/tools/python-scripts"
        check_links(self.root)
        self.enabled = enabled
        if (not isinstance(enabled, bool) or not isinstance(timeout, (int, float))
                or isinstance(timeout, bool) or not 0 < timeout <= 30):
            raise ValueError("Invalid Python runner configuration")
        self.timeout = timeout
        if set(manifest) != {"schema_version", "scripts"} or manifest["schema_version"] != "1.0" or not isinstance(manifest["scripts"], list):
            raise ValueError("Invalid reviewed-script manifest")
        self.scripts = {}
        for item in manifest["scripts"]:
            if (not isinstance(item, dict) or set(item) != {"script_id", "path", "sha256", "description"}
                    or not isinstance(item["script_id"], str) or not isinstance(item["sha256"], str)
                    or not re.fullmatch(r"[a-z][a-z0-9_.-]*", item["script_id"])
                    or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"])
                    or not isinstance(item["description"], str) or not item["description"]):
                raise ValueError("Invalid reviewed-script entry")
            path = safe_relative(item["path"])
            if path.suffix != ".py" or item["script_id"] in self.scripts:
                raise ValueError("Duplicate script or unsupported file type")
            self.scripts[item["script_id"]] = dict(item)

    def execute(self, script_id, data, workspace, job_id):
        if not self.enabled:
            raise ToolError("unavailable", "Reviewed-script execution requires explicit trusted-host enablement; no OS sandbox is provided")
        entry = self.scripts.get(script_id)
        if entry is None:
            raise ToolError("needs_implementation", "No reviewed script registered for this identifier")
        program = self.root / safe_relative(entry["path"])
        if not program.resolve().is_relative_to(self.root.resolve()):
            raise ToolError("unsafe_path", "Reviewed script escapes the registry directory")
        raw = read_bounded(program)
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ToolError("program_changed", "Reviewed script SHA256 differs; review it again before running")
        payload = canonical_bytes(data)
        if len(payload) > MAX_BYTES:
            raise ToolError("size_limit", "Python input exceeds size limit")
        job = workspace.path("jobs/" + job_id)
        job.mkdir(parents=True, exist_ok=False)
        # Execute the reviewed bytes, rather than reopening a possibly changed source.
        frozen_program = workspace.write("jobs/" + job_id + "/program.py", raw)
        environment = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
        environment.update(PATH=str(Path(sys.executable).parent), TMP=str(job), TEMP=str(job), TMPDIR=str(job))
        with (job / "stdout.bin").open("xb") as out, (job / "stderr.bin").open("xb") as err:
            process = subprocess.Popen([sys.executable, "-I", "-B", str(frozen_program)],
                                       stdin=subprocess.PIPE, stdout=out, stderr=err,
                                       cwd=job, env=environment, shell=False)
            deadline = time.monotonic() + self.timeout
            first = True
            try:
                while True:
                    if time.monotonic() >= deadline:
                        raise ToolError("timeout", "Reviewed script exceeded its time limit")
                    if any((job / name).stat().st_size > MAX_BYTES for name in ("stdout.bin", "stderr.bin")):
                        raise ToolError("size_limit", "Reviewed script output exceeded size limit")
                    try:
                        process.communicate(payload if first else None, timeout=min(0.1, max(0.001, deadline - time.monotonic())))
                        break
                    except subprocess.TimeoutExpired:
                        first = False
                if process.returncode != 0:
                    raise ToolError("program_failed", f"Reviewed script exited with code {process.returncode}; stderr remains in private job storage")
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()
        output = strict_json(read_bounded(job / "stdout.bin"))
        if not isinstance(output, dict):
            raise ToolError("invalid_output", "Reviewed script must emit one JSON object on stdout")
        return {"output": output, "program": {"script_id": script_id, "sha256": entry["sha256"],
                "interpreter": sys.version.split()[0], "exit_code": process.returncode},
                "limitations": ["Trusted local execution only; environment sanitization and time limits are not an OS sandbox.",
                                "Output is script JSON, not a validated CalculationResult."]}
