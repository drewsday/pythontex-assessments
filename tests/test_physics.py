"""Check every answer key against an independent re-derivation.

The physics lives in `physics.py`, keyed by question type; this module walks each
document, works out which questions it printed, and compares the recomputed
answers against what randassign recorded.

Values are matched against the units the key reports them in as well as their
magnitude, because a right number carrying the wrong unit is still a wrong
answer -- and is exactly the defect that reached students in CO4c.
"""

from __future__ import annotations

import math
import re

import pytest

from physics import classify, split_questions
from pytexlib import calls_addsoln, doc_id, documents_with_code

RTOL = 0.01  # keys are formatted to three significant figures

# Assessments whose answers are not re-derivable from what they print.  Keep
# this list short: every entry is a key nobody checks.
FIGURE_DRIVEN_CO1A = "CO1a - Graphs - v1 - Fall 2026 - Physics 201.tex"

# `\SI{value}{unit}` for dimensional answers and `\num{value}` for dimensionless
# ones. The unit group is optional so a malformed one-argument \SI still consumes
# its slot rather than shifting everything after it.
_KEY_ENTRY = re.compile(
    r"\\(SI|num)\{(-?\d*\.?\d+(?:[eE][+-]?\d+)?)\}(?:\{([^{}]*)\})?"
)


def key_stream(result) -> list[tuple[float, str | None]]:
    """Every value the answer key reports, in order, with its unit."""
    return [v for entry in solution_entries(result) for v in entry]


def solution_entries(result) -> list[list[tuple[float, str | None]]]:
    """The key grouped by addsoln call.

    Grouping matters: most documents call addsoln once per question, so the
    groups line up with the questions and a wrong count can be reported against
    the question it belongs to instead of silently shifting every value after it.
    """
    entries = []
    for soln in result.solutions:
        parts = soln if isinstance(soln, (list, tuple)) else [soln]
        values = []
        for part in parts:
            for macro, value, unit in _KEY_ENTRY.findall(str(part)):
                # \num carries no unit by construction; represent that as "" so
                # a solver can assert an answer is deliberately dimensionless.
                resolved = "" if macro == "num" else (unit if unit else None)
                values.append((float(value), resolved))
        entries.append(values)
    return entries


def _matches(reported: float, expected: float) -> bool:
    return math.isclose(reported, expected, rel_tol=RTOL, abs_tol=1e-9)


def _compare(name: str, expected, reported) -> list[str]:
    """Match one question's recomputed answers against the values reported."""
    problems = []
    if len(reported) != len(expected):
        problems.append(
            f"[{name}] key reports {len(reported)} value(s), "
            f"the statement calls for {len(expected)} "
            f"({', '.join(label for label, _, _ in expected)})"
        )
    for (label, value, unit), (got, got_unit) in zip(expected, reported):
        if not _matches(got, value):
            problems.append(
                f"[{name}] {label}: key says {got:g}, recomputed {value:g}"
            )
        elif unit is not None and got_unit != unit:
            problems.append(
                f"[{name}] {label}: value correct but unit is {got_unit!r}, "
                f"expected {unit!r}"
            )
    return problems


def check(result) -> list[str]:
    """Compare a document's key against the recomputed answers."""
    problems: list[str] = []
    questions = []

    for statement in split_questions(result.text):
        question_type = classify(statement)
        if question_type is None:
            problems.append(f"unrecognised question: {statement[:70]!r}")
            continue
        if question_type.solve is None:
            continue  # discussion question, contributes nothing to the key
        try:
            questions.append((question_type.name, question_type.solve(statement)))
        except (LookupError, AttributeError, ValueError, ZeroDivisionError) as exc:
            problems.append(f"[{question_type.name}] could not re-derive: {exc}")

    entries = solution_entries(result)

    if len(questions) == len(entries):
        # One addsoln per question: compare group by group, so a count mismatch
        # is attributed to its own question rather than shifting the rest.
        for (name, expected), reported in zip(questions, entries):
            problems.extend(_compare(name, expected, reported))
        return problems

    # Otherwise the grouping does not line up with the questions -- CO4c records
    # one entry per copy covering four questions -- so fall back to a flat
    # stream in printed order.
    reported = key_stream(result)
    position = 0
    for name, expected in questions:
        slice_ = reported[position : position + len(expected)]
        problems.extend(_compare(name, expected, slice_))
        position += len(expected)
    if position < len(reported):
        problems.append(
            f"key has {len(reported) - position} value(s) no question accounts for"
        )
    return problems


def test_answer_key_matches_independent_recomputation(
    document, seeds, runs_cache, check_known
):
    """`document` is parametrised over every document with code by conftest."""
    if not calls_addsoln(document):
        pytest.skip("records no answer key")
    if doc_id(document) == "simple_example.tex":
        pytest.skip("emits no problem statement; covered by its own test below")
    if doc_id(document) == FIGURE_DRIVEN_CO1A:
        # CO1a states its questions in static LaTeX and injects values with
        # \py{...}, so nothing reaches stdout for split_questions to cut up.
        # The values its answers derive from -- strobe positions, the scooters'
        # velocity profiles -- live in the generated figures rather than in the
        # prose, so no text-scraping solver can read them back off the page.
        # Its six key entries are therefore NOT verified by this suite.
        pytest.skip("figure-driven; answers cannot be re-derived from printed text")
    check_known("physics")

    failures = []
    for seed in seeds:
        for problem in check(runs_cache(document, seed)):
            failures.append(f"seed {seed}: {problem}")

    distinct = list(dict.fromkeys(failures))
    assert not failures, "{} disagreement(s) over {} seeds:\n  {}".format(
        len(failures), len(seeds), "\n  ".join(distinct[:8])
    )


def test_simple_example_answer_is_a_reachable_hypotenuse(seeds, runs_cache):
    """simple_example prints no statement, so verify the answer is attainable.

    It draws two integers in 1..10 and reports the hypotenuse, so the answer must
    be one of the finitely many values that construction can produce.
    """
    from pytexlib import REPO_ROOT

    reachable = {
        round(math.hypot(a, b), 2) for a in range(1, 11) for b in range(1, 11)
    }
    document = REPO_ROOT / "simple_example.tex"

    failures = []
    for seed in seeds:
        for entry in runs_cache(document, seed).flat_solutions:
            match = re.fullmatch(r"(\d+\.\d+)~cm", entry.strip())
            if match is None:
                failures.append(f"seed {seed}: {entry!r} is not a length in cm")
                continue
            value = float(match.group(1))
            if value not in reachable:
                failures.append(f"seed {seed}: {value} is not a reachable hypotenuse")

    assert not failures, "\n  ".join(failures[:5])


def test_every_document_with_a_key_is_checked():
    """Coverage ratchet: a key nobody re-derives is a key nobody verifies.

    Uses the AST-based `calls_addsoln`, so documents whose addsoln calls are
    commented out are not counted -- they have no key to check.
    """
    keyed = [p for p in documents_with_code() if calls_addsoln(p)]
    assert keyed, "expected at least one document with an answer key"

    # Every question a keyed document prints must be recognised by the registry,
    # otherwise its answers go unverified. This is what fails when a new
    # assessment lands without a solver.
    from pytexlib import run_document

    unrecognised = []
    for path in keyed:
        if doc_id(path) == "simple_example.tex":
            continue  # prints no statement; covered by its own test
        result = run_document(path, seed=0)
        for statement in split_questions(result.text):
            if classify(statement) is None:
                unrecognised.append(f"{doc_id(path)}: {statement[:60]!r}")

    assert not unrecognised, "questions with no solver:\n  " + "\n  ".join(
        unrecognised[:10]
    )
