"""Seeding must reproduce a paper exactly.

Reproducibility is what lets an instructor regenerate a specific exam to match a
key that has already been printed and handed out.  It is also a precondition for
golden-file testing, so it is worth enforcing everywhere rather than only where
someone happens to need it.

The way this breaks in practice: `from pylab import *` binds `uniform` to
numpy.random.uniform while `random.randrange` stays on the standard library
generator.  `random.seed()` then drives only one of the two streams and the
document silently stops being reproducible.
"""

from __future__ import annotations

from pytexlib import run_document


def test_same_seed_reproduces_output(document, check_known):
    check_known("determinism_text")

    first = run_document(document, 20240401)
    second = run_document(document, 20240401)

    assert first.text == second.text, (
        "same seed produced different papers; a second RNG is in play "
        "(commonly numpy's, pulled in by `from pylab import *`)"
    )


def test_same_seed_reproduces_answer_key(document, check_known):
    check_known("determinism_key")

    first = run_document(document, 20240401)
    second = run_document(document, 20240401)

    assert first.flat_solutions == second.flat_solutions, (
        "same seed produced a different answer key"
    )
