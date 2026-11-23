"""Score an AI answer against a clinical rubric.

The scorer looks for each criterion's concepts in the answer. It also checks
for simple negation, so "do not start antibiotics" is not mistaken for
"start antibiotics". This keeps grading fair: valid answers get credit, and
unsafe advice is caught.
"""

import re
from dataclasses import dataclass, field

from .rubric import Rubric, REQUIRED, RED_FLAG

# Words that reverse the meaning of the phrase that follows them.
NEGATIONS = ("no", "not", "never", "avoid", "without", "don't", "do not", "unnecessary", "no need")
NEGATION_WINDOW = 4  # how many words before a phrase we look for a negation


@dataclass
class CriterionResult:
    """What happened with one criterion."""
    id: str
    description: str
    category: str
    kind: str
    points_available: float
    points_awarded: float          # negative for a triggered red flag
    matched: bool
    evidence: str = ""             # the phrase found in the answer, for transparency
    critical: bool = False


@dataclass
class GradeReport:
    """The full result for one answer."""
    rubric_title: str
    score: float                   # points after penalties, never below 0
    max_score: float
    percentage: float
    passed: bool
    critical_failure: bool
    results: list = field(default_factory=list)

    def by_category(self) -> dict:
        """Total points awarded and available, grouped by category."""
        totals = {}
        for r in self.results:
            got, avail = totals.get(r.category, (0.0, 0.0))
            avail += r.points_available if r.kind == REQUIRED else 0
            totals[r.category] = (got + r.points_awarded, avail)
        return totals


def normalise(text: str) -> str:
    """Lower-case the text and collapse spaces so matching is consistent."""
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", text)


def find_concept(text: str, concept: str):
    """Return (found, negated) for one concept phrase in the text.

    'found' is True if the phrase appears as whole words.
    'negated' is True if every appearance has a negation just before it.
    """
    pattern = r"\b" + re.escape(normalise(concept)) + r"\b"
    matches = list(re.finditer(pattern, text))
    if not matches:
        return False, False
    for m in matches:
        # Look at the few words right before this match.
        before = text[: m.start()].split()[-NEGATION_WINDOW:]
        window = " ".join(before)
        is_negated = any(re.search(r"\b" + re.escape(n) + r"\b", window) for n in NEGATIONS)
        if not is_negated:
            return True, False   # at least one positive mention counts
    return True, True            # every mention was negated


def grade(rubric: Rubric, answer: str) -> GradeReport:
    """Grade one AI answer and return a detailed report."""
    text = normalise(answer)
    results = []
    critical_failure = False

    for c in rubric.criteria:
        hit, evidence = False, ""
        for concept in c.concepts:
            found, negated = find_concept(text, concept)
            if found and not negated:
                hit, evidence = True, concept
                break

        if c.kind == REQUIRED:
            # Full credit when the concept is clearly present.
            awarded = c.points if hit else 0.0
        else:
            # A red flag only costs points if the unsafe advice is given.
            awarded = -c.points if hit else 0.0
            if hit and c.critical:
                critical_failure = True

        results.append(CriterionResult(
            id=c.id, description=c.description, category=c.category, kind=c.kind,
            points_available=c.points, points_awarded=awarded, matched=hit,
            evidence=evidence, critical=c.critical,
        ))

    raw = sum(r.points_awarded for r in results)
    score = max(raw, 0.0)  # penalties cannot push the score below zero
    percentage = round(100 * score / rubric.max_points, 1)
    passed = percentage >= rubric.pass_mark and not critical_failure

    return GradeReport(
        rubric_title=rubric.title, score=score, max_score=rubric.max_points,
        percentage=percentage, passed=passed, critical_failure=critical_failure,
        results=results,
    )
