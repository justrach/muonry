from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class HunkLine:
    tag: str  # ' ', '-', '+'
    text: str


@dataclass
class Hunk:
    header: Optional[str]
    lines: List[HunkLine]


@dataclass
class AddOp:
    to: str
    content: str


@dataclass
class DeleteOp:
    from_path: str


@dataclass
class UpdateOp:
    from_path: str
    to_path: Optional[str]
    hunks: List[Hunk]


FileOp = Tuple[str, object]


def apply_patch(patch: str, cwd: str) -> None:
    ops = _parse_patch(patch)
    root = Path(cwd).resolve()
    for kind, op in ops:
        if kind == "add":
            target = _resolve_safe(root, Path(op.to))
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_atomic(target, op.content)
        elif kind == "delete":
            target = _resolve_safe(root, Path(op.from_path))
            target.unlink()
        elif kind == "update":
            src = _resolve_safe(root, Path(op.from_path))
            dst = _resolve_safe(root, Path(op.to_path)) if op.to_path else src
            original = src.read_text(encoding="utf-8")
            updated = _apply_hunks(original, op.hunks)
            dst.parent.mkdir(parents=True, exist_ok=True)
            _write_atomic(dst, updated)
            if dst != src:
                src.unlink()
        else:
            raise ValueError(f"unknown op: {kind}")


def _parse_patch(patch: str) -> List[FileOp]:
    lines = patch.replace("\r\n", "\n").split("\n")
    i = 0

    def next_line() -> Optional[str]:
        nonlocal i
        if i < len(lines):
            res = lines[i]
            i += 1
            return res
        return None

    def peek() -> Optional[str]:
        return lines[i] if i < len(lines) else None

    if next_line() != "**_ Begin Patch":
        raise ValueError("Missing begin envelope")

    ops: List[FileOp] = []
    while True:
        line = peek()
        if line is None:
            raise ValueError("Unexpected EOF in patch")
        if line == "_** End Patch":
            next_line()
            break
        if line.startswith("*** Add File: "):
            next_line()
            to = line[len("*** Add File: ") :].strip()
            buf: List[str] = []
            while True:
                l = peek()
                if l is None or l.startswith("*** ") or l == "_** End Patch":
                    break
                if not l.startswith("+"):
                    raise ValueError(f"Add File content must start with '+': {l}")
                buf.append(l[1:])
                next_line()
            content = "\n".join(buf) + ("\n" if buf else "")
            ops.append(("add", AddOp(to=to, content=content)))
        elif line.startswith("*** Delete File: "):
            next_line()
            frm = line[len("*** Delete File: ") :].strip()
            ops.append(("delete", DeleteOp(from_path=frm)))
        elif line.startswith("*** Update File: "):
            next_line()
            frm = line[len("*** Update File: ") :].strip()
            to_path: Optional[str] = None
            if peek() and peek().startswith("_** Move to: "):
                mv = next_line()
                assert mv is not None
                to_path = mv[len("_** Move to: ") :].strip()
            hunks: List[Hunk] = []
            while peek() and peek().startswith("@@"):
                header = next_line()[2:].strip() or None  # type: ignore[index]
                hlines: List[HunkLine] = []
                while True:
                    l = peek()
                    if l is None or l.startswith("@@") or l.startswith("*** ") or l == "_** End Patch":
                        break
                    if l.startswith("*** End of File"):
                        next_line()
                        break
                    if not l or l[0] not in {" ", "-", "+"}:
                        raise ValueError(f"Invalid hunk line: {l}")
                    hlines.append(HunkLine(tag=l[0], text=l[1:]))
                    next_line()
                hunks.append(Hunk(header=header, lines=hlines))
            if not hunks:
                raise ValueError("Update File requires at least one hunk")
            ops.append(("update", UpdateOp(from_path=frm, to_path=to_path, hunks=hunks)))
        else:
            raise ValueError(f"Unexpected line in patch: {line}")
    return ops


def _apply_hunks(original_text: str, hunks: List[Hunk]) -> str:
    orig = _split_keep_nl(original_text)
    out: List[str] = []
    cursor = 0
    for h in hunks:
        expected: List[str] = []
        produced: List[str] = []
        for hl in h.lines:
            if hl.tag == " ":
                expected.append(hl.text + "\n")
                produced.append(hl.text + "\n")
            elif hl.tag == "-":
                expected.append(hl.text + "\n")
            elif hl.tag == "+":
                produced.append(hl.text + "\n")
        idx = _find_subseq(orig, expected, cursor)
        if idx < 0:
            ctx = f" (header: {h.header})" if h.header else ""
            raise ValueError(f"Hunk did not match original{ctx}")
        out.extend(orig[cursor:idx])
        out.extend(produced)
        cursor = idx + len(expected)
    out.extend(orig[cursor:])
    return "".join(out)


def _find_subseq(haystack: List[str], needle: List[str], start: int) -> int:
    for i in range(start, len(haystack) - len(needle) + 1):
        for j in range(len(needle)):
            if haystack[i + j] != needle[j]:
                break
        else:
            return i
    return -1


def _split_keep_nl(text: str) -> List[str]:
    if not text:
        return []
    text = text.replace("\r\n", "\n")
    parts = text.split("\n")
    out: List[str] = []
    for i in range(len(parts) - 1):
        out.append(parts[i] + "\n")
    if parts[-1] != "":
        out.append(parts[-1])
    return out


def _resolve_safe(root: Path, target: Path) -> Path:
    abs_path = (root / target).resolve()
    if abs_path != root and not str(abs_path).startswith(str(root) + os.sep):
        raise ValueError(f"Refusing to write outside workspace: {target}")
    return abs_path


def _write_atomic(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".tmp.{target.name}.", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        shutil.move(tmp, target)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except OSError:
            pass
