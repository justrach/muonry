from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class ShellRequest:
    command: List[str]
    workdir: Optional[str] = None
    timeout_ms: int = 10 * 60_000
    env: Optional[Dict[str, str]] = None
    with_escalated_permissions: bool = False
    justification: Optional[str] = None


@dataclass
class ShellResult:
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int


ApprovalFn = Callable[[str], bool]


def run_shell(req: ShellRequest, approve: Optional[ApprovalFn] = None) -> ShellResult:
    if not req.command:
        raise ValueError("command must be a non-empty list")
    if req.with_escalated_permissions:
        if not req.justification:
            raise ValueError("justification required for escalated permissions")
        ok = approve(req.justification) if approve else True
        if not ok:
            raise PermissionError("Escalation denied")

    env = os.environ.copy()
    if req.env:
        env.update({k: v for k, v in req.env.items() if v is not None})

    start = time.time()

    proc = subprocess.Popen(
        req.command,
        cwd=req.workdir or os.getcwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout_chunks: List[str] = []
    stderr_chunks: List[str] = []

    def consume(stream, sink: List[str]):
        for chunk in iter(lambda: stream.readline(), ""):
            sink.append(chunk)

    t_out = threading.Thread(target=consume, args=(proc.stdout, stdout_chunks))  # type: ignore[arg-type]
    t_err = threading.Thread(target=consume, args=(proc.stderr, stderr_chunks))  # type: ignore[arg-type]
    t_out.start(); t_err.start()

    def kill_after_timeout():
        time.sleep(req.timeout_ms / 1000)
        if proc.poll() is None:
            try:
                proc.terminate()
                time.sleep(2)
                if proc.poll() is None:
                    proc.kill()
            except ProcessLookupError:
                pass

    killer = threading.Thread(target=kill_after_timeout)
    killer.daemon = True
    killer.start()

    exit_code = proc.wait()
    t_out.join(); t_err.join()
    duration = int((time.time() - start) * 1000)

    return ShellResult(
        exit_code=exit_code,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
        duration_ms=duration,
    )
