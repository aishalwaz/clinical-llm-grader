"""Turn a grade report into readable text, Markdown or JSON."""

import json
from dataclasses import asdict

from .scorer import GradeReport
from .rubric import RED_FLAG


def to_text(report: GradeReport) -> str:
    """A plain-text summary for the terminal."""
    verdict = "PASS" if report.passed else "FAIL"
    lines = [
        f"Rubric: {report.rubric_title}",
        f"Score: {report.score:g} / {report.max_score:g} ({report.percentage}%)  ->  {verdict}",
    ]
    if report.critical_failure:
        lines.append("Critical safety failure: the answer contains unsafe advice.")
    lines.append("")
    # Show each criterion with a tick, a cross or a warning sign.
    for r in report.results:
        if r.kind == RED_FLAG:
            mark = "!!" if r.matched else "ok"
            note = f"(found: '{r.evidence}')" if r.matched else ""
            lines.append(f"[{mark}] RED FLAG  {r.description} {note}".rstrip())
        else:
            mark = "x" if r.matched else " "
            lines.append(f"[{mark}] {r.points_awarded:g}/{r.points_available:g}  {r.description}")
    lines.append("")
    lines.append("By category:")
    for cat, (got, avail) in report.by_category().items():
        lines.append(f"  {cat}: {got:g} / {avail:g}")
    return "\n".join(lines)


def to_markdown(report: GradeReport) -> str:
    """A Markdown table, handy for pasting into a review document."""
    verdict = "✅ Pass" if report.passed else "❌ Fail"
    out = [
        f"## {report.rubric_title}",
        "",
        f"**Score:** {report.score:g} / {report.max_score:g} ({report.percentage}%) — {verdict}",
        "",
        "| Criterion | Category | Type | Points | Evidence |",
        "|---|---|---|---|---|",
    ]
    for r in report.results:
        out.append(f"| {r.description} | {r.category} | {r.kind} | {r.points_awarded:g} | {r.evidence or '—'} |")
    if report.critical_failure:
        out += ["", "> ⚠️ Critical safety failure: unsafe advice was found."]
    return "\n".join(out)


def to_json(report: GradeReport) -> str:
    """Machine-readable output for further analysis (e.g. in pandas)."""
    return json.dumps(asdict(report), indent=2)
