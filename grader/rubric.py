"""Load and check clinical grading rubrics.

A rubric is a JSON file that lists the criteria an AI answer should meet.
Each criterion says which concepts earn credit, how many points it is worth,
and whether it is a red flag (something unsafe that should never appear).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

# The two kinds of criterion the grader understands.
REQUIRED = "required"   # the answer should mention this to earn points
RED_FLAG = "red_flag"   # the answer must NOT recommend this; it loses points if it does


@dataclass
class Criterion:
    """One line of a rubric, for example 'Recommends a chest X-ray'."""
    id: str                      # short unique name, e.g. "cxr"
    description: str             # what a human reviewer would read
    category: str                # e.g. "diagnosis", "safety", "management"
    kind: str                    # REQUIRED or RED_FLAG
    points: float                # credit earned (or lost, for a red flag)
    concepts: list = field(default_factory=list)  # phrases that count as a match
    critical: bool = False       # a critical red flag fails the answer outright


@dataclass
class Rubric:
    """A full rubric for one clinical question."""
    title: str
    question: str
    pass_mark: float             # percentage needed to pass, e.g. 70
    criteria: list               # list of Criterion objects

    @property
    def max_points(self) -> float:
        # Only required criteria add to the maximum score.
        return sum(c.points for c in self.criteria if c.kind == REQUIRED)


def load_rubric(path) -> Rubric:
    """Read a rubric JSON file and turn it into a Rubric object."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    criteria = [Criterion(**item) for item in data["criteria"]]
    rubric = Rubric(
        title=data["title"],
        question=data["question"],
        pass_mark=float(data.get("pass_mark", 70)),
        criteria=criteria,
    )
    validate(rubric)
    return rubric


def validate(rubric: Rubric) -> None:
    """Catch common rubric-writing mistakes before grading starts."""
    seen = set()
    for c in rubric.criteria:
        # Every criterion needs a unique id so results can be traced back.
        if c.id in seen:
            raise ValueError(f"Duplicate criterion id: {c.id}")
        seen.add(c.id)
        # Only the two known kinds are allowed.
        if c.kind not in (REQUIRED, RED_FLAG):
            raise ValueError(f"Criterion {c.id}: kind must be '{REQUIRED}' or '{RED_FLAG}'")
        # A criterion with no concepts can never be matched, which is unfair.
        if not c.concepts:
            raise ValueError(f"Criterion {c.id}: add at least one concept phrase")
        # Points must be positive; red flags subtract them later.
        if c.points <= 0:
            raise ValueError(f"Criterion {c.id}: points must be greater than 0")
    if rubric.max_points == 0:
        raise ValueError("Rubric needs at least one required criterion")
