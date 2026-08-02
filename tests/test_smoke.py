"""Every embedded block must run, on every seed, and produce output.

This is the floor the rest of the suite builds on: if a document raises, none of
the properties below it are meaningful.
"""

from __future__ import annotations

import pytest

from pytexlib import extract_blocks


def test_document_has_extractable_blocks(document):
    blocks = extract_blocks(document)
    assert blocks, "document was collected as having code but no blocks parsed"
    for source in blocks:
        # A syntax error here means the block could never have run under
        # pythontex either.
        compile(source, str(document), "exec")


def test_runs_without_raising(document, seeds, runs_cache):
    failures = []
    for seed in seeds:
        try:
            runs_cache(document, seed)
        except Exception as exc:  # noqa: BLE001 - reporting whatever surfaced
            failures.append(f"seed {seed}: {type(exc).__name__}: {exc}")
    assert not failures, "document raised on {} of {} seeds:\n  {}".format(
        len(failures), len(seeds), "\n  ".join(failures[:5])
    )


def test_produces_output(document, seeds, runs_cache):
    """A document that prints must actually emit something on every seed.

    Not every document prints: some emit their values through inline `\\py{...}`
    macros instead, which produce no stdout and are checked when the document is
    typeset rather than here.
    """
    if not any("print(" in block for block in extract_blocks(document)):
        pytest.skip("emits via inline \\py{...} macros rather than print()")

    empty = [seed for seed in seeds if not runs_cache(document, seed).text.strip()]
    assert not empty, f"produced no output on seeds {empty[:5]}"
