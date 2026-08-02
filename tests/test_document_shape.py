"""Structural checks on the generated document.

The bug these exist for: CO4c generated its pages question-major (four copies of
Q1, then four of Q2, ...) instead of copy-major, so the PDF was four stacks of
same-numbered pages rather than four complete assessments.  Every individual
question was correct, so nothing but a shape check would have noticed.
"""

from __future__ import annotations

import re

import pytest

from pytexlib import REPO_ROOT, run_document

CO4C = REPO_ROOT / "CO4c-Fall2021-PHYS201.tex"

EXPECTED_COPIES = 4
EXPECTED_QUESTIONS_PER_COPY = 4

# One identifying phrase per question, in the order they should appear.
QUESTION_MARKERS = (
    "what is the spring constant?",
    "what is the mass of the object?",
    "How much has one of the springs been",
    "What is the mass of the object?",
)


@pytest.fixture(scope="module")
def co4c():
    return run_document(CO4C, seed=1234)


def _copies(text: str) -> list[str]:
    return [part for part in text.split(r"\newpage") if part.strip()]


def test_emits_one_page_group_per_copy(co4c):
    assert len(_copies(co4c.text)) == EXPECTED_COPIES


def test_each_copy_is_a_complete_assessment(co4c):
    """Copy-major: every copy carries the full question set, not one question."""
    for index, copy in enumerate(_copies(co4c.text), start=1):
        questions = re.findall(r"\\question", copy)
        assert len(questions) == EXPECTED_QUESTIONS_PER_COPY, (
            f"copy {index} has {len(questions)} questions, "
            f"expected {EXPECTED_QUESTIONS_PER_COPY}"
        )
        for marker in QUESTION_MARKERS:
            assert marker in copy, f"copy {index} is missing a question: {marker!r}"


def test_questions_are_numbered_from_one_in_every_copy(co4c):
    r"""Each copy resets the counter, so papers number 1-4 rather than 1-16.

    \question steps the counter before typesetting, so the reset has to be to 0.
    """
    for index, copy in enumerate(_copies(co4c.text), start=1):
        assert r"\setcounter{question}{0}" in copy, (
            f"copy {index} does not reset the question counter"
        )


def test_answer_key_has_one_entry_per_copy(co4c):
    assert len(co4c.solutions) == EXPECTED_COPIES
    for index, entry in enumerate(co4c.solutions, start=1):
        assert isinstance(entry, list), (
            f"copy {index}: expected a list of answers so the key groups per paper"
        )
        assert len(entry) == EXPECTED_QUESTIONS_PER_COPY, (
            f"copy {index}: key has {len(entry)} answers, "
            f"expected {EXPECTED_QUESTIONS_PER_COPY}"
        )


def test_copies_are_distinct(co4c):
    """Four identical papers would defeat the point of randomising."""
    copies = _copies(co4c.text)
    assert len(set(copies)) == len(copies), "duplicate copies were emitted"
