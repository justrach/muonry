from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class Issue:
    code: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    extra: Optional[Dict] = None


@dataclass
class Suggestion:
    title: str
    explanation: str
    safe: bool = False  # Safe to auto-apply
    kind: Optional[str] = None  # e.g., 'install', 'config'
    data: Optional[Dict] = None  # e.g., {packages: [...], dev: bool}


_SAFE_PKG_RE = re.compile(r"^@?[a-z0-9._-]+(?:/[a-z0-9._-]+)?$", re.IGNORECASE)


def _extract_missing_modules(text: str) -> List[str]:
    modules: List[str] = []
    patterns = [
        r"Cannot find module ['\"]([^'\"\n]+)['\"]",
        r"Module not found:.*(?:Can't resolve|Cannot resolve) ['\"]([^'\"\n]+)['\"]",
        r"Failed to resolve import ['\"]([^'\"\n]+)['\"]",
        r"error TS2307: Cannot find module ['\"]([^'\"\n]+)['\"]",
        r"Could not resolve ['\"]([^'\"\n]+)['\"] from",
        r"Cannot find package ['\"]([^'\"\n]+)['\"] imported from",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            name = m.group(1)
            if name and name not in modules:
                modules.append(name)
    # Filter out relative paths and non-package specifiers
    modules = [m for m in modules if not m.startswith(('.', '/', '#'))]
    return modules


def _extract_ts_errors(text: str) -> List[Issue]:
    issues: List[Issue] = []
    # Format: path:line:col - error TS1234: message
    for m in re.finditer(r"([^\s:][^\n:]*\.(?:ts|tsx|js|jsx)):(\d+):(\d+)\s+-\s+error\s+TS(\d+):\s+(.+)", text):
        issues.append(Issue(
            code=f"TS{m.group(4)}",
            message=m.group(5).strip(),
            file=m.group(1),
            line=int(m.group(2)),
            column=int(m.group(3)),
        ))
    # Alternate format: file(line,col): error TS1234: message
    for m in re.finditer(r"([^\s:][^\n:]*\.(?:ts|tsx|js|jsx))\((\d+),(\d+)\):\s+error\s+TS(\d+):\s+(.+)", text):
        issues.append(Issue(
            code=f"TS{m.group(4)}",
            message=m.group(5).strip(),
            file=m.group(1),
            line=int(m.group(2)),
            column=int(m.group(3)),
        ))
    return issues


def _extract_esm_cjs(text: str) -> Optional[Issue]:
    if re.search(r"Cannot use import statement outside a module|ERR_REQUIRE_ESM|require\(\) of ES Module|Must use import to load ES Module", text):
        return Issue(code="ESM_CJS_MISMATCH", message="ESM/CJS interop issue detected")
    return None


def _extract_tool_missing(text: str) -> Optional[Issue]:
    if re.search(r"\bbun: command not found\b", text):
        return Issue(code="TOOL_NOT_FOUND", message="bun is not installed")
    if re.search(r"\bnpm: command not found\b", text):
        return Issue(code="TOOL_NOT_FOUND", message="npm is not installed")
    if re.search(r"\byarn: command not found\b", text):
        return Issue(code="TOOL_NOT_FOUND", message="yarn is not installed")
    if re.search(r"\bpnpm: command not found\b", text):
        return Issue(code="TOOL_NOT_FOUND", message="pnpm is not installed")
    return None


def _extract_permission_or_port(text: str) -> List[Issue]:
    issues: List[Issue] = []
    if re.search(r"EACCES|Permission denied", text, re.IGNORECASE):
        issues.append(Issue(code="PERMISSION_DENIED", message="Permission denied (EACCES)"))
    if re.search(r"EADDRINUSE|address already in use|port is already in use", text, re.IGNORECASE):
        issues.append(Issue(code="PORT_IN_USE", message="Port already in use"))
    return issues


def analyze_build_output(stdout: str, stderr: str) -> Dict:
    text = f"{stdout}\n{stderr}" if stderr else stdout
    issues: List[Issue] = []
    suggestions: List[Suggestion] = []

    # Missing modules
    missing = _extract_missing_modules(text)
    for mod in missing:
        issues.append(Issue(code="MISSING_MODULE", message=f"Missing module '{mod}'", extra={"module": mod}))
        if _SAFE_PKG_RE.match(mod):
            suggestions.append(Suggestion(
                title=f"Install missing module {mod}",
                explanation=f"The build failed because module '{mod}' was not found.",
                safe=True,
                kind="install",
                data={"packages": [mod], "dev": False}
            ))

    # TS errors
    ts_issues = _extract_ts_errors(text)
    issues.extend(ts_issues)
    # Suggestions for missing type declarations
    for it in ts_issues:
        m = re.search(r"Cannot find module ['\"]([^'\"]+)['\"]", it.message)
        if m:
            mod = m.group(1)
            if _SAFE_PKG_RE.match(mod):
                suggestions.append(Suggestion(
                    title=f"Install types for {mod}",
                    explanation=f"TypeScript cannot find types for '{mod}'.",
                    safe=True,
                    kind="install",
                    data={"packages": [f"@types/{mod.lstrip('@').replace('/', '__')}"], "dev": True}
                ))

    # ESM/CJS
    esm = _extract_esm_cjs(text)
    if esm:
        issues.append(esm)
        suggestions.append(Suggestion(
            title="Fix ESM/CJS configuration",
            explanation="Consider setting package.json 'type' to 'module' or adjust tsconfig 'module' and imports.",
            safe=False,
            kind="config",
        ))

    # Tool missing
    tool = _extract_tool_missing(text)
    if tool:
        issues.append(tool)
        suggestions.append(Suggestion(
            title=f"Install required tool: {tool.message}",
            explanation="Install the missing tool and retry.",
            safe=False,
        ))

    # Permission / Port
    issues.extend(_extract_permission_or_port(text))

    # Confidence heuristic
    confidence = 0.3
    if any(i.code == "MISSING_MODULE" for i in issues):
        confidence = max(confidence, 0.85)
    if any(i.code.startswith("TS") for i in issues):
        confidence = max(confidence, 0.7)
    if any(i.code in ("ESM_CJS_MISMATCH", "TOOL_NOT_FOUND") for i in issues):
        confidence = max(confidence, 0.6)

    # Serialize to plain dicts
    out = {
        "issues": [
            {
                "code": i.code,
                "message": i.message,
                **({"file": i.file} if i.file else {}),
                **({"line": i.line} if i.line is not None else {}),
                **({"column": i.column} if i.column is not None else {}),
                **({"extra": i.extra} if i.extra else {}),
            }
            for i in issues
        ],
        "suggestions": [
            {
                "title": s.title,
                "explanation": s.explanation,
                "safe": s.safe,
                **({"kind": s.kind} if s.kind else {}),
                **({"data": s.data} if s.data else {}),
            }
            for s in suggestions
        ],
        "confidence": round(confidence, 2),
    }
    return out


def pick_package_manager(cwd: Optional[str]) -> str:
    """Pick a JS package manager based on lockfiles or availability order."""
    base = Path(cwd or os.getcwd())
    if (base / "bun.lockb").exists():
        return "bun"
    if (base / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (base / "yarn.lock").exists():
        return "yarn"
    if (base / "package-lock.json").exists():
        return "npm"
    # Fallback preference
    return "bun"
