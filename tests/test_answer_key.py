"""Properties of the answer key.

A wrong or degenerate key is the worst failure mode in this repository: unlike a
broken build it does not announce itself, it just marks students incorrectly.
"""

from __future__ import annotations

import math

from pytexlib import calls_addsoln, si_values


def _uses_addsoln(document) -> bool:
    return calls_addsoln(document)


def test_recorded_key_is_not_empty(document, seeds, runs_cache, check_known):
    """A document that calls addsoln must actually produce answers.

    Without this the checks below pass vacuously on documents whose key never
    gets written -- which is the state several assessments are in, with their
    addsoln calls commented out from an earlier draft.
    """
    if not _uses_addsoln(document):
        return
    check_known("key_not_empty")

    empty = [seed for seed in seeds[:5] if not runs_cache(document, seed).flat_solutions]
    assert not empty, f"calls addsoln but recorded no answers on seeds {empty}"


def test_solutions_are_latex_strings(document, seeds, runs_cache, check_known):
    """addsoln() should receive formatted LaTeX, or a list of it, not raw numbers.

    A bare float reaches the key without units and without rounding control.
    """
    if not _uses_addsoln(document):
        return
    check_known("solution_types")

    offenders = []
    for seed in seeds[:5]:
        for soln in runs_cache(document, seed).solutions:
            if isinstance(soln, (list, tuple)):
                bad = [x for x in soln if not isinstance(x, str)]
                if bad:
                    offenders.append(f"seed {seed}: list containing {type(bad[0]).__name__}")
            elif not isinstance(soln, str):
                offenders.append(f"seed {seed}: {type(soln).__name__}")

    assert not offenders, "non-string solutions:\n  " + "\n  ".join(dict.fromkeys(offenders))


def test_answer_values_are_finite(document, seeds, runs_cache, check_known):
    """NaN or inf in a key means a divide-by-zero slipped through."""
    if not _uses_addsoln(document):
        return
    check_known("finite_answers")

    offenders = []
    for seed in seeds:
        for text in runs_cache(document, seed).flat_solutions:
            if "nan" in text.lower() or "inf" in text.lower():
                offenders.append(f"seed {seed}: {text[:60]}")
            for value in si_values(text):
                if not math.isfinite(value):
                    offenders.append(f"seed {seed}: {value}")

    assert not offenders, "non-finite answers:\n  " + "\n  ".join(offenders[:5])


def test_no_degenerate_answers(document, seeds, runs_cache, check_known):
    """An answer of exactly zero usually means the problem collapsed.

    Randomised parameters can coincide in ways that trivialise a question -- two
    batteries drawing the same voltage, say, so no current flows.  The paper
    still prints, so nothing catches this except a check on the key.
    """
    if not _uses_addsoln(document):
        return
    check_known("no_degenerate_answers")

    offenders = []
    for seed in seeds:
        for text in runs_cache(document, seed).flat_solutions:
            for value in si_values(text):
                if value == 0:
                    offenders.append(f"seed {seed}: zero answer in {text[:50]!r}")

    assert not offenders, "degenerate answers on {} of {} seeds:\n  {}".format(
        len({o.split(":")[0] for o in offenders}),
        len(seeds),
        "\n  ".join(offenders[:5]),
    )
