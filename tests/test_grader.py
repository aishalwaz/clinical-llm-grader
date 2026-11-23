"""Tests for the clinical grader. Run with:  python -m pytest"""

import json
from pathlib import Path

import pytest

from grader import grade, load_rubric
from grader.rubric import Criterion, Rubric, validate
from grader.scorer import find_concept, normalise
from grader.report import to_json, to_markdown

ROOT = Path(__file__).resolve().parent.parent
CAP = ROOT / "examples/rubrics/community_acquired_pneumonia.json"
DKA = ROOT / "examples/rubrics/diabetic_ketoacidosis.json"


def read(name):
    return (ROOT / "examples/responses" / name).read_text(encoding="utf-8")


# --- Concept matching and negation -------------------------------------

def test_plain_mention_is_found():
    assert find_concept(normalise("Start amoxicillin now."), "amoxicillin") == (True, False)


def test_negated_mention_does_not_count():
    # "do not stop the insulin" must NOT trigger the "stop the insulin" red flag
    found, negated = find_concept(normalise("Do not stop the insulin yet."), "stop the insulin")
    assert found and negated


def test_whole_words_only():
    # "cxr" should not match inside an unrelated longer word
    assert find_concept(normalise("cxrays"), "cxr") == (False, False)


# --- Grading the example answers ----------------------------------------

def test_good_pneumonia_answer_passes():
    report = grade(load_rubric(CAP), read("cap_good.txt"))
    assert report.passed and report.percentage == 100.0


def test_unsafe_pneumonia_answer_fails_on_safety():
    report = grade(load_rubric(CAP), read("cap_unsafe.txt"))
    assert report.critical_failure
    assert not report.passed
    assert report.score == 0  # penalties never push the score below zero


def test_good_dka_answer_passes_despite_negated_red_flag_phrase():
    report = grade(load_rubric(DKA), read("dka_good.txt"))
    assert report.passed
    assert not report.critical_failure


def test_partial_answer_gets_partial_credit():
    answer = "Calculate CURB-65 and request a chest X-ray."
    report = grade(load_rubric(CAP), answer)
    assert report.score == 5          # 3 for severity score + 2 for chest X-ray
    assert not report.passed          # 5/14 is below the 70% pass mark


# --- Rubric validation -------------------------------------------------

def make(criteria):
    return Rubric(title="t", question="q", pass_mark=70, criteria=criteria)


def test_rejects_duplicate_ids():
    c = Criterion("a", "d", "cat", "required", 1, ["x"])
    with pytest.raises(ValueError, match="Duplicate"):
        validate(make([c, c]))


def test_rejects_criterion_without_concepts():
    with pytest.raises(ValueError, match="concept"):
        validate(make([Criterion("a", "d", "cat", "required", 1, [])]))


def test_rejects_rubric_with_only_red_flags():
    with pytest.raises(ValueError, match="required"):
        validate(make([Criterion("a", "d", "cat", "red_flag", 1, ["x"])]))


# --- Output formats ----------------------------------------------------

def test_json_and_markdown_outputs():
    report = grade(load_rubric(CAP), read("cap_good.txt"))
    data = json.loads(to_json(report))
    assert data["percentage"] == 100.0
    assert "| Criterion |" in to_markdown(report)
