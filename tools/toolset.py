# Consolidated tool implementations moved from assistant.py
# Avoids importing assistant to prevent cycles; uses plain prints and minimal helpers.
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import platform
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from bhumi.base_client import BaseLLMClient, LLMConfig
from tools.apply_patch import apply_patch as do_apply_patch
from tools.shell import run_shell, ShellRequest
from tools.update_plan import load_plan, update_plan as do_update_plan, PlanItem, Status
from tools.build_analyzer import analyze_build_output, pick_package_manager

# --- Minimal helpers (no ANSI formatting to avoid dependency on assistant) ---

def _info(msg: str) -> str: return msg

def _success(msg: str) -> str: return msg

def _warn(msg: str) -> str: return msg

def _error(msg: str) -> str: return msg


# --- Talk ---
async def talk_tool(content: str) -> str:
    try:
        print("\n🗣️ Assistant")
        print(content)
        return f"Spoke {len(content)} characters"
    except Exception as e:
        return f"Error speaking: {str(e)}"


# --- Planner ---
async def planner_tool(task: str, context: str = "") -> str:
    try:
        # Small terminal animation while planning
        async def _animate_planning(stop_event: asyncio.Event):
            positions = [0, 1, 2, 3]
            symbols = {"empty": "·", "tail": "░", "head": "█"}
            idx = 0
            print(); print()
            while not stop_event.is_set():
                head = positions[idx % 4]
                tail = positions[(idx - 1) % 4]
                grid = [symbols["empty"]] * 4
                grid[tail] = symbols["tail"]
                grid[head] = symbols["head"]
                line1 = f" {grid[0]} {grid[1]}  Planning…"
                line2 = f" {grid[3]} {grid[2]}"
                # Move cursor up 2 lines and redraw
                try:
                    import sys as _sys
                    _sys.stdout.write("\x1b[2A")
                    _sys.stdout.write("\x1b[2K" + line1 + "\n")
                    _sys.stdout.write("\x1b[2K" + line2 + "\n")
                    _sys.stdout.flush()
                except Exception:
                    pass
                idx += 1
                await asyncio.sleep(0.15)
            try:
                import sys as _sys
                _sys.stdout.write("\x1b[2A\x1b[2K\n\x1b[2K\n")
                _sys.stdout.flush()
            except Exception:
                pass

        import orjson
        import json as builtin_json

        # Optional Satya schema validation
        try:
            from satya import Field, Model

            class PlanningStep(Model):
                id: int = Field(description="Step ID number")
                description: str = Field(description="Step description")
                file_path: str = Field(description="Target file path")

            class PlanningPlan(Model):
                steps: list[PlanningStep] = Field(description="List of planning steps")

            satya_available = True
        except Exception:
            satya_available = False
            print(_warn("⚠️ Satya not available - using basic validation"))

        planning_config = LLMConfig(
            api_key=os.getenv("CEREBRAS_API_KEY"),
            model="cerebras/qwen-3-235b-a22b-thinking-2507",
            debug=True,
        )
        planning_client = BaseLLMClient(planning_config)

        numbers = re.findall(r"\b(\d+)\b", task.lower())
        target_count = int(numbers[0]) if numbers else 5
        folder_match = re.search(r"folder(?:\s+named|\s+called)?\s+[\"']?([^\s\"']+)[\"']?", task.lower())
        target_folder = folder_match.group(1) if folder_match else "output"

        system_prompt = f"""You are a task planning assistant. Break down the given task into {target_count} specific, actionable sequential steps.

IMPORTANT: Return ONLY a JSON object with this exact structure:
{{
  "steps": [
    {{"id": 1, "description": "Step 1 description", "file_path": "{target_folder}/file1.txt"}},
    {{"id": 2, "description": "Step 2 description", "file_path": "{target_folder}/file2.txt"}},
    ...
  ]
}}

Rules:
- Create exactly {target_count} steps
- Each step should be specific and actionable
- All file paths should be under the '{target_folder}' folder
- Focus on sequential file creation, one step at a time
- NO markdown code fences, just pure JSON"""

        user_prompt = f"""TASK: {task}
CONTEXT: {context}

Break this into {target_count} sequential steps. Each step should create one specific file.
Return only the JSON object."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        print(_info(f"🧠 Planning task with {target_count} steps..."))
        stop_event = asyncio.Event()
        anim_task = asyncio.create_task(_animate_planning(stop_event))
        try:
            response = await planning_client.completion(messages)
        finally:
            stop_event.set()
            with contextlib.suppress(Exception):
                await anim_task

        if not response or "text" not in response:
            return "❌ Error: No response from planning model"

        response_text = response["text"].strip()
        print(_info(f"🔍 Raw AI response: {response_text[:200]}..."))

        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            clean_text = "\n".join(lines[1:-1]) if len(lines) > 2 else clean_text

        plan_data: Any = None
        try:
            plan_data = orjson.loads(clean_text)
            print(_success("✅ Parsed with orjson"))
        except Exception:
            try:
                plan_data = builtin_json.loads(clean_text)
                print(_success("✅ Parsed with builtin json"))
            except Exception:
                # last resort: try to extract {...}
                import re as _re
                m = _re.search(r"\{[\s\S]*\}", clean_text)
                if not m:
                    return "❌ Error: Unable to parse planning JSON"
                try:
                    plan_data = orjson.loads(m.group(0))
                    print(_success("✅ Parsed with regex + orjson"))
                except Exception:
                    plan_data = builtin_json.loads(m.group(0))
                    print(_success("✅ Parsed with regex + builtin json"))

        if satya_available:
            try:
                # type: ignore[name-defined]
                plan = PlanningPlan(**plan_data)
                # Convert Satya/Pydantic model instances or dict-like steps into plain dicts
                steps: list[dict] = []
                for s in getattr(plan, "steps", []) or []:
                    s_dict: dict
                    try:
                        if hasattr(s, "dict") and callable(getattr(s, "dict")):
                            s_dict = s.dict()  # type: ignore[attr-defined]
                        elif hasattr(s, "model_dump") and callable(getattr(s, "model_dump")):
                            s_dict = s.model_dump()  # type: ignore[attr-defined]
                        elif isinstance(s, dict):
                            s_dict = s
                        else:
                            # Fallback to attribute access
                            s_dict = {
                                "id": getattr(s, "id", None),
                                "description": getattr(s, "description", None),
                                "file_path": getattr(s, "file_path", None),
                            }
                    except Exception:
                        s_dict = {}
                    steps.append(s_dict)
                print(_success(f"✅ Satya validation successful - {len(steps)} steps"))
            except Exception as e:
                print(_warn(f"⚠️ Satya validation failed: {e}"))
                steps = plan_data.get("steps", [])
        else:
            if "steps" not in plan_data:
                return "❌ Error: Invalid plan format - missing 'steps' array"
            steps = plan_data["steps"]

        result = f"📋 **Task Plan Created** ({len(steps)} steps)\n\n"
        result += f"**Main Task:** {task}\n"
        result += f"**Target Folder:** {target_folder}\n\n"
        result += "**Sequential Steps:**\n"
        for i, step in enumerate(steps, 1):
            desc = step.get("description", f"Step {i}")
            file_path = step.get("file_path", f"{target_folder}/file{i}.txt")
            result += f"{i}. **{desc}**\n   → File: `{file_path}`\n"
        result += "\n✅ Plan ready! Use write_file tool to execute each step sequentially."
        print(_info(f"📋 Generated plan with {len(steps)} steps"))
        return result
    except Exception as e:
        return f"❌ Error in planning: {str(e)}"


# --- Patch ---
async def apply_patch_tool(patch: str, cwd: str = ".") -> str:
    try:
        do_apply_patch(patch, cwd)
        print(_success(f"🔧 Patch applied successfully in {cwd}"))
        return f"Patch applied successfully in {cwd}"
    except Exception as e:
        return f"Error applying patch: {str(e)}"


# --- Shell wrappers ---
async def run_shell_tool(command: str, workdir: str | None = None, timeout_ms: int = 30000) -> str:
    try:
        cmd_parts = shlex.split(command)
        req = ShellRequest(command=cmd_parts, workdir=workdir, timeout_ms=timeout_ms)
        result = run_shell(req)
        output = f"Exit code: {result.exit_code}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        output += f"Duration: {result.duration_ms}ms"
        print(_info(f"💻 Shell: {command} (exit {result.exit_code})"))
        return output
    except Exception as e:
        return f"Error running command: {str(e)}"


async def update_plan_tool(steps: list | None = None, explanation: str | None = None) -> str:
    try:
        plan_path = "Muonry/.plan.json"
        if steps:
            plan_items = [
                PlanItem(step=s, status=Status.IN_PROGRESS if i == 0 else Status.PENDING)
                for i, s in enumerate(steps)
            ]
            plan = do_update_plan(plan_path, plan=plan_items)
        else:
            plan = load_plan(plan_path)
        print(_info(f"📋 Plan updated with {len(plan.items)} steps"))
        return f"Plan updated successfully with {len(plan.items)} steps"
    except Exception as e:
        return f"Error updating plan: {str(e)}"


async def smart_run_shell_tool(
    command: str,
    workdir: str | None = None,
    timeout_ms: int = 300000,
    auto_fix: bool = False,
) -> str:
    def _tail(s: str, n: int = 2000) -> str:
        if not s:
            return ""
        return s[-n:]

    def _build_install_cmd(pm: str, packages: list[str], dev: bool) -> str:
        if not packages:
            return ""
        if pm == "bun":
            base = ["bun", "add"]
            if dev:
                base.append("-D")
        elif pm == "npm":
            base = ["npm", "i"]
            if dev:
                base.append("-D")
        elif pm == "yarn":
            base = ["yarn", "add"]
            if dev:
                base.append("-D")
        else:  # pnpm or fallback
            base = ["pnpm", "add"]
            if dev:
                base.append("-D")
        return " ".join(base + packages)

    def _exec(cmd_str: str):
        parts = shlex.split(cmd_str)
        req = ShellRequest(command=parts, workdir=workdir, timeout_ms=timeout_ms)
        res = run_shell(req)
        return (res.exit_code if res.exit_code is not None else -1), res.stdout, res.stderr, res.duration_ms

    attempts: list[dict] = []

    code, out, err, dur = _exec(command)
    attempts.append({
        "phase": "initial",
        "exit_code": code,
        "duration_ms": dur,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
    })

    analysis = analyze_build_output(out or "", err or "") if code != 0 else {"issues": [], "suggestions": [], "confidence": 0.0}

    suggested_commands: list[str] = []
    if code != 0 and analysis.get("suggestions"):
        pm = pick_package_manager(workdir)
        dev_pkgs: list[str] = []
        prod_pkgs: list[str] = []
        for s in analysis["suggestions"]:
            if s.get("safe") and s.get("kind") == "install":
                data = s.get("data") or {}
                pkgs = [p for p in (data.get("packages") or []) if isinstance(p, str)]
                if not pkgs:
                    continue
                if data.get("dev"):
                    dev_pkgs.extend(pkgs)
                else:
                    prod_pkgs.extend(pkgs)
        prod_pkgs = list(dict.fromkeys(prod_pkgs))[:10]
        dev_pkgs = list(dict.fromkeys(dev_pkgs))[:10]
        if prod_pkgs:
            suggested_commands.append(_build_install_cmd(pm, prod_pkgs, dev=False))
        if dev_pkgs:
            suggested_commands.append(_build_install_cmd(pm, dev_pkgs, dev=True))

    if code != 0 and auto_fix and suggested_commands:
        for idx, fix_cmd in enumerate(suggested_commands, start=1):
            f_code, f_out, f_err, f_dur = _exec(fix_cmd)
            attempts.append({
                "phase": f"auto_fix_{idx}",
                "command": fix_cmd,
                "exit_code": f_code,
                "duration_ms": f_dur,
                "stdout_tail": _tail(f_out),
                "stderr_tail": _tail(f_err),
            })
            if f_code != 0:
                break
        r_code, r_out, r_err, r_dur = _exec(command)
        attempts.append({
            "phase": "re_run",
            "exit_code": r_code,
            "duration_ms": r_dur,
            "stdout_tail": _tail(r_out),
            "stderr_tail": _tail(r_err),
        })
        code, out, err, dur = r_code, r_out, r_err, r_dur
        analysis = analyze_build_output(out or "", err or "") if code != 0 else {"issues": [], "suggestions": [], "confidence": 0.0}

    top_errors: list[str] = []
    if err:
        lines = [ln.strip() for ln in err.splitlines() if ln.strip()]
        cand = [ln for ln in lines if any(tok in ln.lower() for tok in ["error", "err!", "failed", "fatal"])]
        top_errors = cand[:5]

    payload = {
        "status": "ok" if code == 0 else "error",
        "exit_code": code,
        "duration_ms": dur,
        "top_errors": top_errors,
        "issues": analysis.get("issues", []),
        "suggestions": analysis.get("suggestions", []),
        "suggested_commands": suggested_commands,
        "attempts": attempts,
    }
    return json.dumps(payload)


# --- File/system helpers ---
async def read_file_tool(file_path: str, start_line: int | None = None, end_line: int | None = None) -> str:
    try:
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")
        if start_line is not None or end_line is not None:
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else len(lines)
            lines = lines[start:end]
            result = "\n".join(f"{i+start+1}: {line}" for i, line in enumerate(lines))
        else:
            result = content
        print(_info(f"📖 Read file: {file_path}"))
        return f"File: {file_path}\n{'-'*40}\n{result}"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"


async def grep_tool(pattern: str, file_path: str = ".", recursive: bool = True, case_sensitive: bool = False) -> str:
    try:
        cmd = ["grep"]
        if not case_sensitive:
            cmd.append("-i")
        if recursive:
            cmd.extend(["-r", "-n"])
        else:
            cmd.append("-n")
        cmd.extend([pattern, file_path])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            output = result.stdout.strip()
            print(_info(f"🔍 Found {len(output.split('\n'))} matches for '{pattern}'"))
            return f"Search results for '{pattern}' in {file_path}:\n{'-'*40}\n{output}"
        elif result.returncode == 1:
            return f"No matches found for '{pattern}' in {file_path}"
        else:
            return f"Error searching: {result.stderr.strip()}"
    except Exception as e:
        return f"Error running grep: {str(e)}"


async def search_replace_tool(file_path: str, search_text: str, replace_text: str, all_occurrences: bool = True) -> str:
    try:
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        content = path.read_text(encoding="utf-8")
        if search_text not in content:
            return f"Text '{search_text}' not found in {file_path}"
        if all_occurrences:
            new_content = content.replace(search_text, replace_text)
            count = content.count(search_text)
        else:
            new_content = content.replace(search_text, replace_text, 1)
            count = 1
        path.write_text(new_content, encoding="utf-8")
        print(_success(f"✏️  Replaced {count} occurrence(s) in {file_path}"))
        return f"Successfully replaced {count} occurrence(s) of '{search_text}' with '{replace_text}' in {file_path}"
    except Exception as e:
        return f"Error in search/replace: {str(e)}"


async def get_system_info_tool() -> str:
    try:
        info = {
            "os": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "current_directory": os.getcwd(),
            "architecture": platform.machine(),
            "user": os.getenv("USER", "unknown"),
        }
        result = "\n".join([f"{k}: {v}" for k, v in info.items()])
        print(_info("💻 System info retrieved"))
        return f"System Information:\n{'-'*20}\n{result}"
    except Exception as e:
        return f"Error getting system info: {str(e)}"


async def quick_check_tool(kind: str, target: str = ".", max_files: int = 200, timeout_ms: int = 120000) -> str:
    import traceback
    res: dict[str, Any] = {
        "status": "ok",
        "kind": kind,
        "target": str(target),
        "checks": [],
        "errors": [],
        "suggestions": [],
        "summary": "",
    }
    try:
        p = Path(target)
        if kind.lower() == "python":
            files: list[Path] = []
            if p.is_file() and p.suffix == ".py":
                files = [p]
            else:
                for root, _, fnames in os.walk(p if p.is_dir() else p.parent):
                    for fn in fnames:
                        if fn.endswith(".py"):
                            files.append(Path(root) / fn)
                            if len(files) >= max_files:
                                break
                    if len(files) >= max_files:
                        break
            ok = 0
            for f in files:
                try:
                    src = f.read_text(encoding="utf-8")
                    import ast as _ast
                    _ast.parse(src)
                    res["checks"].append({"file": str(f), "ok": True})
                    ok += 1
                except SyntaxError as se:
                    res["checks"].append({"file": str(f), "ok": False, "error": f"SyntaxError: {se}"})
            res["summary"] = f"Python syntax OK: {ok}/{len(files)} files"
            if ok < len(files):
                res["status"] = "error"

        elif kind.lower() == "rust":
            cargo_toml = p / "Cargo.toml" if p.is_dir() else (p.parent / "Cargo.toml")
            def _exec(cmd: str):
                parts = shlex.split(cmd)
                req = ShellRequest(command=parts, workdir=str(p if p.is_dir() else p.parent), timeout_ms=timeout_ms)
                r = run_shell(req)
                return r.exit_code, r.stdout, r.stderr, r.duration_ms
            code, _, _, _ = _exec("cargo --version")
            if code == 0 and cargo_toml.exists():
                mcode, mout, merr, _ = _exec("cargo metadata -q --no-deps")
                res["checks"].append({"step": "cargo metadata", "exit_code": mcode, "stderr": (merr or "").splitlines()[-3:]})
                if mcode != 0:
                    res["status"] = "error"
                    res["errors"].append("cargo metadata failed; check Cargo.toml")
                else:
                    ccode, _, cerr, _ = _exec("cargo check -q --locked")
                    res["checks"].append({"step": "cargo check", "exit_code": ccode, "stderr": (cerr or "").splitlines()[-5:]})
                    if ccode != 0:
                        res["status"] = "error"
                        res["errors"].append("cargo check failed (may need network to fetch crates)")
                        res["suggestions"].append("Ensure dependencies are fetched: `cargo fetch` with network, then re-run")
                res["summary"] = "Rust project checked via cargo"
            else:
                files = [p] if (p.is_file() and p.suffix == ".rs") else []
                if p.is_dir():
                    for root, _, fnames in os.walk(p):
                        for fn in fnames:
                            if fn.endswith(".rs"):
                                files.append(Path(root) / fn)
                                if len(files) >= max_files:
                                    break
                        if len(files) >= max_files:
                            break
                ok = 0
                for f in files:
                    code, _, err, _ = _exec(f"rustc --emit=metadata -o /dev/null {shlex.quote(str(f))}")
                    res["checks"].append({"file": str(f), "exit_code": code, "stderr": (err or "").splitlines()[-3:]})
                    if code == 0:
                        ok += 1
                res["summary"] = f"Rust syntax OK (rustc metadata): {ok}/{len(files)} files"
                if ok < len(files):
                    res["status"] = "error"
                if not files:
                    res["suggestions"].append("Provide a Cargo.toml for project-level checks or a .rs file for single-file checks")

        elif kind.lower() == "js":
            base = p if p.is_dir() else p.parent
            tsconfig = base / "tsconfig.json"
            pkg = base / "package.json"
            used_pm = pick_package_manager(str(base))
            def _exec(cmd: str):
                parts = shlex.split(cmd)
                req = ShellRequest(command=parts, workdir=str(base), timeout_ms=timeout_ms)
                r = run_shell(req)
                return r.exit_code, r.stdout, r.stderr, r.duration_ms
            if tsconfig.exists():
                if used_pm == "bun":
                    code, _, err, _ = _exec("bun x tsc --noEmit")
                elif used_pm == "pnpm":
                    code, _, err, _ = _exec("pnpm exec tsc --noEmit")
                elif used_pm == "yarn":
                    code, _, err, _ = _exec("yarn run -s tsc --noEmit")
                else:
                    code, _, err, _ = _exec("npm run -s tsc -- --noEmit")
                res["checks"].append({"step": "tsc --noEmit", "exit_code": code, "stderr": (err or "").splitlines()[-5:]})
                if code != 0:
                    res["status"] = "error"
                    res["errors"].append("TypeScript check failed or tsc not available locally")
                    res["suggestions"].append("Install TypeScript locally: add devDep 'typescript' and run your PM's install")
                res["summary"] = "JS/TS checked via tsc"
            elif pkg.exists():
                try:
                    data = json.loads(pkg.read_text(encoding="utf-8"))
                    res["checks"].append({"step": "package.json parse", "ok": True, "name": data.get("name")})
                    res["summary"] = "package.json parsed"
                    if "typescript" in (data.get("devDependencies") or {}):
                        res["suggestions"].append("Add a tsconfig.json and run 'tsc --noEmit' for type checks")
                except Exception as je:
                    res["status"] = "error"
                    res["errors"].append(f"Invalid package.json: {je}")
            else:
                res["status"] = "error"
                res["errors"].append("No tsconfig.json or package.json found for JS project checks")
                res["suggestions"].append("Initialize a package.json and optionally a tsconfig.json")
        else:
            res["status"] = "error"
            res["errors"].append(f"Unknown kind: {kind}")
        return json.dumps(res)
    except Exception:
        res["status"] = "error"
        import traceback as _tb
        res["errors"].append(_tb.format_exc())
        return json.dumps(res)


# --- Interactive shell via PTY ---
async def interactive_shell_tool(
    command: str,
    workdir: str | None = None,
    timeout_ms: int = 600000,
    answers: list[dict] | None = None,
    input_script: str | None = None,
    env: dict | None = None,
    transcript_limit: int = 20000,
) -> str:
    import pty, os, signal, select
    start = time.time()
    answers = answers or []
    compiled = []
    for a in answers:
        try:
            pat = re.compile(a.get("expect", ".*"))
            compiled.append({"pattern": pat, "send": a.get("send", "")})
        except re.error:
            compiled.append({"pattern": re.compile(re.escape(str(a.get("expect")))), "send": a.get("send", "")})

    pid, master_fd = pty.fork()
    if pid == 0:
        try:
            if workdir:
                os.chdir(workdir)
            child_env = os.environ.copy()
            if env:
                child_env.update({str(k): str(v) for k, v in env.items()})
            os.execvpe("/bin/bash", ["bash", "-lc", command], child_env)
        except Exception:
            os._exit(127)

    transcript = bytearray()
    matched: list[int] = []
    unmatched: list[int] = [i for i in range(len(compiled))]
    sent_initial = False
    exit_code: int | None = None

    try:
        while True:
            if (time.time() - start) * 1000 > timeout_ms:
                try:
                    os.kill(pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
                time.sleep(0.2)
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                exit_code = 124
                break

            rlist, _, _ = select.select([master_fd], [], [], 0.25)
            if master_fd in rlist:
                try:
                    data = os.read(master_fd, 4096)
                    if not data:
                        break
                    transcript.extend(data)
                    if len(transcript) > transcript_limit:
                        transcript[:] = transcript[-transcript_limit:]
                    text = transcript.decode(errors="ignore")
                    for idx in list(unmatched):
                        m = compiled[idx]["pattern"].search(text)
                        if m:
                            to_send = compiled[idx]["send"] + ("\n" if not compiled[idx]["send"].endswith("\n") else "")
                            os.write(master_fd, to_send.encode())
                            matched.append(idx)
                            unmatched.remove(idx)
                except OSError:
                    break

            if not sent_initial and input_script:
                try:
                    payload = input_script
                    if not payload.endswith("\n"):
                        payload += "\n"
                    os.write(master_fd, payload.encode())
                except OSError:
                    pass
                sent_initial = True

            try:
                pid_done, status = os.waitpid(pid, os.WNOHANG)
                if pid_done == pid:
                    if os.WIFEXITED(status):
                        exit_code = os.WEXITSTATUS(status)
                    elif os.WIFSIGNALED(status):
                        exit_code = 128 + os.WTERMSIG(status)
                    break
            except ChildProcessError:
                break
    finally:
        if exit_code is None:
            try:
                _, status = os.waitpid(pid, 0)
                if os.WIFEXITED(status):
                    exit_code = os.WEXITSTATUS(status)
                elif os.WIFSIGNALED(status):
                    exit_code = 128 + os.WTERMSIG(status)
            except Exception:
                pass
        try:
            os.close(master_fd)
        except Exception:
            pass

    dur_ms = int((time.time() - start) * 1000)
    payload = {
        "status": "ok" if (exit_code == 0) else "error",
        "exit_code": exit_code if exit_code is not None else -1,
        "duration_ms": dur_ms,
        "matched": matched,
        "unmatched": unmatched,
        "transcript_tail": transcript.decode(errors="ignore")[-2000:],
    }
    return json.dumps(payload)


async def write_file_tool(file_path: str, content: str, overwrite: bool = True) -> str:
    try:
        path = Path(file_path)
        if path.exists() and not overwrite:
            return f"File {file_path} already exists and overwrite=False"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(_success(f"📝 Wrote file: {file_path}"))
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error writing file {file_path}: {str(e)}"
