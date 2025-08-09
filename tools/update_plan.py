from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional


class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class PlanItem:
    step: str
    status: Status


@dataclass
class Plan:
    items: List[PlanItem]

    def validate(self) -> None:
        if not self.items:
            return
        num_in_progress = sum(1 for i in self.items if i.status == Status.IN_PROGRESS)
        num_completed = sum(1 for i in self.items if i.status == Status.COMPLETED)
        if num_completed == len(self.items):
            # All done; zero in_progress allowed
            return
        if num_in_progress != 1:
            raise ValueError(
                f"Plan must have exactly one in_progress step until completion; found {num_in_progress}"
            )

    def to_json(self) -> str:
        return json.dumps({
            "plan": [
                {"step": it.step, "status": it.status.value} for it in self.items
            ]
        }, indent=2)

    @staticmethod
    def from_json(data: str) -> "Plan":
        obj = json.loads(data)
        items = [
            PlanItem(step=e["step"], status=Status(e["status"])) for e in obj.get("plan", [])
        ]
        return Plan(items=items)


def _write_atomic_json(target: Path, content: str) -> None:
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


def load_plan(path: str | os.PathLike[str]) -> Plan:
    p = Path(path)
    if not p.exists():
        return Plan(items=[])
    return Plan.from_json(p.read_text(encoding="utf-8"))


def save_plan(plan: Plan, path: str | os.PathLike[str]) -> None:
    plan.validate()
    p = Path(path)
    _write_atomic_json(p, plan.to_json())


def update_plan(
    path: str | os.PathLike[str],
    *,
    plan: Optional[List[PlanItem]] = None,
    explanation: Optional[str] = None,  # accepted but unused; kept for API parity
) -> Plan:
    """
    Replace or set the plan content and persist it to JSON, enforcing validation.

    Example:
        new = [
            PlanItem("Explore codebase", Status.COMPLETED),
            PlanItem("Implement feature", Status.IN_PROGRESS),
            PlanItem("Write tests", Status.PENDING),
        ]
        update_plan(".plan.json", plan=new)
    """
    current = load_plan(path)
    if plan is not None:
        current = Plan(items=list(plan))
    save_plan(current, path)
    return current


# Convenience helpers matching the algorithm description

def mark_step_completed(path: str | os.PathLike[str], step_index: int) -> Plan:
    cur = load_plan(path)
    if step_index < 0 or step_index >= len(cur.items):
        raise IndexError("step_index out of range")
    cur.items[step_index].status = Status.COMPLETED
    # Promote first pending to in_progress if any remains
    remaining = [i for i in cur.items if i.status != Status.COMPLETED]
    if remaining:
        # ensure exactly one in_progress among remaining
        for it in cur.items:
            if it.status == Status.IN_PROGRESS:
                it.status = Status.PENDING
        remaining[0].status = Status.IN_PROGRESS
    save_plan(cur, path)
    return cur


def create_initial_plan(path: str | os.PathLike[str], steps: List[str]) -> Plan:
    items: List[PlanItem] = []
    for idx, s in enumerate(steps):
        status = Status.IN_PROGRESS if idx == 0 and steps else Status.PENDING
        items.append(PlanItem(step=s, status=status))
    plan = Plan(items=items)
    save_plan(plan, path)
    return plan
