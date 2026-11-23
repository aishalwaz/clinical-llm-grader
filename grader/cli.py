"""Command-line entry point.

Example:
    python -m grader.cli examples/rubrics/community_acquired_pneumonia.json \
        examples/responses/cap_good.txt --format text
"""

import argparse
import sys
from pathlib import Path

from .rubric import load_rubric
from .scorer import grade
from .report import to_text, to_markdown, to_json

FORMATS = {"text": to_text, "markdown": to_markdown, "json": to_json}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Grade an AI clinical answer against a rubric.")
    parser.add_argument("rubric", help="path to a rubric JSON file")
    parser.add_argument("answers", nargs="+", help="one or more text files containing AI answers")
    parser.add_argument("--format", choices=FORMATS, default="text", help="output format")
    args = parser.parse_args(argv)

    rubric = load_rubric(args.rubric)
    all_passed = True
    for path in args.answers:
        answer = Path(path).read_text(encoding="utf-8")
        report = grade(rubric, answer)
        print(f"=== {path} ===")
        print(FORMATS[args.format](report))
        print()
        all_passed = all_passed and report.passed

    # Exit code 0 if every answer passed, 1 otherwise (useful in automated checks).
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
